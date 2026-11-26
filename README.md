# Distribuição de Cartas

Backend do serviço de distribuição e gerenciamento de cartas do projeto S03 do Inatel. O serviço distribui cinco cartas quando recebe um evento de criação de jogador, consulta as cartas e atualiza a posse após uma troca.

**Stack:** Python 3.13 · Flask · uv · pytest

## Rodando localmente

Instale as dependências e inicie a aplicação:

```bash
uv sync
uv run python -m cartas.main
```

A API fica disponível em `http://127.0.0.1:5000`.

Na execução local, o catálogo de Pokémon e a publicação de eventos usam mocks em memória. Não há conexão com a PokéAPI, Broker ou outras aplicações. Jogadores, cartas e eventos publicados são perdidos ao reiniciar o processo. Os adaptadores HTTP continuam disponíveis para testes e integrações futuras.

### Testes

```bash
uv run pytest
```

## Padrões Arquiteturais

O serviço adota a **arquitetura hexagonal (Ports & Adapters)**, organizada em camadas: o núcleo contém as regras e os casos de uso, enquanto adaptadores conectam suas portas às tecnologias externas. O núcleo não depende das implementações de infraestrutura.

### Comparação arquitetural

| Arquitetura                            | Comparação                                                                                                                                                       |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hexagonal**                          | Isola os casos de uso das tecnologias externas por meio de portas e adaptadores, facilitando testes e desenvolvimento paralelo.                                  |
| **Camadas com dependências concretas** | Também separa responsabilidades, mas os serviços poderiam depender diretamente da PokéAPI ou do repositório, dificultando testes e desenvolvimento independente. |

### Núcleo e infraestrutura

- **Domínio e aplicação:** [`model`](./src/cartas/model/) representa conceitos como [`Jogador`](./src/cartas/model/jogador.py), [`Carta`](./src/cartas/model/carta.py) e [`Pokemon`](./src/cartas/model/pokemon.py). Os serviços de [distribuição](./src/cartas/service/distribuicao_cartas.py) e [posse](./src/cartas/service/posse_carta.py) coordenam os casos de uso e aplicam regras de negócio.
- **Infraestrutura:** [`presentation`](./src/cartas/presentation/) expõe a API e recebe eventos; [`repository`](./src/cartas/repository/) armazena jogadores e cartas; e [`integration`](./src/cartas/integration/) concentra a comunicação com sistemas externos e os mocks.

### Portas e adaptadores

As portas são contratos definidos com `Protocol`; os adaptadores ficam na periferia e os acionam ou implementam:

| Tipo                       | Papel                                            | Exemplos no projeto                                                                                                                                                                                                                                                        |
| -------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Portas de entrada**      | Definem operações oferecidas pela aplicação.     | [`DistribuicaoCartasService`](./src/cartas/service/distribuicao_cartas.py) e [`PosseCartaService`](./src/cartas/service/posse_carta.py).                                                                                                                                   |
| **Adaptadores de entrada** | Recebem chamadas externas e acionam os serviços. | [`CartasController`](./src/cartas/presentation/controllers/cartas_controller.py), [`JogadorCriadoConsumer`](./src/cartas/presentation/consumers/jogador_criado_consumer.py) e [`TrocaConcluidaConsumer`](./src/cartas/presentation/consumers/troca_concluida_consumer.py). |
| **Portas de saída**        | Definem operações necessárias ao núcleo.         | Contratos de [catálogo, repositório e publicação](./src/cartas/service/distribuicao_cartas_ports.py) e de [repositório de posse](./src/cartas/service/posse_carta_ports.py).                                                                                               |

[`main.py`](./src/cartas/main.py) conecta as dependências: a execução local usa catálogo e publisher simulados e um repositório em memória. Os adaptadores HTTP para PokéAPI e broker existem, mas não são usados nessa composição. Não há banco de dados nem persistência após o encerramento do processo.

## Injeção de dependência

Injeção de dependência é uma técnica de projeto, não um padrão GoF. Os serviços recebem catálogo, repositório, publisher e estratégia de sorteio pelo construtor. A composição escolhe as implementações, o que permite trocar integrações por mocks sem alterar os serviços. É essa técnica que torna possíveis o Strategy, o Decorator e o Bridge descritos abaixo.

[`main.py`](./src/cartas/main.py):

```python
repositorio = JogadorCartasRepositoryImpl()
distribuicao = DistribuicaoCartasServiceImpl(
    CatalogoPokemonMock(),
    repositorio,
    PublisherMock(),
    SorteioAleatorioStrategy(),
)
posse = PosseCartaServiceImpl(repositorio)
```

A composição com os adaptadores reais fica em [`integration/composicao.py`](./src/cartas/integration/composicao.py). Hoje ela é usada pelos testes de integração, não pelo `main.py`.

## Design Patterns

A classificação segue o [catálogo do Refactoring.Guru](https://refactoring.guru/design-patterns/catalog), que reúne os 22 padrões GoF em criacionais, estruturais e comportamentais. Um padrão conta como **aplicado** apenas quando o código tem a estrutura e a intenção descritas na página do padrão. Se só uma das duas coincide, ele aparece como **parcial**, com o motivo.

| Padrão                  | Categoria      | Aplicação                                                                |
| ----------------------- | -------------- | ------------------------------------------------------------------------ |
| [Adapter](#adapter)     | Estrutural     | Adapta o cliente HTTP à porta do broker e cada consumer ao roteador      |
| [Bridge](#bridge)       | Estrutural     | Separa o que publicar (`Publisher`) de como entregar (`MensageiroBroker`) |
| [Decorator](#decorator) | Estrutural     | Acrescenta cache ao catálogo                                             |
| [Strategy](#strategy)   | Comportamental | Permite variar o algoritmo de sorteio                                    |

### Cobertura do catálogo

| Categoria      | Padrão                                                                                  | Situação     | Motivo                                                                                                                                            |
| -------------- | --------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Criacional     | [Factory Method](https://refactoring.guru/design-patterns/factory-method)               | Não aplicado | As funções `criar_*` de `composicao.py` são fábricas simples: não há superclasse com método de criação sobrescrito por subclasses.                |
| Criacional     | [Abstract Factory](https://refactoring.guru/design-patterns/abstract-factory)           | Não aplicado | Não há famílias de produtos relacionados.                                                                                                         |
| Criacional     | [Builder](https://refactoring.guru/design-patterns/builder)                             | Não aplicado | Os objetos são criados em uma única chamada de construtor.                                                                                        |
| Criacional     | [Prototype](https://refactoring.guru/design-patterns/prototype)                         | Parcial      | `atualizar_posse` copia jogadores com `type(origem)(...)` sem nomear a classe, mas a cópia é feita pelo serviço, não por um `clone()` do objeto. |
| Criacional     | [Singleton](https://refactoring.guru/design-patterns/singleton)                         | Parcial      | `_load_schemas` usa `lru_cache(maxsize=1)` para carregar os schemas uma única vez; o efeito é parecido, mas não há classe de instância única.      |
| Estrutural     | [Adapter](https://refactoring.guru/design-patterns/adapter)                             | Aplicado     | Ver [Adapter](#adapter).                                                                                                                          |
| Estrutural     | [Bridge](https://refactoring.guru/design-patterns/bridge)                               | Aplicado     | Ver [Bridge](#bridge).                                                                                                                            |
| Estrutural     | [Composite](https://refactoring.guru/design-patterns/composite)                         | Não aplicado | Não há estruturas em árvore.                                                                                                                      |
| Estrutural     | [Decorator](https://refactoring.guru/design-patterns/decorator)                         | Aplicado     | Ver [Decorator](#decorator).                                                                                                                      |
| Estrutural     | [Facade](https://refactoring.guru/design-patterns/facade)                               | Não aplicado | `CartasController` só repassa chamadas a um único serviço; não simplifica um subsistema.                                                         |
| Estrutural     | [Flyweight](https://refactoring.guru/design-patterns/flyweight)                         | Não aplicado | O cache reaproveita objetos `Pokemon` para evitar requisições, não para economizar memória.                                                       |
| Estrutural     | [Proxy](https://refactoring.guru/design-patterns/proxy)                                 | Parcial      | `CatalogoPokemonEmCache` tem a intenção de um *caching proxy*, mas a composição é feita pelo cliente, critério do Decorator. Ver [Decorator](#decorator). |
| Comportamental | [Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility) | Não aplicado | Cada evento tem exatamente um tratador; não há cadeia.                                                                                           |
| Comportamental | [Command](https://refactoring.guru/design-patterns/command)                             | Não aplicado | O tratador do roteador recebe o payload na execução; no Command, o objeto já guarda todos os dados da requisição.                                |
| Comportamental | [Iterator](https://refactoring.guru/design-patterns/iterator)                           | Não aplicado | A paginação da PokéAPI é percorrida dentro de `listar_ids_disponiveis` e devolvida de uma vez.                                                    |
| Comportamental | [Mediator](https://refactoring.guru/design-patterns/mediator)                           | Não aplicado | Os componentes não se comunicam por um intermediário.                                                                                             |
| Comportamental | [Memento](https://refactoring.guru/design-patterns/memento)                             | Parcial      | O repositório guarda snapshots das cartas (ver [Data Mapper](#data-mapper)), mas quem os extrai é o repositório, não o próprio `Jogador`.          |
| Comportamental | [Observer](https://refactoring.guru/design-patterns/observer)                           | Não aplicado | Os assinantes ficam no Broker, fora do processo. `RoteadorEventos` registra um único tratador por evento, sem cancelamento de inscrição.         |
| Comportamental | [State](https://refactoring.guru/design-patterns/state)                                 | Não aplicado | Nenhum objeto muda de comportamento conforme um estado interno.                                                                                   |
| Comportamental | [Strategy](https://refactoring.guru/design-patterns/strategy)                           | Aplicado     | Ver [Strategy](#strategy).                                                                                                                        |
| Comportamental | [Template Method](https://refactoring.guru/design-patterns/template-method)             | Não aplicado | Não há herança de implementação com passos sobrescritos.                                                                                          |
| Comportamental | [Visitor](https://refactoring.guru/design-patterns/visitor)                             | Não aplicado | Não há hierarquia de elementos a percorrer.                                                                                                       |

### Adapter

O Adapter permite que objetos com interfaces incompatíveis colaborem: o adaptador implementa a interface que o cliente usa e envolve o objeto que faz o trabalho. Aparece em dois pontos:

- `MensageiroBrokerHTTP` implementa `MensageiroBroker.enviar(topico, mensagem)`, que o publisher usa, e envolve `ClienteJSONEscrita.enviar_json(url, corpo)`. Ele converte o tópico em URL e os erros HTTP em erros do broker.
- `RoteadorEventos.registrar` recebe um `Consumer[T]` tipado e o adapta à forma que o roteador sabe chamar: uma função que recebe o payload cru.

Os conversores de payload e o mapeador da PokéAPI não são Adapters do GoF: são funções de tradução de dados, sem objeto envolvido. Eles estão em [Conversores e mapeadores](#conversores-e-mapeadores).

[`mensageiro_broker.py`](./src/cartas/integration/mensageiro_broker.py):

```python
class MensageiroBrokerHTTP(MensageiroBroker):
    def __init__(self, http: ClienteJSONEscrita, url_base: str) -> None:
        self._http = http
        self._url_base = url_base.rstrip("/")

    def enviar(self, topico: str, mensagem: Mapping[str, object]) -> None:
        url = f"{self._url_base}/eventos/{quote(topico, safe='')}"
        try:
            self._http.enviar_json(url, mensagem)
        except ServicoExternoIndisponivelError as erro:
            raise BrokerIndisponivelError(str(erro)) from erro
        except RespostaHTTPError as erro:
            if erro.transitoria:
                raise BrokerIndisponivelError(str(erro)) from erro
            raise MensagemRejeitadaPeloBrokerError(str(erro)) from erro
```

[`roteador_eventos.py`](./src/cartas/presentation/consumers/roteador_eventos.py):

```python
def registrar[T](
    self,
    nome: str,
    conversor: Callable[[object], T],
    consumidor: Consumer[T],
) -> None:
    def tratar(payload: object) -> None:
        consumidor.consumir(conversor(payload))

    self._tratadores[nome] = tratar
```

### Bridge

O Bridge separa uma abstração da sua implementação em duas hierarquias ligadas por composição, para que variem de forma independente. Na publicação de eventos:

- **Abstração:** `Publisher[T]` decide *o que* publicar e *em qual tópico* (`CartasDistribuidasPublisher`).
- **Implementação:** `MensageiroBroker` decide *como* a mensagem chega ao broker (`MensageiroBrokerHTTP`).

Um novo evento de saída vira um novo `Publisher`; um novo transporte (RabbitMQ, Kafka) vira um novo `MensageiroBroker`, sem multiplicar classes. Diferente do Adapter, o Bridge é uma decisão tomada de antemão, e aqui ela foi tomada porque o protocolo do broker ainda não está confirmado. Hoje cada lado tem uma única implementação, então o ganho só aparece com o segundo evento ou o segundo transporte.

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py):

```python
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

### Decorator

`CatalogoPokemonEmCache` implementa `PokemonCatalogo` e envolve outro `PokemonCatalogo`, adicionando cache sem modificar o gateway. Os Pokémon consultados ficam em cache; a lista de IDs expira após 24 horas; falhas não são guardadas. O cache atende à política de uso justo da PokéAPI.

Decorator e Proxy têm a mesma estrutura. O Refactoring.Guru os diferencia pelo controle do ciclo de vida: o Proxy costuma gerenciar o objeto que envolve, enquanto no Decorator é o cliente quem compõe os objetos. Aqui o catálogo envolvido é recebido pronto e a composição é feita em `criar_catalogo_pokeapi`, por isso a classificação é Decorator.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
    pokemon = self._pokemons.get(pokemon_id)
    if pokemon is None:
        pokemon = self._catalogo.buscar_pokemon_por_id(pokemon_id)
        self._pokemons[pokemon_id] = pokemon
    return pokemon
```

[`composicao.py`](./src/cartas/integration/composicao.py):

```python
return CatalogoPokemonEmCache(PokeAPIClient(ClienteJSONUrllib(timeout), url_base))
```

### Strategy

O Strategy encapsula algoritmos intercambiáveis sob um contrato comum. `SorteioStrategy` define "escolher cinco IDs distintos"; o serviço de distribuição recebe a estratégia pelo construtor e valida o resultado, então outro algoritmo (por raridade, determinístico para testes) é só uma nova classe.

[`sorteio.py`](./src/cartas/service/sorteio.py):

```python
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

[`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py):

```python
ids_sorteados = self._sorteio.sortear(ids_disponiveis)
if (
    len(ids_sorteados) != 5
    or len(set(ids_sorteados)) != 5
    or not set(ids_sorteados).issubset(ids_disponiveis)
):
    raise ValueError("A estratégia deve retornar cinco IDs distintos do catálogo.")
```

## Outros padrões e conceitos de projeto

Os itens abaixo também aparecem no código, mas não fazem parte do catálogo GoF. Repository, Data Mapper, DTO, Gateway e Service Stub são do catálogo *Patterns of Enterprise Application Architecture* (Martin Fowler); Publisher/Producer descreve a publicação de mensagens; os conversores aplicam a ideia de camada anticorrupção.

| Padrão/conceito                                          | Aplicação neste serviço                                                  | Código                                                                                                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [Repository](#repository)                                | Mantém a posse das cartas e as consultas por jogador ou carta            | [`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py)                                                         |
| [Data Mapper](#data-mapper)                              | Converte entre `Jogador` e a estrutura em memória                        | [`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py)                                                         |
| [DTO](#dto)                                              | Transporta dados da API sem expor o modelo de domínio                    | [`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py)                                                                              |
| [Gateway](#gateway)                                      | Encapsula requisições ao catálogo PokéAPI                                | [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py)                                                                          |
| [Publisher/Producer](#publisherproducer)                 | Formata e encaminha eventos de distribuição                              | [`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py)                                                |
| [Conversores e mapeadores](#conversores-e-mapeadores)    | Traduzem payloads do Broker e respostas da PokéAPI para tipos do sistema | [`conversores.py`](./src/cartas/presentation/consumers/conversores.py), [`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py) |
| [Service Stub](#service-stub)                            | Substitui PokéAPI e Broker na execução local                             | [`mocks.py`](./src/cartas/integration/mocks.py)                                                                                                |

### Repository

O repositório centraliza a leitura e a gravação dos jogadores e suas cartas, expondo-os como uma coleção de objetos de domínio. A implementação atual mantém os dados em memória, sincroniza o acesso com um lock e, antes de gravar uma transferência, confere com `validar_transferencia` que nenhuma outra operação alterou os jogadores; se alterou, lança `ConflitoDePersistenciaError`.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

```python
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
```

### Data Mapper

O armazenamento guarda apenas cartas (`Carta` é imutável), nunca o objeto `Jogador`. `_extrair_cartas` converte o jogador para a forma armazenada e `_montar_jogador` cria um `Jogador` novo a cada leitura. Assim, alterar um jogador recebido nunca muda o estado persistido sem passar por `salvar*`.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

```python
def _extrair_cartas(jogador: Jogador) -> CartasPorId:
    """Snapshot das cartas do jogador, desacoplado do objeto mutável recebido."""
    return {carta.carta_id: carta for carta in jogador.listar_cartas()}


def _montar_jogador(jogador_id: UUID, cartas: CartasPorId) -> Jogador:
    return Jogador(jogador_id, cartas.values())
```

### DTO

DTOs representam os dados que atravessam a fronteira HTTP, mantendo o formato da requisição separado das entidades e regras do domínio. São `dataclass(frozen=True)` sem comportamento.

[`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py):

```python
@dataclass(frozen=True)
class AtualizarPosseRequestDTO:
    carta_id: UUID
    novo_jogador_id: UUID
```

### Gateway

`PokeAPIClient` implementa o contrato do catálogo e isola detalhes de HTTP, paginação e JSON. Erros de rede e respostas inválidas são convertidos em exceções que o serviço já conhece. A composição local usa `CatalogoPokemonMock`; o gateway é exercitado pelos testes de integração.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
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

### Publisher/Producer

O publisher serializa o evento de distribuição e delega o envio à porta de mensageria. O produtor não conhece quem consome o evento; quem mantém as inscrições é o Broker, e por isso não se trata de um Observer do GoF. Na execução local, `PublisherMock` registra os eventos em memória, sem conexão com o Broker.

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py):

```python
def publicar(self, evento: EventoCartasDistribuidas) -> None:
    self._mensageiro.enviar(self._topico, serializar_cartas_distribuidas(evento))
```

### Conversores e mapeadores

Os formatos externos terminam nestes módulos: `conversores.py` transforma o JSON recebido do Broker em eventos tipados, e `mapeador_pokeapi.py` transforma as respostas da PokéAPI em `Pokemon`. Se um formato externo mudar, só o módulo correspondente muda; se chegar um dado inválido, o restante do sistema recebe um erro próprio (`EventoInvalidoError`, `RespostaPokeAPIInvalidaError`), não um `KeyError`.

[`conversores.py`](./src/cartas/presentation/consumers/conversores.py):

```python
def converter_troca_concluida(payload: object) -> EventoTrocaConcluida:
    dados = _exigir_objeto(payload)
    return EventoTrocaConcluida(
        carta_id=_ler_uuid(dados, "carta_id"),
        novo_jogador_id=_ler_uuid(dados, "novo_jogador_id"),
        troca_id=_ler_uuid(dados, "troca_id"),
    )
```

### Service Stub

`CatalogoPokemonMock` e `PublisherMock` implementam as mesmas portas que os adaptadores reais, com dados fixos e eventos guardados em memória. Eles permitem rodar o serviço sem PokéAPI nem Broker. O catálogo simulado tem sete Pokémon; o sorteio exige pelo menos cinco.

[`mocks.py`](./src/cartas/integration/mocks.py):

```python
class PublisherMock(Publisher[EventoCartasDistribuidas]):
    def __init__(self) -> None:
        self._eventos: list[EventoCartasDistribuidas] = []

    @property
    def eventos(self) -> tuple[EventoCartasDistribuidas, ...]:
        return tuple(self._eventos)

    def publicar(self, evento: EventoCartasDistribuidas) -> None:
        self._eventos.append(evento)
```

## Endpoints disponíveis

| Método | Rota                                              | Descrição                                            |
| ------ | ------------------------------------------------- | ---------------------------------------------------- |
| `POST` | `/eventos/jogador-criado`                         | Recebe a criação de jogador e distribui cinco cartas |
| `POST` | `/eventos/troca-concluida`                        | Atualiza a posse após uma troca                      |
| `GET`  | `/jogadores/{jogador_id}/cartas`                  | Lista as cartas do jogador                           |
| `GET`  | `/jogadores/{jogador_id}/cartas/{carta_id}/posse` | Verifica a posse de uma carta                        |
| `PUT`  | `/cartas/{carta_id}/posse`                        | Transfere uma carta para outro jogador               |

O evento `jogador-criado` recebe `jogador_id`. O evento `troca-concluida` recebe `carta_id`, `novo_jogador_id` e `troca_id`. Exemplo:

```json
{
  "carta_id": "3b2a0000-0000-0000-0000-000000000001",
  "novo_jogador_id": "8f1c0000-0000-0000-0000-000000000002",
  "troca_id": "a5120000-0000-0000-0000-000000000003"
}
```
