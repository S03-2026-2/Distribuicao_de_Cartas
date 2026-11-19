from cartas.integration.cartas_distribuidas_publisher import CartasDistribuidasPublisher
from cartas.integration.catalogo_pokemon import (
    URL_BASE_POKEAPI,
    CatalogoPokemonEmCache,
    PokeAPIClient,
)
from cartas.integration.cliente_http import TIMEOUT_PADRAO_SEGUNDOS, ClienteJSONUrllib
from cartas.integration.mensageiro_broker import MensageiroBrokerHTTP
from cartas.model.events import EventoCartasDistribuidas
from cartas.service.distribuicao_cartas_ports import PokemonCatalogo, Publisher


def criar_catalogo_pokeapi(
    url_base: str = URL_BASE_POKEAPI,
    timeout: float = TIMEOUT_PADRAO_SEGUNDOS,
) -> PokemonCatalogo:
    return CatalogoPokemonEmCache(PokeAPIClient(ClienteJSONUrllib(timeout), url_base))


def criar_publisher_cartas_distribuidas(
    url_broker: str,
    timeout: float = TIMEOUT_PADRAO_SEGUNDOS,
) -> Publisher[EventoCartasDistribuidas]:
    return CartasDistribuidasPublisher(MensageiroBrokerHTTP(ClienteJSONUrllib(timeout), url_broker))
