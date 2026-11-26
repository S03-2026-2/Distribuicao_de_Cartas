from flask import Flask

from cartas.integration.mocks import CatalogoPokemonMock, PublisherMock
from cartas.presentation.consumers.composicao import montar_app
from cartas.service.distribuicao_cartas import DistribuicaoCartasServiceImpl
from cartas.repository.jogador_cartas_repository import JogadorCartasRepositoryImpl
from cartas.service.posse_carta import PosseCartaServiceImpl
from cartas.service.sorteio import SorteioAleatorioStrategy


def criar_app() -> Flask:
    repositorio = JogadorCartasRepositoryImpl()
    distribuicao = DistribuicaoCartasServiceImpl(
        CatalogoPokemonMock(),
        repositorio,
        PublisherMock(),
        SorteioAleatorioStrategy(),
    )
    posse = PosseCartaServiceImpl(repositorio)
    return montar_app(distribuicao, posse)


def main() -> None:
    criar_app().run(host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
