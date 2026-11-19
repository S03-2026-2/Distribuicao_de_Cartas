from cartas.integration.mensageiro_broker import MensageiroBroker
from cartas.integration.serializador_cartas_distribuidas import serializar_cartas_distribuidas
from cartas.model.events import EventoCartasDistribuidas
from cartas.service.distribuicao_cartas_ports import Publisher

TOPICO_CARTAS_DISTRIBUIDAS = "cartas-distribuidas"


class CartasDistribuidasPublisher(Publisher[EventoCartasDistribuidas]):
    def __init__(
        self,
        mensageiro: MensageiroBroker,
        topico: str = TOPICO_CARTAS_DISTRIBUIDAS,
    ) -> None:
        self._mensageiro = mensageiro
        self._topico = topico

    def publicar(self, evento: EventoCartasDistribuidas) -> None:
        self._mensageiro.enviar(self._topico, serializar_cartas_distribuidas(evento))
