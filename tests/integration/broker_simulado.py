# Broker SIMULADO, apenas para testar o recebimento de mensagens sem depender da
# equipe do Broker. O protocolo abaixo é PROVISÓRIO (POST /eventos/<nome>, JSON)
# e não representa o Broker real.
#
# Uso manual (com a aplicação rodando em http://localhost:5000):
#   uv run python -m tests.integration.broker_simulado \
#       http://localhost:5000 jogador-criado '{"jogador_id": "<uuid>"}'

import argparse
import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RespostaBroker:
    status: int
    corpo: object


class BrokerSimulado:
    def __init__(self, url_base: str, timeout: float = 5.0) -> None:
        self._url_base = url_base.rstrip("/")
        self._timeout = timeout

    def publicar(self, nome_evento: str, corpo: object) -> RespostaBroker:
        dados = json.dumps(corpo).encode("utf-8")
        return self.publicar_bruto(nome_evento, dados, "application/json")

    def publicar_bruto(
        self, nome_evento: str, dados: bytes, content_type: str
    ) -> RespostaBroker:
        requisicao = Request(
            f"{self._url_base}/eventos/{nome_evento}",
            data=dados,
            method="POST",
            headers={"Content-Type": content_type},
        )
        try:
            with urlopen(requisicao, timeout=self._timeout) as resposta:
                status, texto = resposta.status, resposta.read()
        except HTTPError as erro:
            status, texto = erro.code, erro.read()
        return RespostaBroker(status=status, corpo=json.loads(texto))


def main() -> None:
    analisador = argparse.ArgumentParser(description="Envia um evento ao receptor.")
    analisador.add_argument("url_base")
    analisador.add_argument("nome_evento")
    analisador.add_argument("corpo_json")
    argumentos = analisador.parse_args()

    resposta = BrokerSimulado(argumentos.url_base).publicar(
        argumentos.nome_evento, json.loads(argumentos.corpo_json)
    )
    print(resposta.status, resposta.corpo)


if __name__ == "__main__":
    main()