from unittest import TestCase

from jsonschema import ValidationError

from cartas.presentation.schema_validator import SchemaName, validate_payload


class SchemaValidatorTest(TestCase):
    def test_valid_update_request(self) -> None:
        validate_payload(
            SchemaName.ATUALIZAR_POSSE_REQUEST,
            {
                "carta_id": "d85b1407-351d-4694-9392-03acc5870eb1",
                "novo_jogador_id": "a8098c1a-f86e-11da-bd1a-00112444be1e",
            },
        )

    def test_rejects_invalid_uuid_format(self) -> None:
        with self.assertRaises(ValidationError):
            validate_payload(
                SchemaName.ATUALIZAR_POSSE_REQUEST,
                {"carta_id": "not-a-uuid", "novo_jogador_id": "also-not-a-uuid"},
            )

    def test_validates_cards_through_local_schema_reference(self) -> None:
        with self.assertRaises(ValidationError):
            validate_payload(
                SchemaName.CONSULTAR_CARTAS_DO_JOGADOR_RESPONSE,
                [
                    {
                        "carta_id": "d85b1407-351d-4694-9392-03acc5870eb1",
                        "pokemon_id": 1,
                        "nome_pokemon": "Bulbasaur",
                        "data_obtencao": "2026-11-19T00:00:00Z",
                    }
                ],
            )

    def test_rejects_invalid_date_time_format(self) -> None:
        with self.assertRaises(ValidationError):
            validate_payload(
                SchemaName.CARTA_RESPONSE,
                {
                    "carta_id": "d85b1407-351d-4694-9392-03acc5870eb1",
                    "pokemon_id": 1,
                    "nome_pokemon": "Bulbasaur",
                    "data_obtencao": "yesterday",
                    "origem": "distribuicao_inicial",
                },
            )
