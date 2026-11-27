from unittest import TestCase
from uuid import uuid4

from cartas.main import criar_app


class AplicacaoLocalTest(TestCase):
    def setUp(self) -> None:
        self.cliente = criar_app().test_client()

    def test_documentacao_openapi_disponivel(self) -> None:
        interface = self.cliente.get("/docs")
        self.assertEqual(interface.status_code, 200)
        self.assertIn(b"SwaggerUIBundle", interface.data)
        self.assertIn(b"./openapi.json", interface.data)

        with self.cliente.get("/openapi.json") as resposta:
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.mimetype, "application/json")
            documento = resposta.get_json()
        self.assertEqual(documento["openapi"], "3.1.0")
        self.assertEqual(
            {rota: set(operacoes) for rota, operacoes in documento["paths"].items()},
            {
                "/eventos/jogador-criado": {"post"},
                "/eventos/troca-concluida": {"post"},
                "/jogadores/{jogador_id}/cartas": {"get"},
                "/jogadores/{jogador_id}/cartas/{carta_id}/posse": {"get"},
                "/cartas/{carta_id}/posse": {"put"},
            },
        )

    def test_evento_de_criacao_distribui_cartas_consultaveis(self) -> None:
        jogador_id = uuid4()

        resposta_evento = self.cliente.post(
            "/eventos/jogador-criado", json={"jogador_id": str(jogador_id)}
        )
        resposta_cartas = self.cliente.get(f"/jogadores/{jogador_id}/cartas")

        self.assertEqual(resposta_evento.status_code, 200)
        self.assertEqual(resposta_cartas.status_code, 200)
        cartas = resposta_cartas.get_json()
        self.assertEqual(len(cartas), 5)
        self.assertEqual(len({carta["pokemon_id"] for carta in cartas}), 5)

    def test_evento_de_troca_atualiza_posse_consultavel(self) -> None:
        origem_id, destino_id = uuid4(), uuid4()
        for jogador_id in (origem_id, destino_id):
            resposta = self.cliente.post(
                "/eventos/jogador-criado", json={"jogador_id": str(jogador_id)}
            )
            self.assertEqual(resposta.status_code, 200)

        cartas_origem = self.cliente.get(
            f"/jogadores/{origem_id}/cartas"
        ).get_json()
        cartas_destino = self.cliente.get(
            f"/jogadores/{destino_id}/cartas"
        ).get_json()
        pokemon_destino = {carta["pokemon_id"] for carta in cartas_destino}
        carta = next(
            carta
            for carta in cartas_origem
            if carta["pokemon_id"] not in pokemon_destino
        )

        resposta_troca = self.cliente.post(
            "/eventos/troca-concluida",
            json={
                "carta_id": carta["carta_id"],
                "novo_jogador_id": str(destino_id),
                "troca_id": str(uuid4()),
            },
        )
        cartas_origem_apos_troca = self.cliente.get(
            f"/jogadores/{origem_id}/cartas"
        ).get_json()
        cartas_destino_apos_troca = self.cliente.get(
            f"/jogadores/{destino_id}/cartas"
        ).get_json()

        self.assertEqual(resposta_troca.status_code, 200)
        self.assertNotIn(
            carta["carta_id"],
            {carta_origem["carta_id"] for carta_origem in cartas_origem_apos_troca},
        )
        self.assertIn(
            carta["carta_id"],
            {carta_destino["carta_id"] for carta_destino in cartas_destino_apos_troca},
        )
