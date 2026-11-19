import socket
import threading
from types import TracebackType
from typing import Self

from flask import Flask
from werkzeug.serving import make_server


def url_sem_servidor() -> str:
    with socket.socket() as livre:
        livre.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{livre.getsockname()[1]}"


class ServidorLocal:
    def __init__(self, app: Flask) -> None:
        self._servidor = make_server("127.0.0.1", 0, app)
        self._thread = threading.Thread(target=self._servidor.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._servidor.server_port}"

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        erro: BaseException | None,
        rastro: TracebackType | None,
    ) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()
        self._thread.join(timeout=5)
