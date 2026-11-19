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
│   ├── presentation/
│   ├── service/
│   └── integration/
└── integration/
```

Os arquivos `pyproject.toml`, `.python-version` e `uv.lock` definem a configuração do projeto, a versão padrão do Python e as versões resolvidas das dependências.

## Padrões Arquiteturais

### Arquitetura em camadas

**Onde / Como aparece:** `presentation` contém controllers e consumers; eles delegam operações aos contratos de `service`. Os serviços usam modelos e portas para suas dependências. `integration` implementa as portas de catálogo e de publicação; `repository` ainda não tem adaptador concreto.

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

MVC não está completo porque não há uma View MVC separada. SOA e MOM também não estão completos: a publicação para o Broker usa um adaptador HTTP provisório e ainda não há integração com um broker real. O receptor de eventos `POST /eventos/<nome>` e seu broker simulado continuam provisórios.

### Camada de Integração / Camada Anticorrupção (Anti-Corruption Layer)

**Onde / Como aparece:** [`integration/`](./src/cartas/integration/) implementa as portas que o serviço declara em [`distribuicao_cartas_ports.py`](./src/cartas/service/distribuicao_cartas_ports.py) (`PokemonCatalogo` e `Publisher[T]`). Na entrada, [`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py) traduz o JSON da PokéAPI (campos em inglês, IDs dentro de URLs, tipos ordenados por `slot`) para `Pokemon`. Na saída, [`serializador_cartas_distribuidas.py`](./src/cartas/integration/serializador_cartas_distribuidas.py) traduz `EventoCartasDistribuidas` para JSON. Falhas de transporte viram exceções da própria integração: `PokeAPIIndisponivelError`/`BrokerIndisponivelError` (subclasses de `ConnectionError`, falha transitória) ou `RespostaPokeAPIInvalidaError` (subclasse de `CatalogoPokemonInvalidoError`, do serviço).

**Significado e motivação:** a camada anticorrupção impede que o modelo de um sistema externo contamine o domínio. Se a PokéAPI ou o Broker mudarem de formato, só os tradutores e adaptadores desta camada mudam. Como as portas pertencem ao serviço e a integração depende delas (e não o contrário), a dependência aponta para dentro (Inversão de Dependência).

**Exemplo completo** ([`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py), trecho público):

```python
def mapear_pokemon(dados: object) -> Pokemon:
    registro = _exigir_objeto(dados, "pokemon")
    tipos_ordenados = sorted(
        (_exigir_objeto(tipo, "types[]") for tipo in _ler_lista(registro, "types")),
        key=lambda tipo: _ler_inteiro(tipo, "slot"),
    )
    return Pokemon(
        pokemon_id=_ler_inteiro(registro, "id"),
        nome_pokemon=_ler_texto(registro, "name"),
        tipos=tuple(
            _ler_texto(_exigir_objeto(tipo.get("type"), "types[].type"), "name")
            for tipo in tipos_ordenados
        ),
    )
```

O transporte HTTP fica em [`cliente_http.py`](./src/cartas/integration/cliente_http.py), separado em dois contratos (`ClienteJSONLeitura` e `ClienteJSONEscrita`, Segregação de Interfaces): o gateway da PokéAPI só lê, e o mensageiro do Broker só escreve. `ClienteJSONUrllib` implementa ambos com a biblioteca padrão. As fábricas de [`integration/composicao.py`](./src/cartas/integration/composicao.py) entregam os adaptadores já montados.

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

### Gateway (cliente da PokéAPI)

**Onde / Como aparece:** `PokeAPIClient` implementa `PokemonCatalogo`. Ele conhece as URLs, percorre a paginação de `/pokemon` (seguindo o campo `next`), delega a tradução ao mapeador e converte erros HTTP em exceções da integração. O transporte é injetado como `ClienteJSONLeitura`.

**Significado e motivação:** o Gateway encapsula o acesso a um recurso externo atrás de um objeto com interface do domínio. O serviço pede "IDs disponíveis" e "pokémon por ID" sem saber que existe HTTP, paginação ou JSON, e os testes substituem o gateway (ou só o transporte) por mocks.

**Exemplo completo** ([`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py)):

```python
class PokeAPIClient(PokemonCatalogo):
    def __init__(
        self,
        http: ClienteJSONLeitura,
        url_base: str = URL_BASE_POKEAPI,
        tamanho_pagina: int = TAMANHO_PAGINA_PADRAO,
    ) -> None:
        if tamanho_pagina < 1:
            raise ValueError("O tamanho da página deve ser positivo.")
        self._http = http
        self._url_base = url_base.rstrip("/")
        self._tamanho_pagina = tamanho_pagina

    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        ids: list[int] = []
        url: str | None = f"{self._url_base}/pokemon?limit={self._tamanho_pagina}"
        while url is not None:
            pagina = mapear_pagina_ids(self._obter_json(url))
            ids.extend(pagina.ids)
            url = pagina.proxima_url
        return tuple(ids)

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        return mapear_pokemon(self._obter_json(f"{self._url_base}/pokemon/{pokemon_id}/"))

    def _obter_json(self, url: str) -> object:
        try:
            return self._http.obter_json(url)
        except ServicoExternoIndisponivelError as erro:
            raise PokeAPIIndisponivelError(str(erro)) from erro
        except RespostaHTTPError as erro:
            if erro.transitoria:
                raise PokeAPIIndisponivelError(str(erro)) from erro
            raise RespostaPokeAPIInvalidaError(str(erro)) from erro
        except CorpoJSONInvalidoError as erro:
            raise RespostaPokeAPIInvalidaError(str(erro)) from erro
```

### Decorator (cache do catálogo)

**Onde / Como aparece:** `CatalogoPokemonEmCache`, no mesmo módulo do gateway, implementa `PokemonCatalogo` e envolve outro `PokemonCatalogo`. Ele guarda os pokémon já buscados (os dados não mudam) e a lista de IDs por 24 horas. Falhas não são guardadas.

**Significado e motivação:** o Decorator acrescenta comportamento sem alterar a classe decorada (Aberto/Fechado). O cache atende à política de uso justo da PokéAPI, que pede que os recursos sejam guardados localmente, sem misturar essa responsabilidade com o gateway.

**Exemplo completo** ([`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py)):

```python
class CatalogoPokemonEmCache(PokemonCatalogo):
    def __init__(
        self,
        catalogo: PokemonCatalogo,
        validade_ids: timedelta = VALIDADE_PADRAO_IDS,
        relogio: Callable[[], float] = monotonic,
    ) -> None:
        self._catalogo = catalogo
        self._validade_ids_segundos = validade_ids.total_seconds()
        self._relogio = relogio
        self._ids: tuple[int, ...] | None = None
        self._ids_obtidos_em = 0.0
        self._pokemons: dict[int, Pokemon] = {}

    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        agora = self._relogio()
        if self._ids is None or agora - self._ids_obtidos_em >= self._validade_ids_segundos:
            self._ids = tuple(self._catalogo.listar_ids_disponiveis())
            self._ids_obtidos_em = agora
        return self._ids

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        pokemon = self._pokemons.get(pokemon_id)
        if pokemon is None:
            pokemon = self._catalogo.buscar_pokemon_por_id(pokemon_id)
            self._pokemons[pokemon_id] = pokemon
        return pokemon
```

### Publisher/Producer (publicação de eventos no Broker)

**Onde / Como aparece:** `CartasDistribuidasPublisher` implementa `Publisher[EventoCartasDistribuidas]`. Ele serializa o evento e o entrega ao tópico `cartas-distribuidas` por meio da porta `MensageiroBroker`, sem conhecer o transporte. `MensageiroBrokerHTTP`, em [`mensageiro_broker.py`](./src/cartas/integration/mensageiro_broker.py), é a implementação **provisória** dessa porta: espelha a convenção do receptor (`POST <url_broker>/eventos/<topico>`, JSON) até a equipe do Broker confirmar o protocolo. As cartas da mensagem seguem o mesmo formato de `CartaResponse`.

**Significado e motivação:** o produtor emite eventos sem conhecer quem os consome, o que desacopla este serviço dos demais. Separar o publisher (o quê e para qual tópico) do mensageiro (como entregar) permite trocar HTTP por RabbitMQ ou Kafka criando outro `MensageiroBroker`, sem mudar o publisher nem o serviço.

**Exemplo completo** ([`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py)):

```python
TOPICO_CARTAS_DISTRIBUIDAS = "cartas-distribuidas"


class CartasDistribuidasPublisher(Publisher[EventoCartasDistribuidas]):
    def __init__(
        self,
        mensageiro: MensageiroBroker,
        topico: str = TOPICO_CARTAS_DISTRIBUIDAS,
    ) -> None:
        self._mensageiro = mensageiro
        self._topico = topico

    def publicar(self, evento: EventoCartasDistribuidas) -> None:
        self._mensageiro.enviar(self._topico, serializar_cartas_distribuidas(evento))
```

Mensagem publicada:

```json
{
  "jogador_id": "8f1c...",
  "cartas": [
    {
      "carta_id": "3b2a...",
      "pokemon_id": 25,
      "nome_pokemon": "pikachu",
      "data_obtencao": "2026-11-19T12:30:00+00:00",
      "origem": "distribuicao_inicial"
    }
  ]
}
```

Os JSON Schemas em [`schemas/`](./src/cartas/presentation/schemas/) e o validador em [`schema_validator.py`](./src/cartas/presentation/schema_validator.py) definem e verificam contratos de dados; validação por schema não é um Design Pattern.

Observer não é listado como aplicado dentro do processo: os eventos são entregues ao Broker (Publisher/Producer), e não a assinantes registrados no próprio serviço. Facade e Singleton não têm exemplos completos no código. O contrato de repositório não tem adaptador concreto neste estado.
