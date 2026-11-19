from typing import Protocol


class Consumer[T](Protocol):
    def consumir(self, evento: T) -> None: ...