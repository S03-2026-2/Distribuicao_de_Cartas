from http import HTTPStatus


class IntegracaoHTTPError(Exception):
    def __init__(self, url: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.url = url


class ServicoExternoIndisponivelError(IntegracaoHTTPError):
    def __init__(self, url: str) -> None:
        super().__init__(url, f"Serviço externo indisponível em {url}.")


class RespostaHTTPError(IntegracaoHTTPError):
    def __init__(self, url: str, status: int) -> None:
        super().__init__(url, f"{url} respondeu com o status HTTP {status}.")
        self.status = status

    @property
    def transitoria(self) -> bool:
        # 429 entra aqui porque o limite de requisições se renova; repetir depois resolve.
        return (
            self.status >= HTTPStatus.INTERNAL_SERVER_ERROR
            or self.status == HTTPStatus.TOO_MANY_REQUESTS
        )


class CorpoJSONInvalidoError(IntegracaoHTTPError):
    def __init__(self, url: str) -> None:
        super().__init__(url, f"{url} não respondeu com um JSON válido.")
