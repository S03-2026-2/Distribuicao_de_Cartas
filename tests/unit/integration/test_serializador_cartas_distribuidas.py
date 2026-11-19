from datetime import UTC, datetime
from unittest import TestCase
from uuid import uuid4

from cartas.integration.serializador_cartas_distribuidas import serializar_cartas_distribuidas
from cartas.model.carta import Carta
from cartas.model.events import EventoCartasDistribuidas
from cartas.presentation.schema_validator import SchemaName, validate_payload


class SerializarCartasDistribuidasTest(TestCase):
    def test_gera_json_com_tipos_primitivos(self) -> None:
        jogador_id, carta_id = uuid4(), uuid4()
        data = datetime(2026, 11, 19, 12, 30, tzinfo=UTC)
        evento = EventoCartasDistribuidas(
            jogador_id=jogador_id,
            cartas=(Carta(carta_id, 25, "pikachu", data, "distribuicao_inicial"),),
        )

        mensagem = serializar_cartas_distribuidas(evento)

        self.assertEqual(
            mensagem,
            {
                "jogador_id": str(jogador_id),
                "cartas": [
                    {
                        "carta_id": str(carta_id),
                        "pokemon_id": 25,
                        "nome_pokemon": "pikachu",
                        "data_obtencao": "2026-11-19T12:30:00+00:00",
                        "origem": "distribuicao_inicial",
                    }
                ],
            },
        )

    def test_cartas_seguem_o_mesmo_contrato_da_api_http(self) -> None:
        cartas = tuple(
            Carta(uuid4(), i, f"p{i}", datetime.now(UTC), "distribuicao_inicial")
            for i in range(1, 6)
        )

        mensagem = serializar_cartas_distribuidas(EventoCartasDistribuidas(uuid4(), cartas))

        validate_payload(SchemaName.CONSULTAR_CARTAS_DO_JOGADOR_RESPONSE, mensagem["cartas"])
