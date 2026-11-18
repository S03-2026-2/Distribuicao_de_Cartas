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
