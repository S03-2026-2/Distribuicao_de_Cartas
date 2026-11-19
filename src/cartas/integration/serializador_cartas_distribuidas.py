from cartas.model.carta import Carta
from cartas.model.events import EventoCartasDistribuidas


def serializar_cartas_distribuidas(evento: EventoCartasDistribuidas) -> dict[str, object]:
    return {
        "jogador_id": str(evento.jogador_id),
        "cartas": [_serializar_carta(carta) for carta in evento.cartas],
    }


# Mesmo formato de CartaResponse da API HTTP, para que outros serviços lidem com uma
# única representação de carta.
def _serializar_carta(carta: Carta) -> dict[str, object]:
    return {
        "carta_id": str(carta.carta_id),
        "pokemon_id": carta.pokemon_id,
        "nome_pokemon": carta.nome_pokemon,
        "data_obtencao": carta.data_obtencao.isoformat(),
        "origem": carta.origem,
    }
