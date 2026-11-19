from flask import Flask

from cartas.presentation.consumers.conversores import (
    converter_jogador_criado,
    converter_troca_concluida,
)
from cartas.presentation.consumers.jogador_criado_consumer import JogadorCriadoConsumer
from cartas.presentation.consumers.receptor_http import criar_app
from cartas.presentation.consumers.roteador_eventos import RoteadorEventos
from cartas.presentation.consumers.troca_concluida_consumer import (
    TrocaConcluidaConsumer,
)
from cartas.presentation.controllers.cartas_controller import CartasController
from cartas.service.distribuicao_cartas import DistribuicaoCartasService
from cartas.service.posse_carta import PosseCartaService

EVENTO_JOGADOR_CRIADO = "jogador-criado"
EVENTO_TROCA_CONCLUIDA = "troca-concluida"


def montar_roteador(
    distribuicao: DistribuicaoCartasService,
    posse: PosseCartaService,
) -> RoteadorEventos:
    roteador = RoteadorEventos()
    roteador.registrar(
        EVENTO_JOGADOR_CRIADO,
        converter_jogador_criado,
        JogadorCriadoConsumer(distribuicao),
    )
    roteador.registrar(
        EVENTO_TROCA_CONCLUIDA,
        converter_troca_concluida,
        TrocaConcluidaConsumer(posse),
    )
    return roteador


def montar_app(
    distribuicao: DistribuicaoCartasService,
    posse: PosseCartaService,
) -> Flask:
    return criar_app(
        montar_roteador(distribuicao, posse),
        CartasController(posse),
    )