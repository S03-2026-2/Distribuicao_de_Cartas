from collections.abc import Callable

from cartas.presentation.consumers.consumer import Consumer
from cartas.presentation.consumers.errors import EventoDesconhecidoError


class RoteadorEventos:
    def __init__(self) -> None:
        self._tratadores: dict[str, Callable[[object], None]] = {}

    def registrar[T](
        self,
        nome: str,
        conversor: Callable[[object], T],
        consumidor: Consumer[T],
    ) -> None:
        def tratar(payload: object) -> None:
            consumidor.consumir(conversor(payload))

        self._tratadores[nome] = tratar

    def rotear(self, nome: str, payload: object) -> None:
        tratador = self._tratadores.get(nome)
        if tratador is None:
            raise EventoDesconhecidoError(f"Evento desconhecido: {nome}.")
        tratador(payload)