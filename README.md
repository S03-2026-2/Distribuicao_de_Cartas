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

## Organização do serviço

`presentation` recebe requisições HTTP, valida os dados e delega o trabalho aos serviços. `service` contém os casos de uso e os contratos de suas dependências. `model` representa jogadores, cartas e eventos. `integration` contém adaptadores externos e mocks. A composição local está em [`main.py`](./src/cartas/main.py).

## Padrões e responsabilidades

| Padrão | Aplicação neste serviço | Código |
|---|---|---|
| [Injeção de dependência](#injeção-de-dependência) | Monta serviços com implementações substituíveis de catálogo, persistência e publicação | [`main.py`](./src/cartas/main.py) |
| [Repository](#repository) | Mantém a posse das cartas e as consultas por jogador ou carta | [`jogador_cartas_repository.py`](./src/cartas/service/jogador_cartas_repository.py) |
| [Data Mapper](#data-mapper) | Converte entre os objetos `Jogador` e a estrutura em memória | [`jogador_cartas_repository.py`](./src/cartas/service/jogador_cartas_repository.py) |
| [Strategy](#strategy) | Seleciona cinco Pokémon sem prender o serviço a um algoritmo de sorteio | [`sorteio.py`](./src/cartas/service/sorteio.py) |
| [DTO](#dto) | Transporta dados da API sem expor o modelo de domínio | [`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py) |
| [Adapter](#adapter) | Converte mensagens externas e respostas da PokéAPI para tipos do sistema | [`conversores.py`](./src/cartas/presentation/consumers/conversores.py), [`mapeador_pokeapi.py`](./src/cartas/integration/mapeador_pokeapi.py) |
| [Gateway](#gateway) | Encapsula as requisições ao catálogo PokéAPI | [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) |
| [Decorator](#decorator) | Acrescenta cache ao catálogo sem alterar o gateway | [`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py) |
| [Publisher/Producer](#publisherproducer) | Formata e encaminha eventos de distribuição | [`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py) |

### Injeção de dependência

As dependências são fornecidas na composição da aplicação. Os serviços dependem de contratos, permitindo trocar integrações reais por mocks sem alterar as regras de negócio.

[`main.py`](./src/cartas/main.py):

```python
repositorio = JogadorCartasRepositoryImpl()
distribuicao = DistribuicaoCartasServiceImpl(
    CatalogoPokemonMock(), repositorio, PublisherMock(), SorteioAleatorioStrategy()
)
posse = PosseCartaServiceImpl(repositorio)
```

### Repository

O repositório centraliza a leitura e a gravação dos jogadores e suas cartas. A implementação atual mantém os dados em memória e sincroniza o acesso com um lock.

[`jogador_cartas_repository.py`](./src/cartas/service/jogador_cartas_repository.py):

```python
def buscar_por_carta_id(self, carta_id: UUID) -> Jogador | None:
    with self._lock:
        jogador_id = self._dono_por_carta.get(carta_id)
        if jogador_id is None:
            return None
        return _montar_jogador(jogador_id, self._cartas_por_jogador[jogador_id])
```

### Data Mapper

O repositório converte entre seu armazenamento interno e os objetos de domínio. Assim, os serviços trabalham com `Jogador`, sem depender da estrutura usada para guardar as cartas.

[`jogador_cartas_repository.py`](./src/cartas/service/jogador_cartas_repository.py):

```python
def _extrair_cartas(jogador: Jogador) -> CartasPorId:
    return {carta.carta_id: carta for carta in jogador.listar_cartas()}

def _montar_jogador(jogador_id: UUID, cartas: CartasPorId) -> Jogador:
    return Jogador(jogador_id, cartas.values())
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

### DTO

DTOs representam os dados que atravessam a fronteira HTTP, mantendo o formato da requisição separado das entidades e regras do domínio.

[`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py):

```python
@dataclass(frozen=True)
class AtualizarPosseRequestDTO:
    carta_id: UUID
    novo_jogador_id: UUID
```

### Adapter

O conversor adapta o payload recebido para um evento tipado usado pelo restante da aplicação. O mapeador da PokéAPI faz a mesma separação para dados do catálogo externo.

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

### Gateway

`PokeAPIClient` implementa o contrato do catálogo e isola detalhes de HTTP e JSON. A execução local usa `CatalogoPokemonMock`; o gateway permanece disponível para integração futura.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
def buscar_pokemon_por_id(self, pokemon_id: int) -> Pokemon:
    return mapear_pokemon(
        self._obter_json(f"{self._url_base}/pokemon/{pokemon_id}/")
    )
```

### Decorator

`CatalogoPokemonEmCache` envolve outro catálogo e adiciona cache sem modificar o gateway. Os Pokémon consultados ficam em cache; a lista de IDs expira após 24 horas.

[`catalogo_pokemon.py`](./src/cartas/integration/catalogo_pokemon.py):

```python
pokemon = self._pokemons.get(pokemon_id)
if pokemon is None:
    pokemon = self._catalogo.buscar_pokemon_por_id(pokemon_id)
    self._pokemons[pokemon_id] = pokemon
return pokemon
```

### Publisher/Producer

O publisher serializa o evento de distribuição e o envia pelo contrato de mensageria, sem acoplar o serviço ao transporte. No modo local, `PublisherMock` registra os eventos em memória.

[`cartas_distribuidas_publisher.py`](./src/cartas/integration/cartas_distribuidas_publisher.py):

```python
def publicar(self, evento: EventoCartasDistribuidas) -> None:
    self._mensageiro.enviar(
        self._topico, serializar_cartas_distribuidas(evento)
    )
```

## Endpoints disponíveis

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/eventos/jogador-criado` | Recebe a criação de jogador e distribui cinco cartas |
| `POST` | `/eventos/troca-concluida` | Atualiza a posse após uma troca |
| `GET` | `/jogadores/{jogador_id}/cartas` | Lista as cartas do jogador |
| `GET` | `/jogadores/{jogador_id}/cartas/{carta_id}/posse` | Verifica a posse de uma carta |
| `PUT` | `/cartas/{carta_id}/posse` | Transfere uma carta para outro jogador |

O evento `jogador-criado` recebe `jogador_id`. O evento `troca-concluida` recebe `carta_id`, `novo_jogador_id` e `troca_id`. Exemplo:

```json
{
  "carta_id": "3b2a0000-0000-0000-0000-000000000001",
  "novo_jogador_id": "8f1c0000-0000-0000-0000-000000000002",
  "troca_id": "a5120000-0000-0000-0000-000000000003"
}
```
