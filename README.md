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

Injeção de dependência é uma técnica de projeto, não um padrão GoF. A composição fornece as implementações aos serviços, reduzindo o acoplamento e permitindo substituir integrações por mocks.

[`main.py`](./src/cartas/main.py):

```python
repositorio = JogadorCartasRepositoryImpl()
distribuicao = DistribuicaoCartasServiceImpl(
    CatalogoPokemonMock(), repositorio, PublisherMock(), SorteioAleatorioStrategy()
)
posse = PosseCartaServiceImpl(repositorio)
```

## SOLID

Os cinco princípios SOLID e a Lei de Demeter aparecem na forma como o serviço divide responsabilidades e dependências. Cada subseção abaixo mostra trechos reais do código em que o princípio é aplicado. Os pontos em que a aplicação ainda é incompleta estão reunidos em [Limitações conhecidas](#limitações-conhecidas).

| Princípio | Ideia central | Onde aparece |
| --- | --- | --- |
| [SRP](#s--single-responsibility-principle-srp) | Cada módulo tem um único motivo para mudar | Transporte HTTP, mapeamento, cache, serialização e validação de transferência separados |
| [OCP](#o--openclosed-principle-ocp) | Estender o comportamento sem modificar o código existente | Estratégia de sorteio, cache como decorator, registro de eventos no roteador |
| [LSP](#l--liskov-substitution-principle-lsp) | Implementações substituem o contrato sem quebrar quem o usa | Mocks e adaptadores reais na mesma porta, hierarquia de exceções |
| [ISP](#i--interface-segregation-principle-isp) | Ninguém depende de métodos que não usa | Clientes HTTP de leitura e escrita, repositórios por caso de uso |
| [DIP](#d--dependency-inversion-principle-dip) | O núcleo depende de abstrações; a infraestrutura as implementa | Portas `Protocol` no pacote `service`, adaptadores apontando para dentro |
| [Lei de Demeter](#lei-de-demeter) | Cada objeto conversa apenas com seus colaboradores diretos | `Jogador.possui_pokemon`, cadeia publisher → mensageiro → HTTP, consumers |

### S - Single Responsibility Principle (SRP)

Uma classe ou módulo deve ter um único motivo para mudar. Na integração com sistemas externos, cada etapa ficou em um módulo próprio, de modo que uma mudança em uma delas não alcança as outras:

| Responsabilidade | Código | Muda quando… |
| --- | --- | --- |
| Transporte HTTP/JSON | [`ClienteJSONUrllib`](./src/cartas/integration/cliente_http.py) | Mudam timeout, cabeçalhos ou a biblioteca HTTP |
| Endereços e paginação da PokéAPI | [`PokeAPIClient`](./src/cartas/integration/catalogo_pokemon.py) | Mudam as rotas da PokéAPI |
| Tradução do JSON da PokéAPI para o domínio | [`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py) | Muda o formato da resposta da PokéAPI |
| Cache do catálogo | [`CatalogoPokemonEmCache`](./src/cartas/integration/catalogo_pokemon.py) | Muda a política de cache |
| Formato do evento publicado | [`serializador_cartas_distribuidas.py`](./src/cartas/integration/serializador_cartas_distribuidas.py) | Muda o contrato do evento `cartas-distribuidas` |
| Destino do evento | [`CartasDistribuidasPublisher`](./src/cartas/integration/cartas_distribuidas_publisher.py) | Muda o tópico |
| Convenção de URL do broker | [`MensageiroBrokerHTTP`](./src/cartas/integration/mensageiro_broker.py) | Muda a API do broker |
| Detecção de conflito em transferências | [`validacao_transferencia.py`](./src/cartas/service/validacao_transferencia.py) | Muda a regra de concorrência |

O cache foi separado do client justamente para manter uma responsabilidade por classe, como registra o próprio código.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
# A política de uso justo da PokéAPI pede cache local. Fica num decorator para que o
# client continue responsável só pelo acesso. Dados de um pokémon não mudam, então não
# expiram; a lista de IDs expira para incluir pokémon novos. Falhas não são guardadas
# para que a próxima chamada tente de novo.
class CatalogoPokemonEmCache(PokemonCatalogo):
```

O publisher decide apenas *para onde* o evento vai; *como* ele vira JSON é responsabilidade do serializador.

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py):

```python
def publicar(self, evento: EventoCartasDistribuidas) -> None:
    self._mensageiro.enviar(self._topico, serializar_cartas_distribuidas(evento))
```

O repositório cuida do armazenamento e do lock, mas delega a regra que decide se uma transferência é válida diante de alterações concorrentes.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

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

### O - Open/Closed Principle (OCP)

O código deve estar aberto para extensão e fechado para modificação. Há três pontos de extensão explícitos.

**Algoritmo de sorteio.** `DistribuicaoCartasServiceImpl` só conhece o contrato `SorteioStrategy`. Um novo algoritmo (por raridade, por tipo, determinístico para testes) é uma nova classe, sem alterar o serviço. O teste `test_usa_estrategia_injetada_para_distribuir` faz exatamente isso com um sorteio fixo.

[`sorteio.py`](./src/cartas/service/sorteio.py) e [`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py):

```python
class SorteioStrategy(Protocol):
    def sortear(self, ids: Sequence[int]) -> tuple[int, ...]:
        """Retorna cinco IDs distintos pertencentes à sequência recebida."""
        ...
```

```python
ids_disponiveis = tuple(self._catalogo.listar_ids_disponiveis())
ids_sorteados = self._sorteio.sortear(ids_disponiveis)
```

**Cache do catálogo.** O cache foi acrescentado envolvendo o `PokeAPIClient`, que não precisou ser alterado. Outros comportamentos (log, métricas, retentativas) podem ser empilhados da mesma forma.

[`integration/composicao.py`](./src/cartas/integration/composicao.py):

```python
def criar_catalogo_pokeapi(
    url_base: str = URL_BASE_POKEAPI,
    timeout: float = TIMEOUT_PADRAO_SEGUNDOS,
) -> PokemonCatalogo:
    return CatalogoPokemonEmCache(PokeAPIClient(ClienteJSONUrllib(timeout), url_base))
```

**Novos eventos.** Para tratar um novo evento basta criar um conversor e um `Consumer` e registrá-los na composição. `RoteadorEventos.rotear` e a rota `POST /eventos/<nome>` do receptor HTTP não mudam.

[`roteador_eventos.py`](./src/cartas/presentation/consumers/roteador_eventos.py) e [`consumers/composicao.py`](./src/cartas/presentation/consumers/composicao.py):

```python
def rotear(self, nome: str, payload: object) -> None:
    tratador = self._tratadores.get(nome)
    if tratador is None:
        raise EventoDesconhecidoError(f"Evento desconhecido: {nome}.")
    tratador(payload)
```

```python
roteador.registrar(
    EVENTO_TROCA_CONCLUIDA,
    converter_troca_concluida,
    TrocaConcluidaConsumer(posse),
)
```

### L - Liskov Substitution Principle (LSP)

Qualquer implementação de um contrato deve poder substituir outra sem que o código cliente perceba. Isso exige contratos explícitos - tipos, pós-condições e erros possíveis - e implementações que os respeitem.

**Mesma porta, implementações intercambiáveis.** `PokemonCatalogo` tem três implementações: `CatalogoPokemonMock`, `PokeAPIClient` e `CatalogoPokemonEmCache`. `Publisher[EventoCartasDistribuidas]` tem `PublisherMock` e `CartasDistribuidasPublisher`. O serviço de distribuição funciona com qualquer uma delas; só a composição muda.

[`main.py`](./src/cartas/main.py) (execução local) e [`integration/composicao.py`](./src/cartas/integration/composicao.py) (integração real):

```python
distribuicao = DistribuicaoCartasServiceImpl(
    CatalogoPokemonMock(),
    repositorio,
    PublisherMock(),
    SorteioAleatorioStrategy(),
)
```

```python
return CatalogoPokemonEmCache(PokeAPIClient(ClienteJSONUrllib(timeout), url_base))
```

**Exceções que respeitam o contrato.** As falhas da PokéAPI herdam de exceções que o núcleo já conhece. Um chamador que trata `ConnectionError` ou `CatalogoPokemonInvalidoError` continua correto quando o catálogo simulado é trocado pelo real, sem precisar conhecer detalhes da PokéAPI.

[`erros_catalogo_pokemon.py`](./src/cartas/integration/errors/erros_catalogo_pokemon.py):

```python
# As bases são exceções que o serviço já conhece, para que ele trate as falhas sem
# depender de detalhes da PokéAPI: ConnectionError indica que vale tentar de novo.
class PokeAPIIndisponivelError(ConnectionError):
    pass


class RespostaPokeAPIInvalidaError(CatalogoPokemonInvalidoError):
    pass
```

**Pós-condição documentada e verificada.** O contrato de `SorteioStrategy` declara a pós-condição na docstring ("cinco IDs distintos pertencentes à sequência recebida"), e o serviço rejeita uma implementação que a viole antes de consultar o catálogo ou gravar qualquer dado. O teste `test_estrategia_invalida_nao_consulta_pokemon_nem_grava` cobre esse caso.

[`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py):

```python
if (
    len(ids_sorteados) != 5
    or len(set(ids_sorteados)) != 5
    or not set(ids_sorteados).issubset(ids_disponiveis)
):
    raise ValueError("A estratégia deve retornar cinco IDs distintos do catálogo.")
```

### I - Interface Segregation Principle (ISP)

Nenhum cliente deve depender de métodos que não usa. As portas foram recortadas pelo que cada cliente precisa, e não pelo que a implementação oferece.

**Leitura e escrita HTTP separadas.** `ClienteJSONUrllib` implementa as duas interfaces, mas `PokeAPIClient` depende só da leitura e `MensageiroBrokerHTTP` só da escrita. O catálogo não consegue enviar dados, e o mensageiro não consegue fazer `GET`.

[`cliente_http.py`](./src/cartas/integration/cliente_http.py), [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) e [`mensageiro_broker.py`](./src/cartas/integration/mensageiro_broker.py) (docstrings e parâmetros opcionais omitidos):

```python
class ClienteJSONLeitura(Protocol):
    def obter_json(self, url: str) -> object:
        ...


class ClienteJSONEscrita(Protocol):
    def enviar_json(self, url: str, corpo: Mapping[str, object]) -> None:
        ...


class ClienteJSONUrllib(ClienteJSONLeitura, ClienteJSONEscrita):
```

```python
class PokeAPIClient(PokemonCatalogo):
    def __init__(self, http: ClienteJSONLeitura, ...) -> None:

class MensageiroBrokerHTTP(MensageiroBroker):
    def __init__(self, http: ClienteJSONEscrita, url_base: str) -> None:
```

**Um repositório por caso de uso.** A distribuição precisa apenas criar e buscar jogadores; a posse precisa buscar por carta e salvar transferências. Cada serviço declara a própria porta, e a implementação em memória atende às duas.

[`distribuicao_cartas_ports.py`](./src/cartas/service/distribuicao_cartas_ports.py) e [`posse_carta_ports.py`](./src/cartas/service/posse_carta_ports.py) (docstrings omitidas):

```python
# distribuicao_cartas_ports.py
class JogadorCartasRepository(Protocol):
    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None: ...
    def salvar(self, jogador: Jogador) -> bool: ...
```

```python
# posse_carta_ports.py
class JogadorCartasRepository(Protocol):
    def buscar_por_id(self, jogador_id: UUID) -> Jogador | None: ...
    def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None: ...
    def salvar_transferencia(self, origem: Jogador, destino: Jogador) -> None: ...
```

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

```python
class JogadorCartasRepositoryImpl(RepositorioDeDistribuicao, RepositorioDePosse):
```

O mesmo vale para [`Consumer[T]`](./src/cartas/presentation/consumers/consumer.py), que tem um único método (`consumir`) - tudo de que o roteador precisa.

### D - Dependency Inversion Principle (DIP)

Módulos de alto nível não dependem de módulos de baixo nível; ambos dependem de abstrações, e as abstrações pertencem ao núcleo. No projeto:

- As portas de saída (`PokemonCatalogo`, `JogadorCartasRepository`, `Publisher`) são `Protocol`s definidos no pacote [`service`](./src/cartas/service/), e não em `integration` ou `repository`.
- `service` e `model` não importam nada de `integration`, `repository` ou `presentation`.
- Os adaptadores importam as portas do núcleo para implementá-las: a dependência aponta de fora para dentro.
- `presentation` depende apenas dos contratos dos serviços (`DistribuicaoCartasService`, `PosseCartaService`), nunca das classes `Impl`.

```text
presentation ──► service (contratos)  ◄── integration
                    │                 ◄── repository
                    ▼
                  model
```

O serviço recebe apenas abstrações no construtor.

[`distribuicao_cartas.py`](./src/cartas/service/distribuicao_cartas.py):

```python
class DistribuicaoCartasServiceImpl(DistribuicaoCartasService):
    def __init__(
        self,
        catalogo: PokemonCatalogo,
        repositorio: JogadorCartasRepository,
        publisher: Publisher[EventoCartasDistribuidas],
        sorteio: SorteioStrategy,
    ) -> None:
```

O adaptador importa a porta do núcleo e a implementa.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
from cartas.service.distribuicao_cartas_ports import PokemonCatalogo


class PokeAPIClient(PokemonCatalogo):
```

O adaptador de entrada também depende do contrato, e não da implementação do serviço.

[`jogador_criado_consumer.py`](./src/cartas/presentation/consumers/jogador_criado_consumer.py):

```python
class JogadorCriadoConsumer(Consumer[EventoJogadorCriado]):
    def __init__(self, servico: DistribuicaoCartasService) -> None:
        self._servico = servico
```

A escolha das implementações concretas fica na raiz de composição, descrita em [Injeção de dependência](#injeção-de-dependência).

### Lei de Demeter

A Lei de Demeter (ou princípio do menor conhecimento) diz que um método deve conversar apenas com seus colaboradores diretos - o próprio objeto, seus atributos, seus parâmetros e os objetos que cria - em vez de percorrer a estrutura interna de outros objetos (`a.b().c().d()`).

**Perguntar ao jogador, não às cartas dele.** Para saber se um jogador possui um Pokémon, o serviço de posse pergunta ao `Jogador`, e não percorre `jogador.cartas` comparando `carta.pokemon_id`. A regra fica em um único lugar, e é a mesma que `adicionar_carta` usa para impedir Pokémon repetidos.

[`posse_carta.py`](./src/cartas/service/posse_carta.py) e [`jogador.py`](./src/cartas/model/jogador.py):

```python
def consultar_posse_pokemon(self, jogador_id: UUID, pokemon_id: int) -> bool:
    return self._buscar_jogador(jogador_id).possui_pokemon(pokemon_id)
```

```python
def possui_pokemon(self, pokemon_id: int) -> bool:
    return any(carta.pokemon_id == pokemon_id for carta in self._cartas.values())

def adicionar_carta(self, carta: Carta) -> None:
    if carta.carta_id in self._cartas:
        raise ValueError("O jogador já possui esta carta.")
    if self.possui_pokemon(carta.pokemon_id):
        raise ValueError("O jogador já possui uma carta deste Pokémon.")
    self._cartas[carta.carta_id] = carta
```

**Cada elo conhece só o próximo.** Na publicação de eventos, `CartasDistribuidasPublisher` conhece apenas o `MensageiroBroker`; não sabe que existe HTTP nem qual é a URL. `MensageiroBrokerHTTP` conhece apenas o `ClienteJSONEscrita`; não sabe que a implementação usa `urllib`. Nenhuma classe acessa o colaborador do seu colaborador.

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py) e [`mensageiro_broker.py`](./src/cartas/integration/mensageiro_broker.py):

```python
self._mensageiro.enviar(self._topico, serializar_cartas_distribuidas(evento))
```

```python
url = f"{self._url_base}/eventos/{quote(topico, safe='')}"
try:
    self._http.enviar_json(url, mensagem)
```

**Adaptadores de entrada finos.** Consumers e controller recebem dados prontos (o evento convertido ou os parâmetros da rota) e fazem uma única chamada ao serviço injetado.

[`troca_concluida_consumer.py`](./src/cartas/presentation/consumers/troca_concluida_consumer.py):

```python
def consumir(self, evento: EventoTrocaConcluida) -> None:
    self._servico.atualizar_posse(evento.carta_id, evento.novo_jogador_id)
```

O acesso a campos de `Carta`, `Pokemon` e dos eventos (como `evento.carta_id`) não viola a lei: são dataclasses imutáveis, estruturas de dados sem comportamento, e a Lei de Demeter trata de navegar por objetos com comportamento.

## Design Patterns

Os padrões GoF identificados diretamente no código são:

| Padrão                  | Categoria      | Aplicação                                              |
| ----------------------- | -------------- | ------------------------------------------------------ |
| [Adapter](#adapter)     | Estrutural     | Adapta payloads externos aos tipos usados pelo serviço |
| [Strategy](#strategy)   | Comportamental | Permite variar o algoritmo de sorteio                  |

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

### Strategy

A estratégia de sorteio encapsula como os Pokémon são selecionados. O serviço depende do contrato `SorteioStrategy`, podendo substituir o algoritmo sem alterar a distribuição.

[`sorteio.py`](./src/cartas/service/sorteio.py):

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

## Outros padrões e conceitos de projeto

Os itens abaixo também aparecem no código, mas não fazem parte do catálogo GoF usado acima. Repository e Data Mapper tratam da persistência; DTO e Gateway são padrões de aplicação/integração; Publisher/Producer descreve a publicação de mensagens.

| Padrão/conceito                          | Aplicação neste serviço                                       | Código                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [Repository](#repository)                | Mantém a posse das cartas e as consultas por jogador ou carta | [`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py)          |
| [Data Mapper](#data-mapper)              | Converte entre `Jogador` e a estrutura em memória             | [`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py)          |
| [DTO](#dto)                              | Transporta dados da API sem expor o modelo de domínio         | [`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py)                               |
| [Gateway](#gateway)                      | Encapsula requisições ao catálogo PokéAPI                     | [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py)                           |
| [Publisher/Producer](#publisherproducer) | Formata e encaminha eventos de distribuição                   | [`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py) |

### Repository

O repositório centraliza a leitura e a gravação dos jogadores e suas cartas. A implementação atual mantém os dados em memória e sincroniza o acesso com um lock.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

```python
def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None:
    with self._lock:
        jogador_id = self._dono_por_carta.get(carta_id)
        if jogador_id is None:
            return None
        return _montar_jogador(jogador_id, self._cartas_por_jogador[jogador_id])
```

### Data Mapper

O repositório converte entre sua estrutura interna e os objetos do domínio, mantendo os serviços independentes da forma de armazenamento.

[`jogador_cartas_repository.py`](./src/cartas/repository/jogador_cartas_repository.py):

```python
def _extrair_cartas(jogador: Jogador) -> CartasPorId:
    return {carta.carta_id: carta for carta in jogador.listar_cartas()}

def _montar_jogador(jogador_id: UUID, cartas: CartasPorId) -> Jogador:
    return Jogador(jogador_id, cartas.values())
```

### DTO

DTOs representam os dados que atravessam a fronteira HTTP, mantendo o formato da requisição separado das entidades e regras do domínio.

[`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py):

```python
@dataclass(frozen=True)
class AtualizarPosseRequestDTO:
    carta_id: UUID
    novo_jogador_id: UUID
```

### Gateway

`PokeAPIClient` implementa o contrato do catálogo e isola detalhes de HTTP e JSON. A composição local usa `CatalogoPokemonMock`; o gateway está disponível para integração futura.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
    return mapear_pokemon(
        self._obter_json(f"{self._url_base}/pokemon/{pokemon_id}/")
    )
```

### Publisher/Producer

O publisher serializa o evento de distribuição e delega o envio à porta de mensageria. Na execução local, `PublisherMock` registra os eventos em memória, sem conexão com o Broker.

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py):

```python
def publicar(self, evento: EventoCartasDistribuidas) -> None:
    self._mensageiro.enviar(
        self._topico, serializar_cartas_distribuidas(evento)
    )
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
