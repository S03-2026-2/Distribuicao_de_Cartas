from unittest import TestCase
from unittest.mock import Mock
from uuid import UUID, uuid4

from flask import Flask, Response, abort, jsonify, request

from cartas.integration.catalogo_pokemon import PokeAPIClient
from cartas.integration.cliente_http import ClienteJSONUrllib
from cartas.integration.composicao import (
    criar_catalogo_pokeapi,
    criar_publisher_cartas_distribuidas,
)
from cartas.model.jogador import Jogador
from cartas.presentation.consumers.composicao import montar_app
from cartas.service.distribuicao_cartas import DistribuicaoCartasServiceImpl
from cartas.service.posse_carta import PosseCartaService
from cartas.service.sorteio import SorteioAleatorioStrategy
from tests.integration.broker_simulado import BrokerSimulado
from tests.integration.servidor_local import ServidorLocal, url_sem_servidor

POKEMONS = {
    1: ("bulbasaur", ["grass", "poison"]),
    4: ("charmander", ["fire"]),
    7: ("squirtle", ["water"]),
    25: ("pikachu", ["electric"]),
    39: ("jigglypuff", ["normal", "fairy"]),
    133: ("eevee", ["normal"]),
    10033: ("venusaur-mega", ["grass", "poison"]),
}


def criar_pokeapi_simulada(requisicoes: list[str]) -> Flask:
    app = Flask("pokeapi_simulada")

    @app.before_request
    def registrar() -> None:
        requisicoes.append(request.full_path)

    @app.get("/api/v2/pokemon")
    def listar() -> Response:
        limite = int(request.args["limit"])
        inicio = int(request.args.get("offset", 0))
        proximo = inicio + limite
        return jsonify(
            count=len(POKEMONS),
            next=(
                f"{request.host_url}api/v2/pokemon?offset={proximo}&limit={limite}"
                if proximo < len(POKEMONS)
                else None
            ),
            previous=None,
            results=[
                {"name": POKEMONS[i][0], "url": f"{request.host_url}api/v2/pokemon/{i}/"}
                for i in list(POKEMONS)[inicio:proximo]
            ],
        )

    @app.get("/api/v2/pokemon/<int:pokemon_id>/")
    def detalhar(pokemon_id: int) -> Response:
        if pokemon_id not in POKEMONS:
            abort(404)
        nome, tipos = POKEMONS[pokemon_id]
        return jsonify(
            id=pokemon_id,
            name=nome,
            types=[
                {"slot": slot, "type": {"name": tipo, "url": "..."}}
                for slot, tipo in enumerate(tipos, start=1)
            ],
        )

    return app


def criar_broker_destino(mensagens: list[tuple[str, object]]) -> Flask:
    app = Flask("broker_destino")

    @app.post("/eventos/<topico>")
    def receber(topico: str) -> tuple[str, int]:
        mensagens.append((topico, request.get_json()))
        return "", 202

    return app


# O repositório real é escopo da camada de persistência e ainda não existe.
class RepositorioEmMemoria:
    def __init__(self) -> None:
        self.jogadores: dict[UUID, Jogador] = {}

    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None:
        return self.jogadores.get(jogador_id)

    def salvar(self, jogador: Jogador) -> bool:
        if jogador.jogador_id in self.jogadores:
            return False
        self.jogadores[jogador.jogador_id] = jogador
        return True


class FluxoDistribuicaoCartasTest(TestCase):
    def setUp(self) -> None:
        self.requisicoes_pokeapi: list[str] = []
        self.mensagens_broker: list[tuple[str, object]] = []
        pokeapi = self._subir(criar_pokeapi_simulada(self.requisicoes_pokeapi))
        broker = self._subir(criar_broker_destino(self.mensagens_broker))
        self.repositorio = RepositorioEmMemoria()
        servico = DistribuicaoCartasServiceImpl(
            criar_catalogo_pokeapi(f"{pokeapi.url}/api/v2", timeout=2),
            self.repositorio,
            criar_publisher_cartas_distribuidas(broker.url, timeout=2),
            SorteioAleatorioStrategy(),
        )
        aplicacao = self._subir(montar_app(servico, Mock(spec=PosseCartaService)))
        self.broker_origem = BrokerSimulado(aplicacao.url)

    def _subir(self, app: Flask) -> ServidorLocal:
        servidor = ServidorLocal(app).__enter__()
        self.addCleanup(servidor.__exit__, None, None, None)
        return servidor

    def test_jogador_criado_recebe_cinco_cartas_e_evento_e_publicado(self) -> None:
        jogador_id = uuid4()

        resposta = self.broker_origem.publicar("jogador-criado", {"jogador_id": str(jogador_id)})

        self.assertEqual(resposta.status, 200)
        jogador = self.repositorio.jogadores[jogador_id]
        self.assertEqual(len(jogador.cartas), 5)
        self.assertEqual(len({carta.pokemon_id for carta in jogador.cartas}), 5)
        for carta in jogador.cartas:
            self.assertEqual(carta.nome_pokemon, POKEMONS[carta.pokemon_id][0])
        self.assertEqual(len(self.mensagens_broker), 1)
        topico, mensagem = self.mensagens_broker[0]
        self.assertEqual(topico, "cartas-distribuidas")
        self.assertEqual(mensagem["jogador_id"], str(jogador_id))
        self.assertEqual(
            [carta["carta_id"] for carta in mensagem["cartas"]],
            [str(carta.carta_id) for carta in jogador.cartas],
        )

    def test_cache_evita_consultas_repetidas_a_pokeapi(self) -> None:
        for _ in range(3):
            self.broker_origem.publicar("jogador-criado", {"jogador_id": str(uuid4())})

        paginas = [r for r in self.requisicoes_pokeapi if "limit=" in r]
        detalhes = [r for r in self.requisicoes_pokeapi if "limit=" not in r]
        self.assertEqual(len(paginas), 1)
        self.assertEqual(len(detalhes), len(set(detalhes)))
        self.assertEqual(len(self.mensagens_broker), 3)

    def test_paginacao_percorre_todas_as_paginas(self) -> None:
        requisicoes: list[str] = []
        pokeapi = self._subir(criar_pokeapi_simulada(requisicoes))
        client = PokeAPIClient(
            ClienteJSONUrllib(timeout=2), f"{pokeapi.url}/api/v2", tamanho_pagina=3
        )

        ids = client.listar_ids_disponiveis()

        self.assertEqual(ids, tuple(POKEMONS))
        self.assertEqual(len(requisicoes), 3)

    def test_pokeapi_fora_do_ar_responde_500_e_nada_e_gravado_ou_publicado(self) -> None:
        servico = DistribuicaoCartasServiceImpl(
            criar_catalogo_pokeapi(f"{url_sem_servidor()}/api/v2", timeout=0.5),
            self.repositorio,
            Mock(),
            SorteioAleatorioStrategy(),
        )
        aplicacao = self._subir(montar_app(servico, Mock(spec=PosseCartaService)))

        with self.assertLogs(level="ERROR"):
            resposta = BrokerSimulado(aplicacao.url).publicar(
                "jogador-criado", {"jogador_id": str(uuid4())}
            )

        self.assertEqual(resposta.status, 500)
        self.assertEqual(self.repositorio.jogadores, {})
        self.assertEqual(self.mensagens_broker, [])
