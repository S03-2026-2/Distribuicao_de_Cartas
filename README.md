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
