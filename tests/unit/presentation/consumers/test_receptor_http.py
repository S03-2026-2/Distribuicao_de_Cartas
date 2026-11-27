from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from flask import Flask
from flask.testing import FlaskClient

from cartas.model.carta import Carta
from cartas.presentation.consumers.composicao import montar_app
from cartas.service.distribuicao_cartas import DistribuicaoCartasService
from cartas.service.posse_carta import PosseCartaService


class ReceptorHttpTest(TestCase):
    def setUp(self) -> None:
        self.distribuicao = Mock(spec=DistribuicaoCartasService)
        self.posse = Mock(spec=PosseCartaService)
        self.app: Flask = montar_app(self.distribuicao, self.posse)
        self.client: FlaskClient = self.app.test_client()
        self.jogador_id = uuid4()
        self.troca = {
            "carta_id": str(uuid4()),
            "novo_jogador_id": str(uuid4()),
            "troca_id": str(uuid4()),
        }

    def test_jogador_criado_valido_responde_200_e_aciona_o_servico(self) -> None:
        resposta = self.client.post(
            "/eventos/jogador-criado", json={"jogador_id": str(self.jogador_id)}
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"status": "ok"})
        self.distribuicao.distribuir_cartas_iniciais.assert_called_once_with(
            self.jogador_id
        )

    def test_troca_concluida_valida_responde_200_e_aciona_o_servico(self) -> None:
        resposta = self.client.post("/eventos/troca-concluida", json=self.troca)

        self.assertEqual(resposta.status_code, 200)
        self.posse.atualizar_posse.assert_called_once()
        carta_id, novo_jogador_id = self.posse.atualizar_posse.call_args.args
        self.assertEqual(str(carta_id), self.troca["carta_id"])
        self.assertEqual(str(novo_jogador_id), self.troca["novo_jogador_id"])

    def test_consultar_cartas_retorna_cartas_serializadas(self) -> None:
        carta = Carta(
            uuid4(), 1, "Bulbasaur", datetime(2026, 11, 19, tzinfo=UTC), "inicial"
        )
        self.posse.consultar_cartas_do_jogador.return_value = [carta]

        resposta = self.client.get(f"/jogadores/{self.jogador_id}/cartas")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.get_json(),
            [
                {
                    "carta_id": str(carta.carta_id),
                    "pokemon_id": 1,
                    "nome_pokemon": "Bulbasaur",
                    "data_obtencao": "2026-11-19T00:00:00+00:00",
                    "origem": "inicial",
                }
            ],
        )
        self.posse.consultar_cartas_do_jogador.assert_called_once_with(
            self.jogador_id
        )

    def test_consultar_posse_retorna_dto_serializado(self) -> None:
        self.posse.consultar_posse_pokemon.return_value = True

        resposta = self.client.get(f"/jogadores/{self.jogador_id}/pokemons/1/posse")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"possui": True})
        self.posse.consultar_posse_pokemon.assert_called_once_with(self.jogador_id, 1)

    def test_pokemon_id_invalido_responde_400(self) -> None:
        for pokemon_id in ("0", "-1", "1.5", str(uuid4())):
            with self.subTest(pokemon_id=pokemon_id):
                resposta = self.client.get(
                    f"/jogadores/{self.jogador_id}/pokemons/{pokemon_id}/posse"
                )
                self.assertEqual(resposta.status_code, 400)
        self.posse.consultar_posse_pokemon.assert_not_called()

    def test_atualizar_posse_retorna_204_e_delega(self) -> None:
        carta_id, novo_jogador_id = uuid4(), uuid4()

        resposta = self.client.put(
            f"/cartas/{carta_id}/posse",
            json={"novo_jogador_id": str(novo_jogador_id)},
        )

        self.assertEqual(resposta.status_code, 204)
        self.assertEqual(resposta.get_data(), b"")
        self.posse.atualizar_posse.assert_called_once_with(carta_id, novo_jogador_id)

    def test_requisicao_de_cartas_com_uuid_invalido_responde_400(self) -> None:
        resposta = self.client.get("/jogadores/invalido/cartas")

        self.assertEqual(resposta.status_code, 400)
        self.posse.consultar_cartas_do_jogador.assert_not_called()

    def test_corpo_invalido_de_atualizacao_responde_400(self) -> None:
        respostas = (
            self.client.put("/cartas/posse-invalida/posse", json={}),
            self.client.put(
                f"/cartas/{uuid4()}/posse", json={"novo_jogador_id": "invalido"}
            ),
            self.client.put(
                f"/cartas/{uuid4()}/posse",
                json={"novo_jogador_id": str(uuid4()), "campo_extra": True},
            ),
        )

        for resposta in respostas:
            with self.subTest(status=resposta.status_code):
                self.assertEqual(resposta.status_code, 400)
        self.posse.atualizar_posse.assert_not_called()

    def test_jogador_inexistente_responde_404(self) -> None:
        self.posse.consultar_cartas_do_jogador.side_effect = LookupError(
            "Jogador não encontrado."
        )

        resposta = self.client.get(f"/jogadores/{self.jogador_id}/cartas")

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.get_json()["status"], "erro")

    def test_transferencia_invalida_responde_409(self) -> None:
        self.posse.atualizar_posse.side_effect = ValueError("Pokémon duplicado.")

        resposta = self.client.put(
            f"/cartas/{uuid4()}/posse",
            json={"novo_jogador_id": str(uuid4())},
        )

        self.assertEqual(resposta.status_code, 409)

    def test_aceita_json_sem_cabecalho_content_type(self) -> None:
        corpo = f'{{"jogador_id": "{self.jogador_id}"}}'

        resposta = self.client.post(
            "/eventos/jogador-criado", data=corpo, content_type="text/plain"
        )

        self.assertEqual(resposta.status_code, 200)

    def test_mensagem_invalida_responde_400_e_nao_aciona_servico(self) -> None:
        corpos = [{}, {"jogador_id": 123}, {"jogador_id": "invalido"}, [1], None]
        for corpo in corpos:
            with self.subTest(corpo=corpo):
                resposta = self.client.post("/eventos/jogador-criado", json=corpo)

                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(resposta.get_json()["status"], "erro")
        self.distribuicao.distribuir_cartas_iniciais.assert_not_called()

    def test_corpo_que_nao_e_json_responde_400(self) -> None:
        resposta = self.client.post(
            "/eventos/jogador-criado", data="isto nao e json", content_type="text/plain"
        )

        self.assertEqual(resposta.status_code, 400)
        self.distribuicao.distribuir_cartas_iniciais.assert_not_called()

    def test_troca_com_campo_ausente_responde_400(self) -> None:
        incompleta = {k: v for k, v in self.troca.items() if k != "troca_id"}

        resposta = self.client.post("/eventos/troca-concluida", json=incompleta)

        self.assertEqual(resposta.status_code, 400)
        self.posse.atualizar_posse.assert_not_called()

    def test_evento_desconhecido_responde_404(self) -> None:
        resposta = self.client.post("/eventos/qualquer-coisa", json={})

        self.assertEqual(resposta.status_code, 404)

    def test_metodo_diferente_de_post_responde_405(self) -> None:
        resposta = self.client.get("/eventos/jogador-criado")

        self.assertEqual(resposta.status_code, 405)

    def test_falha_do_servico_responde_500_registra_log_e_nao_sinaliza_sucesso(
        self,
    ) -> None:
        erros = (ValueError("duplicada"), LookupError("sem carta"), ConnectionError())
        for erro in erros:
            with self.subTest(erro=type(erro).__name__):
                self.posse.atualizar_posse.side_effect = erro

                with self.assertLogs(self.app.logger, level="ERROR"):
                    resposta = self.client.post("/eventos/troca-concluida", json=self.troca)

                self.assertEqual(resposta.status_code, 500)
                self.assertEqual(resposta.get_json()["status"], "erro")

    def test_falha_de_distribuicao_responde_500(self) -> None:
        self.distribuicao.distribuir_cartas_iniciais.side_effect = RuntimeError("x")

        with self.assertLogs(self.app.logger, level="ERROR"):
            resposta = self.client.post(
                "/eventos/jogador-criado", json={"jogador_id": str(self.jogador_id)}
            )

        self.assertEqual(resposta.status_code, 500)

    def test_resposta_500_nao_vaza_a_mensagem_interna_do_erro(self) -> None:
        self.posse.atualizar_posse.side_effect = RuntimeError("segredo interno")

        with self.assertLogs(self.app.logger, level="ERROR"):
            resposta = self.client.post("/eventos/troca-concluida", json=self.troca)

        self.assertNotIn("segredo interno", resposta.get_data(as_text=True))