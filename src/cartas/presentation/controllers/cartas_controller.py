from cartas.presentation.dtos.posse_carta import (
    AtualizarPosseRequestDTO,
    CartaResponseDTO,
    ConsultarCartasDoJogadorRequestDTO,
    ConsultarPosseCartaRequestDTO,
    ConsultarPosseCartaResponseDTO,
)
from cartas.service.posse_carta import PosseCartaService


class CartasController:
    def __init__(self, posse_carta_service: PosseCartaService) -> None:
        self._posse_carta_service = posse_carta_service

    def consultar_cartas_do_jogador(
        self, request: ConsultarCartasDoJogadorRequestDTO
    ) -> list[CartaResponseDTO]:
        cartas = self._posse_carta_service.consultar_cartas_do_jogador(
            request.jogador_id
        )
        return [
            CartaResponseDTO(
                carta_id=carta.carta_id,
                pokemon_id=carta.pokemon_id,
                nome_pokemon=carta.nome_pokemon,
                data_obtencao=carta.data_obtencao,
                origem=carta.origem,
            )
            for carta in cartas
        ]

    def consultar_posse_carta(
        self, request: ConsultarPosseCartaRequestDTO
    ) -> ConsultarPosseCartaResponseDTO:
        possui = self._posse_carta_service.consultar_posse_carta(
            request.jogador_id, request.carta_id
        )
        return ConsultarPosseCartaResponseDTO(possui=possui)

    def atualizar_posse(self, request: AtualizarPosseRequestDTO) -> None:
        self._posse_carta_service.atualizar_posse(
            request.carta_id, request.novo_jogador_id
        )
