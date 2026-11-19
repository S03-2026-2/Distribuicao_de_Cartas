from cartas.presentation.consumers.consumer import Consumer
from cartas.presentation.consumers.events import EventoJogadorCriado
from cartas.service.distribuicao_cartas import DistribuicaoCartasService


class JogadorCriadoConsumer(Consumer[EventoJogadorCriado]):
    def __init__(self, servico: DistribuicaoCartasService) -> None:
        self._servico = servico

    def consumir(self, evento: EventoJogadorCriado) -> None:
        self._servico.distribuir_cartas_iniciais(evento.jogador_id)