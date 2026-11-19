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

### Arquitetura em camadas — fronteira da apresentação

**Onde / Como aparece:** `CartasController` recebe o contrato `PosseCartaService`, delega as operações e mapeia os resultados para DTOs de apresentação. Isso demonstra a separação na fronteira da apresentação.

**Significado e motivação:** organizar a apresentação separadamente permite que o controller coordene a entrada e a saída sem assumir responsabilidades do serviço.

**Exemplo** ([`cartas_controller.py`](./src/cartas/presentation/controllers/cartas_controller.py)):

```python
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
```

### MVC — não completo nesta contribuição

**Onde / Como aparece:** foi adicionado o componente Controller. A contribuição não adiciona componentes Model ou View; portanto, não reivindica a implementação completa de MVC.

**Significado e motivação:** MVC separa o controle das interações, o modelo e a apresentação. Essa separação só pode ser considerada completa quando os componentes correspondentes estiverem presentes.

**Exemplo** ([`cartas_controller.py`](./src/cartas/presentation/controllers/cartas_controller.py), contribuição da Pessoa 1):

```python
class CartasController:
    def atualizar_posse(self, request: AtualizarPosseRequestDTO) -> None:
        self._posse_carta_service.atualizar_posse(
            request.carta_id, request.novo_jogador_id
        )
```

## Design Patterns

### Injeção de Dependência — aplicada

**Onde / Como aparece:** `CartasController` recebe `PosseCartaService` pelo construtor, em vez de instanciar uma implementação. O teste do controller também injeta um mock desse contrato.

**Significado e motivação:** fornecer as dependências de fora reduz o acoplamento a uma implementação específica e facilita substituir o serviço por um mock nos testes.

**Exemplo** ([`cartas_controller.py`](./src/cartas/presentation/controllers/cartas_controller.py) e [`test_cartas_controller.py`](./tests/unit/presentation/test_cartas_controller.py)):

```python
def __init__(self, posse_carta_service: PosseCartaService) -> None:
    self._posse_carta_service = posse_carta_service
```

```python
self.service = Mock(spec=PosseCartaService)
self.controller = CartasController(self.service)
```

### DTO (Data Transfer Object) — aplicado

**Onde / Como aparece:** [`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py), define DTOs imutáveis de requisição e resposta. O controller usa esses objetos na fronteira da apresentação.

**Significado e motivação:** DTOs transportam dados entre fronteiras da aplicação sem incorporar regras de negócio, mantendo o formato da apresentação separado do modelo de domínio.

**Exemplo** ([`posse_carta.py`](./src/cartas/presentation/dtos/posse_carta.py)):

```python
@dataclass(frozen=True)
class ConsultarPosseCartaRequestDTO:
    jogador_id: UUID
    carta_id: UUID
```

Os JSON Schemas em [`schemas/`](./src/cartas/presentation/schemas/) e o validador em [`schema_validator.py`](./src/cartas/presentation/schema_validator.py). Eles definem e verificam formatos de dados.
