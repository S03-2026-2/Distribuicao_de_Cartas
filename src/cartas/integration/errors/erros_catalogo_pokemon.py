from cartas.service.erros_distribuicao_cartas import CatalogoPokemonInvalidoError


# As bases são exceções que o serviço já conhece, para que ele trate as falhas sem
# depender de detalhes da PokéAPI: ConnectionError indica que vale tentar de novo.
class PokeAPIIndisponivelError(ConnectionError):
    pass


class RespostaPokeAPIInvalidaError(CatalogoPokemonInvalidoError):
    pass
