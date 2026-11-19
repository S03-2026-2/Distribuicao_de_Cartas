from unittest import TestCase
from unittest.mock import Mock, call

from cartas.integration.catalogo_pokemon import PokeAPIClient
from cartas.integration.cliente_http import ClienteJSONLeitura
from cartas.integration.errors.erros_catalogo_pokemon import (
    PokeAPIIndisponivelError,
    RespostaPokeAPIInvalidaError,
)
from cartas.integration.errors.erros_cliente_http import (
    CorpoJSONInvalidoError,
    RespostaHTTPError,
    ServicoExternoIndisponivelError,
)
from cartas.model.pokemon import Pokemon

URL_BASE = "https://pokeapi.test/api/v2"


def item(pokemon_id: int) -> dict[str, str]:
    return {"name": f"p{pokemon_id}", "url": f"{URL_BASE}/pokemon/{pokemon_id}/"}


class PokeAPIClientTest(TestCase):
    def setUp(self) -> None:
        self.http = Mock(spec=ClienteJSONLeitura)
        self.client = PokeAPIClient(self.http, f"{URL_BASE}/", tamanho_pagina=2)

    def test_lista_ids_seguindo_a_paginacao(self) -> None:
        segunda_pagina = f"{URL_BASE}/pokemon?offset=2&limit=2"
        self.http.obter_json.side_effect = [
            {"next": segunda_pagina, "results": [item(1), item(2)]},
            {"next": None, "results": [item(10001)]},
        ]

        ids = self.client.listar_ids_disponiveis()

        self.assertEqual(ids, (1, 2, 10001))
        self.assertEqual(
            self.http.obter_json.call_args_list,
            [call(f"{URL_BASE}/pokemon?limit=2"), call(segunda_pagina)],
        )

    def test_busca_pokemon_e_traduz_para_o_modelo(self) -> None:
        self.http.obter_json.return_value = {
            "id": 25,
            "name": "pikachu",
            "types": [{"slot": 1, "type": {"name": "electric"}}],
        }

        pokemon = self.client.buscar_pokemon_por_id(25)

        self.assertEqual(pokemon, Pokemon(25, "pikachu", ("electric",)))
        self.http.obter_json.assert_called_once_with(f"{URL_BASE}/pokemon/25/")

    def test_falhas_transitorias_viram_pokeapi_indisponivel(self) -> None:
        url = f"{URL_BASE}/pokemon/1/"
        for falha in [
            ServicoExternoIndisponivelError(url),
            RespostaHTTPError(url, 500),
            RespostaHTTPError(url, 503),
            RespostaHTTPError(url, 429),
        ]:
            with self.subTest(falha=str(falha)):
                self.http.obter_json.side_effect = falha

                with self.assertRaises(PokeAPIIndisponivelError) as contexto:
                    self.client.buscar_pokemon_por_id(1)

                self.assertIs(contexto.exception.__cause__, falha)
                self.assertIsInstance(contexto.exception, ConnectionError)

    def test_respostas_fora_do_contrato_viram_resposta_invalida(self) -> None:
        url = f"{URL_BASE}/pokemon/1/"
        for falha in [
            RespostaHTTPError(url, 404),
            RespostaHTTPError(url, 400),
            CorpoJSONInvalidoError(url),
        ]:
            with self.subTest(falha=str(falha)):
                self.http.obter_json.side_effect = falha

                with self.assertRaises(RespostaPokeAPIInvalidaError):
                    self.client.buscar_pokemon_por_id(1)

    def test_falha_na_listagem_tambem_e_traduzida(self) -> None:
        self.http.obter_json.side_effect = ServicoExternoIndisponivelError(URL_BASE)

        with self.assertRaises(PokeAPIIndisponivelError):
            self.client.listar_ids_disponiveis()

    def test_rejeita_tamanho_de_pagina_nao_positivo(self) -> None:
        with self.assertRaises(ValueError):
            PokeAPIClient(self.http, tamanho_pagina=0)
