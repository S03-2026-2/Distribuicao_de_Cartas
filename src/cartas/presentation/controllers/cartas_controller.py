from uuid import UUID

from cartas.model.carta import Carta
from cartas.service.posse_carta import PosseCartaService


class CartasController:
    def __init__(self, posse_carta_service: PosseCartaService) -> None:
        self._posse_carta_service = posse_carta_service

    def consultar_cartas_do_jogador(self, jogador_id: UUID) -> list[Carta]:
        return self._posse_carta_service.consultar_cartas_do_jogador(jogador_id)

    def consultar_posse_pokemon(self, jogador_id: UUID, pokemon_id: int) -> bool:
        return self._posse_carta_service.consultar_posse_pokemon(jogador_id, pokemon_id)

    def atualizar_posse(self, carta_id: UUID, novo_jogador_id: UUID) -> None:
        self._posse_carta_service.atualizar_posse(carta_id, novo_jogador_id)
