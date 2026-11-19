import threading
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from werkzeug.serving import make_server

from cartas.presentation.consumers.composicao import montar_roteador
from cartas.presentation.consumers.receptor_http import criar_app
from cartas.service.distribuicao_cartas import DistribuicaoCartasService
from cartas.service.posse_carta import PosseCartaService
from tests.integration.broker_simulado import BrokerSimulado


class BrokerSimuladoTest(TestCase):
    """Envia requisições HTTP reais, por socket, a um servidor local do receptor."""

    def setUp(self) -> None:
        self.distribuicao = Mock(spec=DistribuicaoCartasService)
        self.posse = Mock(spec=PosseCartaService)
        self.app = criar_app(montar_roteador(self.distribuicao, self.posse))
        self.servidor = make_server("127.0.0.1", 0, self.app)
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()
        self.broker = BrokerSimulado(f"http://127.0.0.1:{self.servidor.server_port}")

    def tearDown(self) -> None:
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(timeout=5)

    def test_jogador_criado_chega_ao_servico_por_http(self) -> None:
        jogador_id = uuid4()

        resposta = self.broker.publicar("jogador-criado", {"jogador_id": str(jogador_id)})

        self.assertEqual(resposta.status, 200)
        self.assertEqual(resposta.corpo, {"status": "ok"})
        self.distribuicao.distribuir_cartas_iniciais.assert_called_once_with(jogador_id)

    def test_troca_concluida_chega_ao_servico_por_http(self) -> None:
        carta_id, novo_jogador_id = uuid4(), uuid4()

        resposta = self.broker.publicar(
            "troca-concluida",
            {
                "carta_id": str(carta_id),
                "novo_jogador_id": str(novo_jogador_id),
                "troca_id": str(uuid4()),
            },
        )

        self.assertEqual(resposta.status, 200)
        self.posse.atualizar_posse.assert_called_once_with(carta_id, novo_jogador_id)

    def test_mensagem_invalida_recebe_400_e_nao_aciona_servico(self) -> None:
        resposta = self.broker.publicar("jogador-criado", {"jogador_id": "invalido"})

        self.assertEqual(resposta.status, 400)
        self.distribuicao.distribuir_cartas_iniciais.assert_not_called()

    def test_corpo_que_nao_e_json_recebe_400(self) -> None:
        resposta = self.broker.publicar_bruto(
            "jogador-criado", b"nao e json", "text/plain"
        )

        self.assertEqual(resposta.status, 400)

    def test_evento_desconhecido_recebe_404(self) -> None:
        resposta = self.broker.publicar("outro-evento", {})

        self.assertEqual(resposta.status, 404)

    def test_falha_do_servico_recebe_500_e_nunca_200(self) -> None:
        self.posse.atualizar_posse.side_effect = LookupError("sem carta")

        with self.assertLogs(self.app.logger, level="ERROR"):
            resposta = self.broker.publicar(
                "troca-concluida",
                {
                    "carta_id": str(uuid4()),
                    "novo_jogador_id": str(uuid4()),
                    "troca_id": str(uuid4()),
                },
            )

        self.assertEqual(resposta.status, 500)