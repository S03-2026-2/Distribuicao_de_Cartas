from unittest import TestCase
from unittest.mock import Mock

from cartas.integration.cliente_http import ClienteJSONEscrita
from cartas.integration.errors.erros_cliente_http import (
    RespostaHTTPError,
    ServicoExternoIndisponivelError,
)
from cartas.integration.errors.erros_mensageiro_broker import (
    BrokerIndisponivelError,
    MensagemRejeitadaPeloBrokerError,
)
from cartas.integration.mensageiro_broker import MensageiroBrokerHTTP

URL_BROKER = "http://broker.test"


class MensageiroBrokerHTTPTest(TestCase):
    def setUp(self) -> None:
        self.http = Mock(spec=ClienteJSONEscrita)
        self.mensageiro = MensageiroBrokerHTTP(self.http, f"{URL_BROKER}/")

    def test_envia_post_para_a_rota_do_topico(self) -> None:
        self.mensageiro.enviar("cartas-distribuidas", {"a": 1})

        self.http.enviar_json.assert_called_once_with(
            f"{URL_BROKER}/eventos/cartas-distribuidas", {"a": 1}
        )

    def test_topico_e_codificado_na_url(self) -> None:
        self.mensageiro.enviar("a/b c", {})

        self.assertEqual(self.http.enviar_json.call_args.args[0], f"{URL_BROKER}/eventos/a%2Fb%20c")

    def test_falhas_transitorias_viram_broker_indisponivel(self) -> None:
        for falha in [
            ServicoExternoIndisponivelError(URL_BROKER),
            RespostaHTTPError(URL_BROKER, 502),
            RespostaHTTPError(URL_BROKER, 429),
        ]:
            with self.subTest(falha=str(falha)):
                self.http.enviar_json.side_effect = falha

                with self.assertRaises(BrokerIndisponivelError) as contexto:
                    self.mensageiro.enviar("t", {})

                self.assertIs(contexto.exception.__cause__, falha)

    def test_rejeicao_do_broker_nao_e_tratada_como_transitoria(self) -> None:
        for status in [400, 404, 422]:
            with self.subTest(status=status):
                self.http.enviar_json.side_effect = RespostaHTTPError(URL_BROKER, status)

                with self.assertRaises(MensagemRejeitadaPeloBrokerError):
                    self.mensageiro.enviar("t", {})
