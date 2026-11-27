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

### Documentação da API

Com o serviço em execução, abra a [Swagger UI](http://127.0.0.1:5000/docs) e use **Try it out** para enviar requisições. A interface carrega os arquivos do Swagger UI de uma CDN e precisa de internet no navegador. A [especificação OpenAPI](./src/cartas/presentation/openapi.json) também está disponível em `GET /openapi.json`, sem acesso externo.

### Testes

```bash
uv run pytest
```

## Padrões Arquiteturais

O serviço adota a **arquitetura hexagonal (Ports & Adapters)**, organizada em camadas: o núcleo contém as regras e os casos de uso, enquanto adaptadores conectam suas portas às tecnologias externas. O núcleo não depende das implementações de infraestrutura.

### Comparação arquitetural

| Arquitetura | Comparação |
| --- | --- |
| **Arquitetura Hexagonal (Ports & Adapters)** | Foco no isolamento total do núcleo: A aplicação é dividida entre o núcleo (regras de negócio e contratos/portas) e as bordas (adaptadores externos). Todas as dependências apontam estritamente de fora para dentro; o núcleo desconhece qualquer tecnologia de entrada (APIs, filas, UI) ou de saída (bancos de dados, serviços externos). |
| **Clean Architecture** | Segue a mesma regra de dependências de fora para dentro da arquitetura hexagonal, mas explicita a separação em círculos: entidades, casos de uso, adaptadores de interface e frameworks. |

Escolhemos a arquitetura hexagonal porque, para o escopo da distribuição de cartas, a distinção entre núcleo, portas e adaptadores já isola as regras de negócio e permite testá-las sem acessar a PokéAPI ou o broker. Formalizar os limites entre todos os círculos da Clean Architecture acrescentaria convenções e nomenclatura sem um ganho proporcional de desacoplamento ou testabilidade.

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

Injeção de dependência é uma técnica de projeto, não um padrão GoF. Cada classe recebe suas dependências pelo construtor, tipadas pelas portas (`Protocol`), e um único ponto do sistema — a **raiz de composição** — decide quais implementações concretas usar. Isso reduz o acoplamento e permite substituir integrações por mocks sem alterar o núcleo.

[`main.py`](./src/cartas/main.py) é a raiz de composição da execução local:

```python
repositorio = JogadorCartasRepositoryImpl()
distribuicao = DistribuicaoCartasServiceImpl(
    CatalogoPokemonMock(),
    repositorio,
    PublisherMock(),
    SorteioAleatorioStrategy(),
)
posse = PosseCartaServiceImpl(repositorio)
return montar_app(distribuicao, posse)
```

[`composicao.py`](./src/cartas/presentation/consumers/composicao.py) faz o mesmo para a camada de entrada: os consumers e o controller recebem os serviços já construídos.

```python
roteador.registrar(
    EVENTO_JOGADOR_CRIADO,
    converter_jogador_criado,
    JogadorCriadoConsumer(distribuicao),
)
```

## SOLID

Os cinco princípios SOLID, mais a Lei de Demeter, orientam a divisão de responsabilidades do serviço. Cada princípio abaixo traz trechos do código em que ele é aplicado e, quando existe, um ponto em que a aplicação ainda é incompleta.

| Princípio | Ideia central | Onde aparece |
| --- | --- | --- |
| [SRP](#s--single-responsibility-principle-srp) | Uma classe deve ter um único motivo para mudar | Cliente HTTP, mapeador, cache e serializador separados |
| [OCP](#o--openclosed-principle-ocp) | Aberto para extensão, fechado para modificação | Estratégia de sorteio, decorator de cache, registro de eventos |
| [LSP](#l--liskov-substitution-principle-lsp) | Subtipos devem poder substituir o tipo base sem quebrar o cliente | Mocks no lugar dos adaptadores reais, hierarquia de exceções |
| [ISP](#i--interface-segregation-principle-isp) | Clientes não devem depender de métodos que não usam | Portas de leitura/escrita HTTP e repositórios por caso de uso |
| [DIP](#d--dependency-inversion-principle-dip) | Módulos de alto nível dependem de abstrações | Serviços dependem de `Protocol`; infraestrutura implementa |
| [Lei de Demeter](#lei-de-demeter-principle-of-least-knowledge) | Converse apenas com seus colaboradores imediatos | `Jogador.possui_pokemon`, consumers e controller |

### S — Single Responsibility Principle (SRP)

Cada módulo de integração tem um único motivo para mudar. O acesso HTTP, a tradução do JSON da PokéAPI, o cache e a serialização de eventos estão em classes/funções diferentes: uma mudança na política de cache não toca o código de rede, e uma mudança no formato da PokéAPI não toca o cliente.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) — o cache foi separado do client justamente para manter uma responsabilidade por classe:

```python
# A política de uso justo da PokéAPI pede cache local. Fica num decorator para que o
# client continue responsável só pelo acesso. ...
class CatalogoPokemonEmCache(PokemonCatalogo):
    ...

class PokeAPIClient(PokemonCatalogo):
    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        return mapear_pokemon(self._obter_json(f"{self._url_base}/pokemon/{pokemon_id}/"))
```

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py) — o publisher decide *para onde* o evento vai; *como* ele vira JSON é responsabilidade de [`serializador_cartas_distribuidas.py`](./src/cartas/integration/serializador_cartas_distribuidas.py):

```python
def publicar(self, evento: EventoCartasDistribuidas) -> None:
    self._mensageiro.enviar(self._topico, serializar_cartas_distribuidas(evento))
```

[`erros_mensageiro_broker.py`](./src/cartas/integration/errors/erros_mensageiro_broker.py) — até as exceções são separadas por motivo de reação, e não agrupadas em um erro genérico:

```python
# Separadas porque pedem reações diferentes: indisponibilidade justifica reentrega,
# rejeição indica mensagem fora do contrato e repetir não resolve.
class BrokerIndisponivelError(ConnectionError):
    pass


class MensagemRejeitadaPeloBrokerError(RuntimeError):
    pass
```

**Ponto de atenção:** [`receptor_http.py`](./src/cartas/presentation/consumers/receptor_http.py) concentra rotas, validação de schema, montagem de DTOs, serialização de respostas e mapeamento de exceções para status HTTP. É o módulo com mais motivos para mudar no projeto.

### O — Open/Closed Principle (OCP)

Novos comportamentos entram como novas classes ou novos registros, sem editar o código que já funciona.

[`sorteio.py`](./src/cartas/service/sorteio.py) — um novo algoritmo de sorteio (por raridade, por tipo, determinístico para testes) é uma nova classe que implementa `SorteioStrategy`; `DistribuicaoCartasServiceImpl` não muda:

```python
class SorteioStrategy(Protocol):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        """Retorna cinco IDs distintos pertencentes à sequência recebida."""
        ...
```

[`composicao.py`](./src/cartas/integration/composicao.py) — o cache foi acrescentado envolvendo o client, sem alterar `PokeAPIClient`:

```python
return CatalogoPokemonEmCache(PokeAPIClient(ClienteJSONUrllib(timeout), url_base))
```

[`roteador_eventos.py`](./src/cartas/presentation/consumers/roteador_eventos.py) — um novo tipo de evento é suportado com uma nova chamada a `registrar`; `rotear` não precisa de um novo `if`:

```python
def rotear(self, nome: str, payload: object) -> None:
    tratador = self._tratadores.get(nome)
    if tratador is None:
        raise EventoDesconhecidoError(f"Evento desconhecido: {nome}.")
    tratador(payload)
```

### L — Liskov Substitution Principle (LSP)

Qualquer implementação de uma porta deve poder substituir outra sem que o serviço perceba. É o que permite a execução local usar `CatalogoPokemonMock` e `PublisherMock` no lugar de `PokeAPIClient` e `CartasDistribuidasPublisher`.

[`mocks.py`](./src/cartas/integration/mocks.py) — o mock respeita a mesma assinatura e o mesmo significado de `PokemonCatalogo`:

```python
class CatalogoPokemonMock(PokemonCatalogo):
    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        return tuple(self._pokemons)

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        ...
```

[`erros_catalogo_pokemon.py`](./src/cartas/integration/errors/erros_catalogo_pokemon.py) — LSP também vale para exceções: os erros específicos da PokéAPI herdam de tipos que o serviço já conhece, então quem trata `CatalogoPokemonInvalidoError` ou `ConnectionError` continua funcionando com o adaptador real:

```python
class PokeAPIIndisponivelError(ConnectionError):
    pass


class RespostaPokeAPIInvalidaError(CatalogoPokemonInvalidoError):
    pass
```

[`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py) — o serviço verifica a pós-condição do contrato da estratégia, de modo que uma implementação que viole o LSP falha de forma explícita em vez de corromper o estado:

```python
ids_sorteados = self._sorteio.sortear(ids_disponiveis)
if (
    len(ids_sorteados) != 5
    or len(set(ids_sorteados)) != 5
    or not set(ids_sorteados).issubset(ids_disponiveis)
):
    raise ValueError("A estratégia deve retornar cinco IDs distintos do catálogo.")
```

**Ponto de atenção:** a porta `PokemonCatalogo.buscar_pokemon_por_id` não documenta qual exceção é lançada para um ID inexistente. `CatalogoPokemonMock` lança `LookupError`, enquanto `PokeAPIClient` traduz um `404` em `RespostaPokeAPIInvalidaError` (um `ValueError`). Um cliente que trate apenas um dos dois tipos se comportaria de forma diferente com cada implementação.

### I — Interface Segregation Principle (ISP)

As portas são pequenas e definidas pelo que cada cliente usa, não pelo que a implementação oferece.

[`cliente_http.py`](./src/cartas/integration/cliente_http.py) — leitura e escrita HTTP são portas separadas. `PokeAPIClient` depende só de `ClienteJSONLeitura` e `MensageiroBrokerHTTP` só de `ClienteJSONEscrita`, embora a mesma classe concreta implemente as duas:

```python
class ClienteJSONLeitura(Protocol):
    def obter_json(self, url: str) -> object: ...


class ClienteJSONEscrita(Protocol):
    def enviar_json(self, url: str, corpo: Mapping[str, object]) -> None: ...


class ClienteJSONUrllib(ClienteJSONLeitura, ClienteJSONEscrita):
    ...
```

[`distribuicao_cartas_ports.py`](./src/cartas/service/distribuicao_cartas_ports.py) e [`posse_carta_ports.py`](./src/cartas/service/posse_carta_ports.py) — cada serviço declara seu próprio `JogadorCartasRepository` com apenas os métodos de que precisa. A distribuição não enxerga `salvar_transferencia`; a posse não enxerga `salvar`:

```python
# distribuicao_cartas_ports.py
class JogadorCartasRepository(Protocol):
    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None: ...
    def salvar(self, jogador: Jogador) -> bool: ...

# posse_carta_ports.py
class JogadorCartasRepository(Protocol):
    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None: ...
    def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None: ...
    def salvar_transferencia(self, origem: Jogador, destino: Jogador) -> None: ...
```

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py) — uma única implementação satisfaz as duas portas:

```python
class JogadorCartasRepositoryImpl(RepositorioDeDistribuicao, RepositorioDePosse):
```

### D — Dependency Inversion Principle (DIP)

Os serviços (alto nível) dependem de abstrações definidas no próprio pacote `service`; a infraestrutura (baixo nível) importa essas abstrações e as implementa. A seta de dependência no código-fonte aponta de fora para dentro, como exige a arquitetura hexagonal.

[`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py) — o serviço só conhece portas:

```python
def __init__(
    self,
    catalogo: PokemonCatalogo,
    repositorio: JogadorCartasRepository,
    publisher: Publisher[EventoCartasDistribuidas],
    sorteio: SorteioStrategy,
) -> None:
```

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) — o adaptador importa a porta do núcleo, e não o contrário:

```python
from cartas.service.distribuicao_cartas_ports import PokemonCatalogo

class PokeAPIClient(PokemonCatalogo):
```

[`jogador_criado_consumer.py`](./src/cartas/presentation/consumers/jogador_criado_consumer.py) — o adaptador de entrada também depende da interface do serviço (`DistribuicaoCartasService`), não de `DistribuicaoCartasServiceImpl`:

```python
class JogadorCriadoConsumer(Consumer[EventoJogadorCriado]):
    def __init__(self, servico: DistribuicaoCartasService) -> None:
        self._servico = servico
```

### Lei de Demeter (Principle of Least Knowledge)

Um método deve chamar apenas métodos de `self`, de seus parâmetros, de objetos que ele cria e de seus atributos diretos — e não navegar por cadeias como `a.b().c().d()`.

[`jogador.py`](./src/cartas/model/jogador.py) — `Jogador` responde se possui um Pokémon. Quem consulta não precisa conhecer a estrutura interna das cartas (*Tell, Don't Ask*):

```python
def possui_pokemon(self, pokemon_id: int) -> bool:
    return any(carta.pokemon_id == pokemon_id for carta in self._cartas.values())
```

[`posse_carta.py`](./src/cartas/service/posse_carta.py) — o serviço pede ao jogador a resposta, em vez de percorrer `jogador.cartas` e comparar IDs:

```python
def consultar_posse_pokemon(self, jogador_id: UUID, pokemon_id: int) -> bool:
    return self._buscar_jogador(jogador_id).possui_pokemon(pokemon_id)
```

[`troca_concluida_consumer.py`](./src/cartas/presentation/consumers/troca_concluida_consumer.py) — o consumer fala apenas com o seu atributo (`_servico`) e com o seu parâmetro (`evento`), sem alcançar o repositório ou o jogador por trás do serviço:

```python
def consumir(self, evento: EventoTrocaConcluida) -> None:
    self._servico.atualizar_posse(evento.carta_id, evento.novo_jogador_id)
```

Acessos como `carta.pokemon_id` ou `evento.jogador_id` não violam a Lei de Demeter: `Carta` e os eventos são estruturas de dados imutáveis, sem comportamento a encapsular.

## Design Patterns

Os padrões abaixo seguem o [catálogo do Refactoring.Guru](https://refactoring.guru/design-patterns/catalog), que organiza os 22 padrões GoF em criacionais, estruturais e comportamentais. Foram identificados três padrões aplicados diretamente no código:

| Padrão                  | Categoria      | Aplicação                                                            |
| ----------------------- | -------------- | -------------------------------------------------------------------- |
| [Adapter](#adapter)     | Estrutural     | Adapta interfaces externas (HTTP, PokéAPI, consumers) às portas      |
| [Decorator](#decorator) | Estrutural     | Acrescenta cache ao catálogo sem alterar o client da PokéAPI         |
| [Strategy](#strategy)   | Comportamental | Permite variar o algoritmo de sorteio das cartas                     |

Os demais padrões do catálogo foram avaliados e não se aplicam; o motivo de cada um está em [Padrões do catálogo não aplicados](#padrões-do-catálogo-não-aplicados).

### [Adapter](https://refactoring.guru/design-patterns/adapter)

**Intenção:** permitir que objetos com interfaces incompatíveis colaborem. O adaptador implementa a interface que o cliente espera (*target*) e envolve o objeto que de fato faz o trabalho (*adaptee*), convertendo chamadas, dados e erros entre os dois.

| Adaptador | Interface esperada (target) | Objeto adaptado (adaptee) | O que converte |
| --- | --- | --- | --- |
| `MensageiroBrokerHTTP` | `MensageiroBroker.enviar(topico, mensagem)` | `ClienteJSONEscrita.enviar_json(url, corpo)` | Tópico → URL; erros HTTP → erros do broker |
| `PokeAPIClient` | `PokemonCatalogo` | `ClienteJSONLeitura.obter_json(url)` | IDs → URLs paginadas; JSON → `Pokemon`; erros HTTP → erros do catálogo |
| `RoteadorEventos.registrar` | `Callable[[object], None]` (tratador do roteador) | `Consumer[T].consumir(evento: T)` | Payload cru → evento tipado |

**1. Mensageiro do broker** — [`mensageiro_broker.py`](./src/cartas/integration/mensageiro_broker.py). O publisher só sabe enviar para um tópico; o adaptador traduz isso em uma requisição HTTP e traduz os erros de transporte em erros que fazem sentido para mensageria:

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

**2. Catálogo da PokéAPI** — [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py). O serviço pede "todos os IDs disponíveis"; o adaptador transforma isso em uma sequência de requisições paginadas ao cliente HTTP genérico:

```python
class PokeAPIClient(PokemonCatalogo):
    def listar_ids_disponiveis(self) -> tuple[int, ...]:
        ids: list[int] = []
        url: str | None = f"{self._url_base}/pokemon?limit={self._tamanho_pagina}"
        while url is not None:
            pagina = mapear_pagina_ids(self._obter_json(url))
            ids.extend(pagina.ids)
            url = pagina.proxima_url
        return tuple(ids)
```

**3. Registro de consumers** — [`roteador_eventos.py`](./src/cartas/presentation/consumers/roteador_eventos.py). O roteador só sabe chamar funções que recebem o payload cru; `registrar` envolve um `Consumer[T]` tipado em uma função com essa forma. Aqui o adaptador é uma *closure*, a forma idiomática de Adapter em Python quando a interface alvo é um único callable:

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

Os conversores de payload e o mapeador da PokéAPI, isoladamente, não são Adapters: são funções de tradução de dados, sem um objeto envolvido. Eles aparecem em [Camada anticorrupção](#camada-anticorrupção).

### [Decorator](https://refactoring.guru/design-patterns/decorator)

**Intenção:** acrescentar comportamento a um objeto envolvendo-o em outro objeto que implementa a mesma interface. O decorator delega a chamada ao objeto envolvido e adiciona algo antes ou depois.

`CatalogoPokemonEmCache` implementa `PokemonCatalogo` e envolve outro `PokemonCatalogo`. O serviço de distribuição não sabe se está falando com o client ou com o cache.

**1. O decorator** — [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py). Mesma interface, mesma assinatura, comportamento extra (cache) em volta da delegação:

```python
class CatalogoPokemonEmCache(PokemonCatalogo):
    def __init__(
        self,
        catalogo: PokemonCatalogo,
        validade_ids: timedelta = VALIDADE_PADRAO_IDS,
        relogio: Callable[[], float] = monotonic,
    ) -> None:
        self._catalogo = catalogo
        ...

    def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
        pokemon = self._pokemons.get(pokemon_id)
        if pokemon is None:
            pokemon = self._catalogo.buscar_pokemon_por_id(pokemon_id)
            self._pokemons[pokemon_id] = pokemon
        return pokemon
```

**2. Expiração da lista de IDs** — mesmo arquivo. Os dados de um Pokémon não mudam, mas a lista de IDs expira para incluir Pokémon novos. O relógio é injetado, o que permite testar a expiração sem esperar 24 horas:

```python
def listar_ids_disponiveis(self) -> tuple[int, ...]:
    agora = self._relogio()
    if self._ids is None or agora - self._ids_obtidos_em >= self._validade_ids_segundos:
        self._ids = tuple(self._catalogo.listar_ids_disponiveis())
        self._ids_obtidos_em = agora
    return self._ids
```

**3. Composição pelo cliente** — [`composicao.py`](./src/cartas/integration/composicao.py). O empilhamento é decidido por quem monta o objeto:

```python
def criar_catalogo_pokeapi(
    url_base: str = URL_BASE_POKEAPI,
    timeout: float = TIMEOUT_PADRAO_SEGUNDOS,
) -> PokemonCatalogo:
    return CatalogoPokemonEmCache(PokeAPIClient(ClienteJSONUrllib(timeout), url_base))
```

**Decorator ou Proxy?** Um cache também é um uso clássico de Proxy, e as duas estruturas são quase idênticas. Segundo o Refactoring.Guru, a diferença está em quem controla o objeto envolvido: o Proxy normalmente gerencia sozinho o ciclo de vida do serviço, enquanto a composição de um Decorator é sempre controlada pelo cliente. Aqui o `PokeAPIClient` é criado fora e passado ao cache (exemplo 3), por isso a classificação como Decorator.

### [Strategy](https://refactoring.guru/design-patterns/strategy)

**Intenção:** definir uma família de algoritmos, encapsular cada um em uma classe e torná-los intercambiáveis. O objeto que usa o algoritmo (*contexto*) depende apenas da interface da estratégia.

**1. A interface da estratégia** — [`sorteio.py`](./src/cartas/service/sorteio.py). A docstring define o contrato que toda estratégia deve cumprir:

```python
class SorteioStrategy(Protocol):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        """Retorna cinco IDs distintos pertencentes à sequência recebida."""
        ...
```

**2. A estratégia concreta** — mesmo arquivo. Remove duplicatas preservando a ordem e sorteia cinco IDs distintos:

```python
class SorteioAleatorioStrategy(SorteioStrategy):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        ids_unicos = tuple(dict.fromkeys(ids))
        if len(ids_unicos) < 5:
            raise CatalogoPokemonInvalidoError(
                "O catálogo precisa ter pelo menos cinco Pokémon distintos."
            )
        return tuple(sample(ids_unicos, k=5))
```

**3. O contexto** — [`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py). O serviço recebe a estratégia por injeção e só chama `sortear`; trocar o algoritmo é trocar o objeto passado em [`main.py`](./src/cartas/main.py):

```python
self._sorteio = sorteio
...
ids_disponiveis = tuple(self._catalogo.listar_ids_disponiveis())
ids_sorteados = self._sorteio.sortear(ids_disponiveis)
```

### Padrões do catálogo não aplicados

Os demais padrões do catálogo foram avaliados contra o código. Nenhum deles está aplicado; alguns trechos lembram um padrão, mas não cumprem sua intenção:

| Padrão | Categoria | Por que não se aplica |
| --- | --- | --- |
| [Factory Method](https://refactoring.guru/design-patterns/factory-method) | Criacional | `criar_catalogo_pokeapi` e `criar_publisher_cartas_distribuidas` são funções de fábrica simples; não há subclasse que sobrescreva um método de criação. Ver [Simple Factory](#simple-factory). |
| [Abstract Factory](https://refactoring.guru/design-patterns/abstract-factory) | Criacional | Não há famílias de objetos relacionados que precisem ser criadas em conjunto. |
| [Builder](https://refactoring.guru/design-patterns/builder) | Criacional | Todos os objetos são construídos em uma única chamada de construtor. |
| [Prototype](https://refactoring.guru/design-patterns/prototype) | Criacional | `PosseCartaServiceImpl.atualizar_posse` copia jogadores com `type(origem)(origem.jogador_id, origem.listar_cartas())`. A cópia é feita de fora, dependendo do construtor; um Prototype delegaria a cópia a um método do próprio `Jogador`. |
| [Singleton](https://refactoring.guru/design-patterns/singleton) | Criacional | Nenhuma classe restringe o número de instâncias. `_load_schemas` usa `lru_cache(maxsize=1)` para carregar os schemas uma vez; é memoização de função, não um Singleton. |
| [Bridge](https://refactoring.guru/design-patterns/bridge) | Estrutural | Não há duas hierarquias independentes (abstração × implementação) evoluindo em paralelo. |
| [Composite](https://refactoring.guru/design-patterns/composite) | Estrutural | Não há estruturas em árvore tratadas de forma uniforme. |
| [Facade](https://refactoring.guru/design-patterns/facade) | Estrutural | `CartasController` repassa cada chamada a um único serviço, sem simplificar um subsistema. `montar_app` monta dependências: é composição, não fachada. |
| [Flyweight](https://refactoring.guru/design-patterns/flyweight) | Estrutural | Não há volume de objetos que justifique compartilhar estado para economizar memória. |
| [Proxy](https://refactoring.guru/design-patterns/proxy) | Estrutural | O candidato natural, `CatalogoPokemonEmCache`, é classificado como [Decorator](#decorator) pelo motivo explicado lá. |
| [Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility) | Comportamental | O tratamento de erros em `receptor_http.py` usa blocos `except` fixos, não uma cadeia de tratadores encadeáveis. |
| [Command](https://refactoring.guru/design-patterns/command) | Comportamental | Os callables passados a `_executar_cartas` encapsulam uma operação, mas apenas para envolvê-la em tratamento de erros; não há fila, histórico ou desfazer. |
| [Iterator](https://refactoring.guru/design-patterns/iterator) | Comportamental | A iteração usa os protocolos nativos do Python; a paginação da PokéAPI é consumida de uma vez e devolvida como tupla. |
| [Mediator](https://refactoring.guru/design-patterns/mediator) | Comportamental | `RoteadorEventos` despacha cada evento para um único tratador; os componentes não se comunicam entre si por ele. |
| [Memento](https://refactoring.guru/design-patterns/memento) | Comportamental | `_extrair_cartas` tira um *snapshot* do jogador, mas não há restauração de estado anterior. |
| [Observer](https://refactoring.guru/design-patterns/observer) | Comportamental | A publicação de eventos vai para um broker externo (publish/subscribe distribuído); não há lista de assinantes em memória notificados pelo próprio objeto. |
| [State](https://refactoring.guru/design-patterns/state) | Comportamental | Nenhum objeto muda de comportamento conforme um estado interno. |
| [Template Method](https://refactoring.guru/design-patterns/template-method) | Comportamental | Não há classe base com um algoritmo-esqueleto e passos sobrescritos por subclasses. |
| [Visitor](https://refactoring.guru/design-patterns/visitor) | Comportamental | Não há operações aplicadas a uma hierarquia de tipos heterogêneos. |

## Outros padrões e conceitos de projeto

Os itens abaixo aparecem no código, mas não fazem parte do catálogo GoF. Repository, Data Mapper, DTO, Value Object e Gateway vêm do catálogo de padrões de aplicação corporativa (*Patterns of Enterprise Application Architecture*, Martin Fowler); a camada anticorrupção vem do *Domain-Driven Design* (Eric Evans); os demais são padrões de integração e de teste.

| Padrão/conceito | Aplicação neste serviço | Código |
| --- | --- | --- |
| [Repository](#repository) | Coleção de jogadores e cartas, sem expor o armazenamento | [`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py) |
| [Data Mapper](#data-mapper) | Converte entre `Jogador` e a estrutura em memória | [`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py) |
| [Controle otimista de concorrência](#controle-otimista-de-concorrência) | Rejeita transferências baseadas em leituras desatualizadas | [`validacao_transferencia.py`](./src/cartas/service/validacao_transferencia.py) |
| [DTO](#dto) | Transporta dados da API sem expor o modelo de domínio | [`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py) |
| [Value Object](#value-object) | Objetos imutáveis, comparados por valor | [`carta.py`](./src/cartas/model/carta.py), [`pokemon.py`](./src/cartas/model/pokemon.py) |
| [Gateway](#gateway) | Encapsula o acesso à PokéAPI | [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) |
| [Camada anticorrupção](#camada-anticorrupção) | Impede que formatos externos alcancem o domínio | [`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py), [`conversores.py`](./src/cartas/presentation/consumers/conversores.py) |
| [Tradução de exceções](#tradução-de-exceções) | Converte erros técnicos em erros do contexto de quem chama | [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) |
| [Simple Factory](#simple-factory) | Funções que montam adaptadores reais já configurados | [`composicao.py`](./src/cartas/integration/composicao.py) |
| [Publisher/Producer](#publisherproducer) | Formata e encaminha eventos de distribuição | [`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py) |
| [Consumidor idempotente](#consumidor-idempotente) | Reprocessar um evento não duplica a distribuição | [`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py) |
| [Test Double (Fake)](#test-double-fake) | Implementações em memória para execução local e testes | [`mocks.py`](./src/cartas/integration/mocks.py) |

### Repository

O repositório se apresenta ao serviço como uma coleção de `Jogador`, escondendo como os dados são guardados. A implementação atual mantém dois índices em memória — cartas por jogador e dono por carta — e serializa todas as operações com um lock.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py) — o índice reverso permite encontrar o dono de uma carta sem percorrer todos os jogadores:

```python
def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None:
    with self._lock:
        jogador_id = self._dono_por_carta.get(carta_id)
        if jogador_id is None:
            return None
        return _montar_jogador(jogador_id, self._cartas_por_jogador[jogador_id])
```

Mesmo arquivo — `salvar` decide atomicamente se o jogador é novo, cumprindo o contrato da porta ("retorna False sem alterar suas cartas" se ele já existir):

```python
def salvar(self, jogador: Jogador) -> bool:
    cartas = _extrair_cartas(jogador)
    with self._lock:
        if jogador.jogador_id in self._cartas_por_jogador:
            return False
        self._exigir_cartas_sem_dono(cartas)
        self._gravar(jogador.jogador_id, cartas)
        return True
```

### Data Mapper

O armazenamento guarda apenas `Carta` (imutável); `Jogador` é remontado a cada leitura. Assim, alterar um `Jogador` recebido ou devolvido nunca modifica o estado persistido sem passar por `salvar*`.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

```python
def _extrair_cartas(jogador: Jogador) -> CartasPorId:
    """Snapshot das cartas do jogador, desacoplado do objeto mutável recebido."""
    return {carta.carta_id: carta for carta in jogador.listar_cartas()}


def _montar_jogador(jogador_id: UUID, cartas: CartasPorId) -> Jogador:
    return Jogador(jogador_id, cartas.values())
```

### Controle otimista de concorrência

`PosseCartaServiceImpl` lê os dois jogadores, aplica a transferência em cópias e só então pede ao repositório para gravar. Entre a leitura e a gravação, outra requisição pode ter alterado os mesmos jogadores. Em vez de bloquear durante todo o caso de uso, o repositório verifica, já dentro do lock, se o novo estado é exatamente "estado persistido + transferência". Se não for, lança `ConflitoDePersistenciaError` e o chamador pode reler e tentar de novo.

[`validacao_transferencia.py`](./src/cartas/service/validacao_transferencia.py):

```python
movidas = origem_persistida.keys() - origem_nova.keys()

_exigir(bool(movidas), "Nenhuma carta foi transferida.")
_exigir(
    _contida_em(origem_nova, origem_persistida),
    "A origem foi alterada por outra operação.",
)
_exigir(
    _contida_em(destino_persistido, destino_novo),
    "O destino foi alterado por outra operação.",
)
```

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py) — a validação e a gravação acontecem sob o mesmo lock:

```python
with self._lock:
    origem_persistida = self._obter_persistido(origem.jogador_id)
    destino_persistido = self._obter_persistido(destino.jogador_id)
    validar_transferencia(
        origem_persistida, destino_persistido, origem_nova, destino_novo
    )
    self._gravar(origem.jogador_id, origem_nova)
    self._gravar(destino.jogador_id, destino_novo)
```

### DTO

DTOs representam os dados que atravessam a fronteira HTTP, mantendo o formato da requisição e da resposta separado das entidades do domínio.

[`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py):

```python
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
```

[`receptor_http.py`](./src/cartas/presentation/consumers/receptor_http.py) — o DTO só é criado depois que o payload passa pela validação do JSON Schema:

```python
erro = _validar_entrada(SchemaName.ATUALIZAR_POSSE_REQUEST, payload)
if erro is not None:
    return erro

try:
    request_dto = AtualizarPosseRequestDTO(
        carta_id=_ler_uuid(payload, "carta_id"),
        novo_jogador_id=_ler_uuid(payload, "novo_jogador_id"),
    )
```

### Value Object

`Carta`, `Pokemon` e os eventos são `dataclass(frozen=True)`: imutáveis e comparados por valor. Isso permite compartilhá-los entre objetos sem cópia defensiva e é o que torna possível a comparação `origem_persistida[carta_id] == destino_novo[carta_id]` no controle de concorrência.

[`carta.py`](./src/cartas/model/carta.py):

```python
@dataclass(frozen=True)
class Carta:
    carta_id: UUID
    pokemon_id: int
    nome_pokemon: str
    data_obtencao: datetime
    origem: str
```

Rigorosamente, `Carta` tem identidade própria (`carta_id`) e, em termos de DDD, seria uma entidade imutável; o que o código aproveita do Value Object é a imutabilidade e a igualdade por valor. `Jogador`, ao contrário, é uma entidade mutável com identidade (`jogador_id`) e regras próprias, como não aceitar duas cartas do mesmo Pokémon.

### Gateway

`PokeAPIClient` é o único ponto do serviço que conhece a PokéAPI: URLs, paginação, formato JSON e códigos HTTP. Do ponto de vista do GoF, ele é também um [Adapter](#adapter) da porta `PokemonCatalogo`. A composição local usa `CatalogoPokemonMock`; o gateway está disponível para integração futura.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
    return mapear_pokemon(self._obter_json(f"{self._url_base}/pokemon/{pokemon_id}/"))
```

### Camada anticorrupção

Formatos externos — o JSON da PokéAPI e o payload provisório do Broker — são validados e traduzidos na borda. Se a PokéAPI mudar, só o mapeador muda; o domínio continua recebendo `Pokemon`.

[`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py):

```python
# Camada anticorrupção: o formato da PokéAPI termina aqui, para que mudanças nela
# não alcancem o domínio.

def mapear_pokemon(dados: object) -> Pokemon:
    registro = _exigir_objeto(dados, "pokemon")
    tipos_ordenados = sorted(
        (_exigir_objeto(tipo, "types[]") for tipo in _ler_lista(registro, "types")),
        key=lambda tipo: _ler_inteiro(tipo, "slot"),
    )
    return Pokemon(
        pokemon_id=_ler_inteiro(registro, "id"),
        nome_pokemon=_ler_texto(registro, "name"),
        tipos=tuple(...),
    )
```

[`conversores.py`](./src/cartas/presentation/consumers/conversores.py) — o mesmo papel para as mensagens recebidas do Broker:

```python
def converter_troca_concluida(payload: object) -> EventoTrocaConcluida:
    dados = _exigir_objeto(payload)
    return EventoTrocaConcluida(
        carta_id=_ler_uuid(dados, "carta_id"),
        novo_jogador_id=_ler_uuid(dados, "novo_jogador_id"),
        troca_id=_ler_uuid(dados, "troca_id"),
    )
```

### Tradução de exceções

Cada camada converte as exceções da camada de baixo em exceções do seu próprio vocabulário, preservando a causa com `raise ... from erro`. O serviço nunca vê `RespostaHTTPError`; vê "catálogo indisponível" (vale tentar de novo) ou "resposta inválida" (repetir não resolve).

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
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

[`erros_cliente_http.py`](./src/cartas/integration/errors/erros_cliente_http.py) — a decisão "é transitório?" fica em um único lugar e é reaproveitada pelo catálogo e pelo broker:

```python
@property
def transitoria(self) -> bool:
    # 429 entra aqui porque o limite de requisições se renova; repetir depois resolve.
    return (
        self.status >= HTTPStatus.INTERNAL_SERVER_ERROR
        or self.status == HTTPStatus.TOO_MANY_REQUESTS
    )
```

### Simple Factory

Funções que encapsulam a montagem das cadeias de adaptadores reais, devolvendo o tipo da porta. Diferem do Factory Method do GoF por não haver hierarquia de criadores: são apenas funções.

[`composicao.py`](./src/cartas/integration/composicao.py):

```python
def criar_publisher_cartas_distribuidas(
    url_broker: str,
    timeout: float = TIMEOUT_PADRAO_SEGUNDOS,
) -> Publisher[EventoCartasDistribuidas]:
    return CartasDistribuidasPublisher(MensageiroBrokerHTTP(ClienteJSONUrllib(timeout), url_broker))
```

### Publisher/Producer

O publisher serializa o evento de distribuição e delega o envio à porta de mensageria. Na execução local, `PublisherMock` registra os eventos em memória, sem conexão com o Broker.

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

[`serializador_cartas_distribuidas.py`](./src/cartas/integration/serializador_cartas_distribuidas.py) — cada carta do evento usa o mesmo formato de `CartaResponse` da API HTTP, para que outros serviços lidem com uma única representação:

```python
def _serializar_carta(carta: Carta) -> dict[str, object]:
    return {
        "carta_id": str(carta.carta_id),
        "pokemon_id": carta.pokemon_id,
        "nome_pokemon": carta.nome_pokemon,
        "data_obtencao": carta.data_obtencao.isoformat(),
        "origem": carta.origem,
    }
```

### Consumidor idempotente

Brokers costumam entregar uma mesma mensagem mais de uma vez. Receber `jogador-criado` repetido não distribui novas cartas: o serviço devolve o jogador existente, inclusive quando duas entregas chegam ao mesmo tempo e só uma consegue `salvar`.

[`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py):

```python
jogador_existente = self._repositorio.buscar_por_id(jogador_id)
if jogador_existente is not None:
    return jogador_existente
...
if not self._repositorio.salvar(jogador):
    jogador_existente = self._repositorio.buscar_por_id(jogador_id)
    if jogador_existente is None:
        raise RuntimeError("O repositório não retornou o jogador já cadastrado.")
    return jogador_existente
```

**Limitação conhecida:** `troca-concluida` é idempotente apenas para reentregas imediatas. Uma mensagem antiga reentregue depois que a carta já mudou de dono a transferiria de novo; evitar isso exige registrar o `troca_id` já processado, como documentado em [`troca_concluida_consumer.py`](./src/cartas/presentation/consumers/troca_concluida_consumer.py).

### Test Double (Fake)

`CatalogoPokemonMock` e `PublisherMock` são, na terminologia de Gerard Meszaros (*xUnit Test Patterns*), *fakes*: implementações funcionais e simplificadas das portas, usadas tanto na execução local quanto nos testes. `PublisherMock` também expõe os eventos recebidos para inspeção.

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
| `GET`  | `/jogadores/{jogador_id}/pokemons/{pokemon_id}/posse` | Verifica se o jogador possui uma carta desse Pokémon |
| `PUT`  | `/cartas/{carta_id}/posse`                        | Transfere uma carta para outro jogador               |

Para verificar se um jogador possui Bulbasaur, use `GET /jogadores/{jogador_id}/pokemons/1/posse`. A consulta recebe o ID numérico do Pokémon: retorna `200` com `{"possui": true}` ou `{"possui": false}` para um jogador cadastrado, `400` se o ID for inválido e `404` se o jogador não existir. A transferência continua usando o UUID da carta (`carta_id`).

O evento `jogador-criado` recebe `jogador_id`. O evento `troca-concluida` recebe `carta_id`, `novo_jogador_id` e `troca_id`. Exemplo:

```json
{
  "carta_id": "3b2a0000-0000-0000-0000-000000000001",
  "novo_jogador_id": "8f1c0000-0000-0000-0000-000000000002",
  "troca_id": "a5120000-0000-0000-0000-000000000003"
}
```
