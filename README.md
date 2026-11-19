# Distribuicao_de_Cartas

Repositório para manter o código backend do sistema de cartas do projeto da disciplina de S03 do Inatel.

## Ambiente de desenvolvimento

O projeto usa Python 3.13 e [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente e as dependências.

```bash
uv sync
```

O comando cria ou atualiza o ambiente virtual local em `.venv/` conforme o `uv.lock`.

## Estrutura inicial

```text
src/
└── cartas/
    ├── main.py
    ├── presentation/
    │   ├── controllers/
    │   └── consumers/
    ├── service/
    ├── repository/
    ├── integration/
    └── model/

tests/
├── unit/
│   ├── model/
│   └── service/
└── integration/
```

Os arquivos `pyproject.toml`, `.python-version` e `uv.lock` definem a configuração do projeto, a versão padrão do Python e as versões resolvidas das dependências.

## Padrões Arquiteturais

### Arquitetura em camadas

**Onde / Como aparece:** `presentation` contém controllers e consumers; eles delegam operações aos contratos de `service`. Os serviços usam modelos e portas para suas dependências. `repository` e `integration` ainda não têm adaptadores concretos.

**Significado e motivação:** separar apresentação, casos de uso e domínio limita o acoplamento e torna explícitas as responsabilidades de cada parte.

**Exemplo completo** ([`cartas_controller.py`](./src/cartas/presentation/controllers/cartas_controller.py)):

```python
from uuid import UUID

from cartas.model.carta import Carta
from cartas.service.posse_carta import PosseCartaService


class CartasController:
    def __init__(self, posse_carta_service: PosseCartaService) -> None:
        self._posse_carta_service = posse_carta_service

    def consultar_cartas_do_jogador(self, jogador_id: UUID) -> list[Carta]:
        return self._posse_carta_service.consultar_cartas_do_jogador(jogador_id)

    def consultar_posse_carta(self, jogador_id: UUID, carta_id: UUID) -> bool:
        return self._posse_carta_service.consultar_posse_carta(
            jogador_id, carta_id
        )

    def atualizar_posse(self, carta_id: UUID, novo_jogador_id: UUID) -> None:
        self._posse_carta_service.atualizar_posse(carta_id, novo_jogador_id)

```

### API HTTP com estilo REST

**Onde / Como aparece:** o receptor Flask expõe `GET /jogadores/<jogador_id>/cartas`, `GET /jogadores/<jogador_id>/cartas/<carta_id>/posse` e `PUT /cartas/<carta_id>/posse`. As rotas validam os dados com JSON Schema, convertem UUIDs, delegam ao `CartasController` e serializam as respostas. O endpoint de atualização recebe `novo_jogador_id` no JSON e responde `204`.

**Significado e motivação:** uma API REST organiza a comunicação em recursos HTTP e usa métodos e representações padronizados, desacoplando clientes da implementação interna. A API back-end está presente; não há uma SPA/front-end neste repositório.

**Exemplo completo da rota de consulta** ([`receptor_http.py`](./src/cartas/presentation/consumers/receptor_http.py)):

```python
@app.get("/jogadores/<jogador_id>/cartas")
def consultar_cartas_do_jogador(jogador_id: str) -> tuple[Response, int]:
    payload = {"jogador_id": jogador_id}
    erro = _validar_entrada(
        SchemaName.CONSULTAR_CARTAS_DO_JOGADOR_REQUEST, payload
    )
    if erro is not None:
        return erro

    try:
        request_dto = ConsultarCartasDoJogadorRequestDTO(
            jogador_id=_ler_uuid(payload, "jogador_id")
        )
    except ValueError as erro:
        return _erro(str(erro)), 400

    return _executar_cartas(
        app,
        "consultar cartas do jogador",
        lambda: _responder_cartas(
            cartas_controller.consultar_cartas_do_jogador(request_dto.jogador_id)
        ),
    )
```

MVC não está completo porque não há uma View MVC separada. SOA e MOM também não estão completos: não há comunicação entre serviços nem integração com um broker real. O receptor de eventos `POST /eventos/<nome>` e seu broker simulado continuam provisórios.

## Design Patterns

### Injeção de Dependência

**Onde / Como aparece:** o `CartasController` recebe `PosseCartaService` pelo construtor e delega a ele as operações do diagrama. A composição injeta o mesmo serviço no controller e no consumer de troca.

**Significado e motivação:** fornecer dependências de fora reduz o acoplamento a implementações concretas e permite substituí-las por mocks em testes.

**Exemplo completo** ([`cartas_controller.py`](./src/cartas/presentation/controllers/cartas_controller.py)):

```python
from uuid import UUID

from cartas.model.carta import Carta
from cartas.service.posse_carta import PosseCartaService


class CartasController:
    def __init__(self, posse_carta_service: PosseCartaService) -> None:
        self._posse_carta_service = posse_carta_service

    def consultar_cartas_do_jogador(self, jogador_id: UUID) -> list[Carta]:
        return self._posse_carta_service.consultar_cartas_do_jogador(jogador_id)

    def consultar_posse_carta(self, jogador_id: UUID, carta_id: UUID) -> bool:
        return self._posse_carta_service.consultar_posse_carta(
            jogador_id, carta_id
        )

    def atualizar_posse(self, carta_id: UUID, novo_jogador_id: UUID) -> None:
        self._posse_carta_service.atualizar_posse(carta_id, novo_jogador_id)
```

### DTO (Data Transfer Object)

**Onde / Como aparece:** os DTOs de entrada e saída da API HTTP estão em [`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py). As rotas os usam para representar os dados recebidos e formatar os dados de resposta; o controller recebe os valores tipados e delega as operações ao serviço.

**Significado e motivação:** DTOs definem contratos de dados explícitos e separam o formato de transporte das entidades e regras do domínio.

**Exemplo completo** ([`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py)):

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ConsultarCartasDoJogadorRequestDTO:
    jogador_id: UUID


@dataclass(frozen=True)
class ConsultarPosseCartaRequestDTO:
    jogador_id: UUID
    carta_id: UUID


@dataclass(frozen=True)
class AtualizarPosseRequestDTO:
    carta_id: UUID
    novo_jogador_id: UUID


@dataclass(frozen=True)
class CartaResponseDTO:
    carta_id: UUID
    pokemon_id: int
    nome_pokemon: str
    data_obtencao: datetime
    origem: str


@dataclass(frozen=True)
class ConsultarPosseCartaResponseDTO:
    possui: bool
```

### Adapter (adaptação de payload)

**Onde / Como aparece:** o roteador registra uma função conversora para cada tipo de evento. A conversora adapta o objeto JSON recebido para um evento tipado que o consumer entende, além de rejeitar campos obrigatórios ausentes ou UUIDs inválidos.

**Significado e motivação:** Adapter permite que duas interfaces incompatíveis cooperem. Aqui, a função de conversão isola o formato externo da mensagem do tipo interno consumido pelo serviço.

**Exemplo completo** ([`conversores.py`](./src/cartas/presentation/consumers/conversores.py), [`events.py`](./src/cartas/presentation/consumers/events.py) e [`errors.py`](./src/cartas/presentation/consumers/errors.py)):

```python
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID


class EventoInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class EventoTrocaConcluida:
    carta_id: UUID
    novo_jogador_id: UUID
    troca_id: UUID


def converter_troca_concluida(payload: object) -> EventoTrocaConcluida:
    dados = _exigir_objeto(payload)
    return EventoTrocaConcluida(
        carta_id=_ler_uuid(dados, "carta_id"),
        novo_jogador_id=_ler_uuid(dados, "novo_jogador_id"),
        troca_id=_ler_uuid(dados, "troca_id"),
    )


def _exigir_objeto(payload: object) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise EventoInvalidoError("O corpo da mensagem deve ser um objeto JSON.")
    return payload


def _ler_uuid(dados: Mapping[str, object], campo: str) -> UUID:
    valor = dados.get(campo)
    if valor is None:
        raise EventoInvalidoError(f"Campo obrigatório ausente: {campo}.")
    if not isinstance(valor, str):
        raise EventoInvalidoError(f"O campo {campo} deve ser um UUID em texto.")
    try:
        return UUID(valor)
    except ValueError as erro:
        raise EventoInvalidoError(f"O campo {campo} não é um UUID válido.") from erro
```

### Strategy

**Onde / Como aparece:** `SorteioStrategy` define o contrato do algoritmo; `SorteioAleatorioStrategy` implementa uma opção concreta. `DistribuicaoCartasServiceImpl` recebe a estratégia por injeção e delega a ela o sorteio.

**Significado e motivação:** Strategy encapsula algoritmos intercambiáveis sob um contrato comum, permitindo trocar o comportamento sem alterar quem o utiliza.

**Exemplo completo** ([`sorteio.py`](./src/cartas/service/sorteio.py) e [`erros_distribuicao_cartas.py`](./src/cartas/service/erros_distribuicao_cartas.py)):

```python
# erros_distribuicao_cartas.py
class CatalogoPokemonInvalidoError(ValueError):
    """O catálogo não forneceu os dados para uma distribuição completa."""
```

```python
# sorteio.py
from collections.abc import Sequence
from typing import Protocol
from random import sample

from cartas.service.erros_distribuicao_cartas import CatalogoPokemonInvalidoError


class SorteioStrategy(Protocol):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        """Retorna cinco IDs distintos pertencentes à sequência recebida."""
        ...


class SorteioAleatorioStrategy(SorteioStrategy):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        ids_unicos = tuple(dict.fromkeys(ids))
        if len(ids_unicos) < 5:
            raise CatalogoPokemonInvalidoError(
                "O catálogo precisa ter pelo menos cinco Pokémon distintos."
            )
        return tuple(sample(ids_unicos, k=5))
```

Os JSON Schemas em [`schemas/`](./src/cartas/presentation/schemas/) e o validador em [`schema_validator.py`](./src/cartas/presentation/schema_validator.py) definem e verificam contratos de dados; validação por schema não é um Design Pattern.

Observer não é listado como aplicado porque existe apenas o contrato `Publisher`, sem implementação concreta de publicação/assinantes. Facade e Singleton não têm exemplos completos no código. O contrato de repositório não tem adaptador concreto neste estado.
