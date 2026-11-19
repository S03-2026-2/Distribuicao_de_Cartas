from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from flask import Flask
from flask.testing import FlaskClient

from cartas.presentation.consumers.composicao import montar_roteador
from cartas.presentation.consumers.receptor_http import criar_app
from cartas.service.distribuicao_cartas import DistribuicaoCartasService
from cartas.service.posse_carta import PosseCartaService


class ReceptorHttpTest(TestCase):
    def setUp(self) -> None:
        self.distribuicao = Mock(spec=DistribuicaoCartasService)
        self.posse = Mock(spec=PosseCartaService)
        self.app: Flask = criar_app(montar_roteador(self.distribuicao, self.posse))
        self.client: FlaskClient = self.app.test_client()
        self.jogador_id = uuid4()
        self.troca = {
            "carta_id": str(uuid4()),
            "novo_jogador_id": str(uuid4()),
            "troca_id": str(uuid4()),
        }

    def test_jogador_criado_valido_responde_200_e_aciona_o_servico(self) -> None:
        resposta = self.client.post(
            "/eventos/jogador-criado", json={"jogador_id": str(self.jogador_id)}
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"status": "ok"})
        self.distribuicao.distribuir_cartas_iniciais.assert_called_once_with(
            self.jogador_id
        )

    def test_troca_concluida_valida_responde_200_e_aciona_o_servico(self) -> None:
        resposta = self.client.post("/eventos/troca-concluida", json=self.troca)

        self.assertEqual(resposta.status_code, 200)
        self.posse.atualizar_posse.assert_called_once()
        carta_id, novo_jogador_id = self.posse.atualizar_posse.call_args.args
        self.assertEqual(str(carta_id), self.troca["carta_id"])
        self.assertEqual(str(novo_jogador_id), self.troca["novo_jogador_id"])

    def test_aceita_json_sem_cabecalho_content_type(self) -> None:
        corpo = f'{{"jogador_id": "{self.jogador_id}"}}'

        resposta = self.client.post(
            "/eventos/jogador-criado", data=corpo, content_type="text/plain"
        )

        self.assertEqual(resposta.status_code, 200)

    def test_mensagem_invalida_responde_400_e_nao_aciona_servico(self) -> None:
        corpos = [{}, {"jogador_id": 123}, {"jogador_id": "invalido"}, [1], None]
        for corpo in corpos:
            with self.subTest(corpo=corpo):
                resposta = self.client.post("/eventos/jogador-criado", json=corpo)

                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(resposta.get_json()["status"], "erro")
        self.distribuicao.distribuir_cartas_iniciais.assert_not_called()

    def test_corpo_que_nao_e_json_responde_400(self) -> None:
        resposta = self.client.post(
            "/eventos/jogador-criado", data="isto nao e json", content_type="text/plain"
        )

        self.assertEqual(resposta.status_code, 400)
        self.distribuicao.distribuir_cartas_iniciais.assert_not_called()

    def test_troca_com_campo_ausente_responde_400(self) -> None:
        incompleta = {k: v for k, v in self.troca.items() if k != "troca_id"}

        resposta = self.client.post("/eventos/troca-concluida", json=incompleta)

        self.assertEqual(resposta.status_code, 400)
        self.posse.atualizar_posse.assert_not_called()

    def test_evento_desconhecido_responde_404(self) -> None:
        resposta = self.client.post("/eventos/qualquer-coisa", json={})

        self.assertEqual(resposta.status_code, 404)

    def test_metodo_diferente_de_post_responde_405(self) -> None:
        resposta = self.client.get("/eventos/jogador-criado")

        self.assertEqual(resposta.status_code, 405)

    def test_falha_do_servico_responde_500_registra_log_e_nao_sinaliza_sucesso(
        self,
    ) -> None:
        erros = (ValueError("duplicada"), LookupError("sem carta"), ConnectionError())
        for erro in erros:
            with self.subTest(erro=type(erro).__name__):
                self.posse.atualizar_posse.side_effect = erro

                with self.assertLogs(self.app.logger, level="ERROR"):
                    resposta = self.client.post("/eventos/troca-concluida", json=self.troca)

                self.assertEqual(resposta.status_code, 500)
                self.assertEqual(resposta.get_json()["status"], "erro")

    def test_falha_de_distribuicao_responde_500(self) -> None:
        self.distribuicao.distribuir_cartas_iniciais.side_effect = RuntimeError("x")

        with self.assertLogs(self.app.logger, level="ERROR"):
            resposta = self.client.post(
                "/eventos/jogador-criado", json={"jogador_id": str(self.jogador_id)}
            )

        self.assertEqual(resposta.status_code, 500)

    def test_resposta_500_nao_vaza_a_mensagem_interna_do_erro(self) -> None:
        self.posse.atualizar_posse.side_effect = RuntimeError("segredo interno")

        with self.assertLogs(self.app.logger, level="ERROR"):
            resposta = self.client.post("/eventos/troca-concluida", json=self.troca)

        self.assertNotIn("segredo interno", resposta.get_data(as_text=True))