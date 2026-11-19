from collections.abc import Mapping
from typing import Protocol
from urllib.parse import quote

from cartas.integration.cliente_http import ClienteJSONEscrita
from cartas.integration.errors.erros_cliente_http import (
    RespostaHTTPError,
    ServicoExternoIndisponivelError,
)
from cartas.integration.errors.erros_mensageiro_broker import (
    BrokerIndisponivelError,
    MensagemRejeitadaPeloBrokerError,
)


class MensageiroBroker(Protocol):
    def enviar(self, topico: str, mensagem: Mapping[str, object]) -> None:
        """Lança BrokerIndisponivelError ou MensagemRejeitadaPeloBrokerError se a mensagem não for aceita."""
        ...


# PROVISÓRIO até confirmação da equipe do Broker. Espelha a convenção do receptor deste
# serviço (POST /eventos/<topico>) para que os dois lados possam ser testados entre si.
class MensageiroBrokerHTTP(MensageiroBroker):
    def __init__(self, http: ClienteJSONEscrita, url_base: str) -> None:
        self._http = http
        self._url_base = url_base.rstrip("/")

    def enviar(self, topico: str, mensagem: Mapping[str, object]) -> None:
        url = f"{self._url_base}/eventos/{quote(topico, safe='')}"
        try:
            self._http.enviar_json(url, mensagem)
        except ServicoExternoIndisponivelError as erro:
            raise BrokerIndisponivelError(str(erro)) from erro
        except RespostaHTTPError as erro:
            if erro.transitoria:
                raise BrokerIndisponivelError(str(erro)) from erro
            raise MensagemRejeitadaPeloBrokerError(str(erro)) from erro
