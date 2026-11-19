from unittest import TestCase
from unittest.mock import Mock
from uuid import UUID, uuid4

from cartas.model.events import EventoCartasDistribuidas
from cartas.model.jogador import Jogador
from cartas.model.pokemon import Pokemon
from cartas.service.distribuicao_cartas_ports import (
    JogadorCartasRepository,
    PokemonCatalogo,
    Publisher,
)
from cartas.service.distribuicao_cartas import (
    CatalogoPokemonInvalidoError,
    DistribuicaoCartasServiceImpl,
)
from cartas.service.sorteio import SorteioAleatorioStrategy
from cartas.service.sorteio import SorteioStrategy


class DistribuicaoCartasServiceTest(TestCase):
    def setUp(self) -> None:
        self.jogador_id = uuid4()
        self.jogadores: dict[UUID, Jogador] = {}
        self.catalogo = Mock(spec=PokemonCatalogo)
        self.catalogo.listar_ids_disponiveis.return_value = [1, 3, 7, 9, 25, 10001]
        self.catalogo.buscar_pokemon_por_id.side_effect = self._buscar_pokemon
        self.repositorio = Mock(spec=JogadorCartasRepository)
        self.repositorio.buscar_por_id.side_effect = self.jogadores.get
        self.repositorio.salvar.side_effect = self._salvar
        self.publisher = Mock(spec=Publisher)
        self.service = DistribuicaoCartasServiceImpl(
            self.catalogo, self.repositorio, self.publisher, SorteioAleatorioStrategy()
        )

    def test_sorteia_cinco_ids_distintos_e_publica_depois_de_gravar(self) -> None:
        ids_catalogo = [1, 3, 7, 7, 9, 25, 10001]
        self.catalogo.listar_ids_disponiveis.return_value = ids_catalogo

        def verificar_gravacao(evento: EventoCartasDistribuidas) -> None:
            self.assertEqual(self.jogadores[evento.jogador_id].cartas, evento.cartas)

        self.publisher.publicar.side_effect = verificar_gravacao

        jogador = self.service.distribuir_cartas_iniciais(self.jogador_id)

        ids_sorteados = {carta.pokemon_id for carta in jogador.cartas}
        self.assertEqual(len(jogador.cartas), 5)
        self.assertEqual(len(ids_sorteados), 5)
        self.assertTrue(ids_sorteados.issubset(ids_catalogo))
        self.assertEqual(len({carta.carta_id for carta in jogador.cartas}), 5)
        self.assertEqual(self.jogadores[self.jogador_id], jogador)
        self.publisher.publicar.assert_called_once_with(
            EventoCartasDistribuidas(self.jogador_id, jogador.cartas)
        )

    def test_usa_estrategia_injetada_para_distribuir(self) -> None:
        sorteio = Mock(spec=SorteioStrategy)
        sorteio.sortear.return_value = (25, 9, 7, 3, 1)
        service = DistribuicaoCartasServiceImpl(
            self.catalogo, self.repositorio, self.publisher, sorteio
        )

        jogador = service.distribuir_cartas_iniciais(self.jogador_id)
        service.distribuir_cartas_iniciais(self.jogador_id)

        sorteio.sortear.assert_called_once_with((1, 3, 7, 9, 25, 10001))
        self.assertEqual(
            tuple(carta.pokemon_id for carta in jogador.cartas), (25, 9, 7, 3, 1)
        )

    def test_estrategia_invalida_nao_consulta_pokemon_nem_grava(self) -> None:
        for ids in [(1, 3, 7, 9), (1, 1, 3, 7, 9), (1, 3, 7, 9, 999999)]:
            with self.subTest(ids=ids):
                sorteio = Mock(spec=SorteioStrategy)
                sorteio.sortear.return_value = ids
                service = DistribuicaoCartasServiceImpl(
                    self.catalogo, self.repositorio, self.publisher, sorteio
                )

                with self.assertRaises(ValueError):
                    service.distribuir_cartas_iniciais(self.jogador_id)

                self.catalogo.buscar_pokemon_por_id.assert_not_called()
                self.repositorio.salvar.assert_not_called()
                self.publisher.publicar.assert_not_called()

    def test_mesmo_pokemon_pode_ser_distribuido_a_dois_jogadores(self) -> None:
        ids_catalogo = [1, 3, 7, 9, 25]
        self.catalogo.listar_ids_disponiveis.return_value = ids_catalogo

        primeiro = self.service.distribuir_cartas_iniciais(self.jogador_id)
        segundo = self.service.distribuir_cartas_iniciais(uuid4())

        self.assertEqual({carta.pokemon_id for carta in primeiro.cartas}, set(ids_catalogo))
        self.assertEqual({carta.pokemon_id for carta in segundo.cartas}, set(ids_catalogo))
        self.assertTrue(
            {carta.carta_id for carta in primeiro.cartas}.isdisjoint(
                carta.carta_id for carta in segundo.cartas
            )
        )

    def test_catalogo_com_menos_de_cinco_ids_distintos_nao_grava(self) -> None:
        self.catalogo.listar_ids_disponiveis.return_value = [1, 1, 3, 7, 9]

        with self.assertRaises(CatalogoPokemonInvalidoError):
            self.service.distribuir_cartas_iniciais(self.jogador_id)

        self.repositorio.salvar.assert_not_called()
        self.publisher.publicar.assert_not_called()

    def test_falha_na_quinta_consulta_nao_deixa_lote_parcial(self) -> None:
        def buscar_pokemon(pokemon_id: int) -> Pokemon:
            if self.catalogo.buscar_pokemon_por_id.call_count == 5:
                raise TimeoutError("PokéAPI indisponível")
            return self._buscar_pokemon(pokemon_id)

        self.catalogo.buscar_pokemon_por_id.side_effect = buscar_pokemon

        with self.assertRaises(TimeoutError):
            self.service.distribuir_cartas_iniciais(self.jogador_id)

        self.repositorio.salvar.assert_not_called()
        self.publisher.publicar.assert_not_called()

    def test_falha_ao_gravar_nao_publica(self) -> None:
        self.repositorio.salvar.side_effect = ConnectionError

        with self.assertRaises(ConnectionError):
            self.service.distribuir_cartas_iniciais(self.jogador_id)

        self.publisher.publicar.assert_not_called()

    def test_reentrega_preserva_cartas_atuais_do_jogador(self) -> None:
        jogador = self.service.distribuir_cartas_iniciais(self.jogador_id)
        jogador.remover_carta(jogador.cartas[-1].carta_id)

        jogador_reentregue = self.service.distribuir_cartas_iniciais(self.jogador_id)

        self.assertIs(jogador_reentregue, jogador)
        self.assertEqual(len(jogador_reentregue.listar_cartas()), 4)
        self.catalogo.listar_ids_disponiveis.assert_called_once_with()
        self.repositorio.salvar.assert_called_once_with(jogador)
        self.publisher.publicar.assert_called_once()

    def test_criacao_concorrente_publica_apenas_o_lote_vencedor(self) -> None:
        def salvar_apos_concorrente(candidato: Jogador) -> bool:
            self.repositorio.salvar.side_effect = self._salvar
            vencedor = self.service.distribuir_cartas_iniciais(self.jogador_id)
            self.assertNotEqual(candidato.cartas, vencedor.cartas)
            return self._salvar(candidato)

        self.repositorio.salvar.side_effect = salvar_apos_concorrente

        jogador = self.service.distribuir_cartas_iniciais(self.jogador_id)

        self.assertEqual(jogador, self.jogadores[self.jogador_id])
        self.assertEqual(self.repositorio.salvar.call_count, 2)
        self.publisher.publicar.assert_called_once_with(
            EventoCartasDistribuidas(self.jogador_id, jogador.cartas)
        )

    def test_falha_ao_publicar_preserva_lote_gravado(self) -> None:
        self.publisher.publicar.side_effect = ConnectionError

        with self.assertRaises(ConnectionError):
            self.service.distribuir_cartas_iniciais(self.jogador_id)

        jogador = self.service.distribuir_cartas_iniciais(self.jogador_id)

        self.assertEqual(self.jogadores[self.jogador_id], jogador)
        self.assertEqual(len(jogador.cartas), 5)
        self.publisher.publicar.assert_called_once()

    @staticmethod
    def _buscar_pokemon(pokemon_id: int) -> Pokemon:
        return Pokemon(pokemon_id=pokemon_id, nome_pokemon=f"pokemon-{pokemon_id}")

    def _salvar(self, jogador: Jogador) -> bool:
        if jogador.jogador_id in self.jogadores:
            return False
        self.jogadores[jogador.jogador_id] = jogador
        return True
