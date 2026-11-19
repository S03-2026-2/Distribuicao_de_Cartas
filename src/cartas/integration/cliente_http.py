import json
from collections.abc import Mapping
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from cartas.integration.errors.erros_cliente_http import (
    CorpoJSONInvalidoError,
    RespostaHTTPError,
    ServicoExternoIndisponivelError,
)

TIMEOUT_PADRAO_SEGUNDOS = 10.0
USER_AGENT_PADRAO = "cartas-service/0.1"


class ClienteJSONLeitura(Protocol):
    def obter_json(self, url: str) -> object:
        """Lança ServicoExternoIndisponivelError, RespostaHTTPError ou CorpoJSONInvalidoError."""
        ...


class ClienteJSONEscrita(Protocol):
    def enviar_json(self, url: str, corpo: Mapping[str, object]) -> None:
        """Lança ServicoExternoIndisponivelError ou RespostaHTTPError."""
        ...


class ClienteJSONUrllib(ClienteJSONLeitura, ClienteJSONEscrita):
    def __init__(
        self,
        timeout: float = TIMEOUT_PADRAO_SEGUNDOS,
        user_agent: str = USER_AGENT_PADRAO,
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    def obter_json(self, url: str) -> object:
        requisicao = Request(
            url,
            method="GET",
            headers={"Accept": "application/json", "User-Agent": self._user_agent},
        )
        corpo = self._executar(requisicao)
        try:
            return json.loads(corpo)
        except ValueError as erro:
            raise CorpoJSONInvalidoError(url) from erro

    def enviar_json(self, url: str, corpo: Mapping[str, object]) -> None:
        requisicao = Request(
            url,
            data=json.dumps(corpo).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": self._user_agent},
        )
        self._executar(requisicao)

    def _executar(self, requisicao: Request) -> bytes:
        try:
            with urlopen(requisicao, timeout=self._timeout) as resposta:
                corpo: bytes = resposta.read()
                return corpo
        except HTTPError as erro:
            raise RespostaHTTPError(requisicao.full_url, erro.code) from erro
        except OSError as erro:
            raise ServicoExternoIndisponivelError(requisicao.full_url) from erro
