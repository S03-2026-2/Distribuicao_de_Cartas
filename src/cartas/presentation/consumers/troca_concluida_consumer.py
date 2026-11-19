from cartas.presentation.consumers.consumer import Consumer
from cartas.presentation.consumers.events import EventoTrocaConcluida
from cartas.service.posse_carta import PosseCartaService


class TrocaConcluidaConsumer(Consumer[EventoTrocaConcluida]):
    """Limitação conhecida (mensagem duplicada): uma mensagem reentregue logo em
    seguida não altera nada, pois a carta já pertence ao destino. Mas, se uma
    mensagem antiga for reentregue depois que a carta já passou para outro
    jogador, o serviço a transferiria de novo. Evitar isso exigiria registrar as
    trocas já processadas (troca_id), o que depende de persistência e de
    contratos que ainda não existem. Não é tratado aqui.
    """

    def __init__(self, servico: PosseCartaService) -> None:
        self._servico = servico

    def consumir(self, evento: EventoTrocaConcluida) -> None:
        self._servico.atualizar_posse(evento.carta_id, evento.novo_jogador_id)