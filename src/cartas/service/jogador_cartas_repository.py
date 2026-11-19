from threading import Lock
from uuid import UUID

from cartas.model.carta import Carta
from cartas.model.jogador import Jogador
from cartas.repository.validacao_transferencia import CartasPorId, validar_transferencia
from cartas.service.distribuicao_cartas_ports import (
    JogadorCartasRepository as RepositorioDeDistribuicao,
)
from cartas.service.erros_persistencia import ConflitoDePersistenciaError
from cartas.service.posse_carta_ports import (
    JogadorCartasRepository as RepositorioDePosse,
)


class JogadorCartasRepositoryImpl(RepositorioDeDistribuicao, RepositorioDePosse):
    """Repositório em memória de jogadores e das cartas que possuem.

    Padrões:
    - Repository: expõe uma coleção de `Jogador` sem revelar como é armazenada.
    - Data Mapper: o armazenamento guarda apenas `Carta` (imutável); `Jogador`
      é remontado a cada leitura. Assim, alterar um `Jogador` recebido ou
      devolvido nunca modifica o estado persistido sem passar por `salvar*`.

    Todas as operações são serializadas por um lock, o que torna `salvar` e
    `salvar_transferencia` atômicos entre requisições concorrentes.
    """

    def __init__(self) -> None:
        self._cartas_por_jogador: dict[UUID, CartasPorId] = {}
        self._dono_por_carta: dict[UUID, UUID] = {}
        self._lock = Lock()

    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None:
        with self._lock:
            cartas = self._cartas_por_jogador.get(jogador_id)
            return None if cartas is None else _montar_jogador(jogador_id, cartas)

    def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None:
        with self._lock:
            jogador_id = self._dono_por_carta.get(carta_id)
            if jogador_id is None:
                return None
            return _montar_jogador(jogador_id, self._cartas_por_jogador[jogador_id])

    def salvar(self, jogador: Jogador) -> bool:
        cartas = _extrair_cartas(jogador)
        with self._lock:
            if jogador.jogador_id in self._cartas_por_jogador:
                return False
            self._exigir_cartas_sem_dono(cartas)
            self._gravar(jogador.jogador_id, cartas)
            return True

    def salvar_transferencia(self, origem: Jogador, destino: Jogador) -> None:
        if origem.jogador_id == destino.jogador_id:
            raise ValueError("Origem e destino devem ser jogadores diferentes.")
        origem_nova = _extrair_cartas(origem)
        destino_novo = _extrair_cartas(destino)

        with self._lock:
            origem_persistida = self._obter_persistido(origem.jogador_id)
            destino_persistido = self._obter_persistido(destino.jogador_id)
            validar_transferencia(
                origem_persistida, destino_persistido, origem_nova, destino_novo
            )
            self._gravar(origem.jogador_id, origem_nova)
            self._gravar(destino.jogador_id, destino_novo)

    def _obter_persistido(self, jogador_id: UUID) -> CartasPorId:
        try:
            return self._cartas_por_jogador[jogador_id]
        except KeyError:
            raise LookupError(f"Jogador {jogador_id} não encontrado.") from None

    def _exigir_cartas_sem_dono(self, cartas: CartasPorId) -> None:
        if any(carta_id in self._dono_por_carta for carta_id in cartas):
            raise ConflitoDePersistenciaError("Uma das cartas já pertence a outro jogador.")

    def _gravar(self, jogador_id: UUID, cartas: CartasPorId) -> None:
        """Substitui as cartas do jogador e mantém o índice de donos consistente."""
        for carta_id in self._cartas_por_jogador.get(jogador_id, {}):
            del self._dono_por_carta[carta_id]
        self._cartas_por_jogador[jogador_id] = cartas
        for carta_id in cartas:
            self._dono_por_carta[carta_id] = jogador_id


def _extrair_cartas(jogador: Jogador) -> CartasPorId:
    """Snapshot das cartas do jogador, desacoplado do objeto mutável recebido."""
    return {carta.carta_id: carta for carta in jogador.listar_cartas()}


def _montar_jogador(jogador_id: UUID, cartas: CartasPorId) -> Jogador:
    return Jogador(jogador_id, cartas.values())
