# Controle de Qualidade

## Tempos e Performance

### Middleware de Logging

Toda requisição HTTP é instrumentada pelo middleware em `main.py`, que registra:

- **Request ID** (UUID) — incluído no header `X-Request-ID` da resposta
- **Método e rota** da requisição
- **Status code** da resposta
- **Tempo de execução** em milissegundos

Exemplo de log:

```
2026-03-11 10:30:15 [INFO] app: [a1b2c3d4] GET /api/v1/products/ranked -> 200 (12.45ms)
```

### Timeouts de APIs Externas

| API | Timeout | Comportamento em caso de timeout |
|-----|---------|----------------------------------|
| Open Food Facts | 5s | Log de warning + fallback para USDA |
| USDA (busca + detalhes) | 5s por requisição | Log de warning + retorna lista vazia |

### Tempo de Resposta Esperado

| Operação | Tempo típico |
|----------|-------------|
| CRUD local (SQLite) | < 10ms |
| Busca/ranking | < 20ms |
| Lookup externo (cache miss) | 500ms – 5s |

## Protocolos

### Comunicação Frontend ↔ Backend

| Aspecto | Especificação |
|---------|---------------|
| Protocolo | HTTP/1.1 (REST) |
| Formato | JSON (`Content-Type: application/json`) |
| Prefixo de versão | `/api/v1/` |
| CORS | Permitido para todas as origens (`*`) |

### Formato de Resposta de Sucesso

```json
{
  "id": "uuid-v4",
  "name": "Red Bull 250ml",
  "price_cents": 599,
  "caffeine_mg": 80,
  "caffeine_currency_ratio": 13.36,
  "currency": "USD"
}
```

### Formato de Resposta de Erro

Todas as respostas de erro seguem o mesmo formato estruturado:

```json
{
  "detail": "Mensagem descritiva do erro",
  "status_code": 404,
  "request_id": "a1b2c3d4-..."
}
```

### Códigos HTTP Utilizados

| Código | Significado | Quando |
|--------|-------------|--------|
| 200 | OK | Leitura/atualização bem-sucedida |
| 201 | Created | Produto criado |
| 204 | No Content | Produto deletado |
| 400 | Bad Request | Valor inválido (ex: preço ≤ 0) |
| 404 | Not Found | Produto não encontrado |
| 409 | Conflict | Violação de constraint do banco |
| 422 | Unprocessable Entity | Falha de validação Pydantic |
| 500 | Internal Server Error | Erro não tratado |

## Versionamento

### API

A API usa versionamento via prefixo de rota:

- Versão atual: **v1** (`/api/v1/products/...`)
- Versão semântica do app: **1.0.0** (definida no `FastAPI(version="1.0.0")`)

### Dependências

Todas as dependências do backend estão fixadas em `requirements.txt` com versões exatas:

| Pacote | Versão |
|--------|--------|
| fastapi | 0.115.6 |
| uvicorn | 0.34.0 |
| sqlalchemy | 2.0.36 |
| pydantic | 2.10.4 |
| httpx | 0.28.1 |
| python-dotenv | 1.0.1 |
| pytest | 8.3.4 |
| pytest-asyncio | 0.25.0 |

Dependências do frontend definidas em `package.json`:

| Pacote | Versão |
|--------|--------|
| next | 16.1.6 |
| react | 19.2.3 |
| react-dom | 19.2.3 |
| tailwindcss | ^4 |
| typescript | ^5 |

## Tratamento de Exceções

### Hierarquia de Exception Handlers (Backend)

O `main.py` registra handlers globais na seguinte ordem de prioridade:

| Exceção | Status | Resposta |
|---------|--------|----------|
| `StarletteHTTPException` | Variável (404, 405, etc.) | `detail` da exceção original |
| `RequestValidationError` | 422 | Lista de erros de validação do Pydantic |
| `IntegrityError` (SQLAlchemy) | 409 | "Database integrity constraint violated" |
| `ValueError` | 400 | Mensagem da exceção (ex: "price_cents must be positive") |
| `Exception` (genérica) | 500 | "Internal server error" (detalhes logados no servidor) |

Todos os handlers incluem o `request_id` na resposta para rastreabilidade.

### Validação de Entrada

#### Backend (Pydantic + DB Constraints)

| Campo | Regra Pydantic | Constraint SQLite |
|-------|----------------|-------------------|
| `name` | `min_length=1, max_length=255` | `NOT NULL` |
| `price_cents` | `gt=0` | `CHECK(price_cents > 0)` |
| `caffeine_mg` | `ge=0` | `CHECK(caffeine_mg >= 0)` |
| `currency` | Enum `USD` / `BRL` | `CHECK(currency IN ('USD', 'BRL'))` |

A validação em duas camadas (Pydantic + SQLite) garante integridade mesmo em caso de bypass da API.

#### Frontend

- Preço: validado como número positivo (`> 0`) antes do envio
- Cafeína: validado como inteiro não-negativo (`>= 0`)
- Nome: campo obrigatório (`required`)
- Moeda: seleção restrita a USD/BRL via `<select>`

### Cadeia de Fallback — APIs Externas

```
lookup_caffeine(query)
│
├─ 1. Open Food Facts
│     ├── Sucesso com dados → retorna resultados
│     ├── Sucesso sem dados → próximo
│     ├── Timeout (5s) → log warning + próximo
│     ├── HTTP error → log warning + próximo
│     └── Erro genérico → log warning + próximo
│
├─ 2. USDA FoodData Central (duas etapas)
│     ├── POST search (filtrado por Survey/SR Legacy) → obtém fdcIds
│     ├── POST foods (nutriente 262) → obtém cafeína em lote
│     ├── Sucesso → retorna resultados com caffeine_mg
│     ├── Timeout (5s) → log warning
│     ├── HTTP error → log warning
│     └── Erro genérico → log warning
│
└─ 3. Retorna [] (lista vazia — lookup é best-effort)
```

A falha na consulta externa **nunca impede** a criação do produto. O usuário pode sempre inserir manualmente o valor de cafeína.

### Transações do Banco de Dados

- Cada operação CRUD executa dentro de uma sessão SQLAlchemy com `autocommit=False`
- `commit()` é chamado explicitamente após cada operação
- Em caso de erro, o SQLAlchemy faz rollback automaticamente ao fechar a sessão
- O modo WAL do SQLite permite leituras concorrentes durante escritas

### Frontend — Tratamento de Erros

| Cenário | Comportamento |
|---------|---------------|
| Falha ao carregar produtos | Banner vermelho com mensagem + botão "Retry" |
| Falha ao deletar produto | Mensagem de erro exibida no topo da lista |
| Falha ao criar produto | Mensagem de erro no formulário |
| Falha no lookup de cafeína | Silenciosa (best-effort); usuário preenche manualmente |
| Lista vazia | Mensagem amigável com instrução para adicionar produto |

## Testes

### Estrutura de Testes

```
backend/tests/
├── conftest.py          # Fixtures: banco in-memory, sessão, TestClient
├── test_ratio.py        # Testes unitários do cálculo de ratio
├── test_crud.py         # Testes das operações CRUD + integridade do banco
└── test_endpoints.py    # Testes de integração dos endpoints HTTP
```

### Execução

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

### Categorias de Teste

| Arquivo | Tipo | O que testa |
|---------|------|-------------|
| `test_ratio.py` | Unitário | Cálculo `caffeine_mg / (price_cents / 100)`, divisão por zero, valores negativos |
| `test_crud.py` | Integração (DB) | Criar, ler, atualizar, deletar, buscar, ranking, constraints do banco |
| `test_endpoints.py` | Integração (HTTP) | Todos os 8 endpoints, status codes, payloads, lookup com mock |

### Banco de Testes

Os testes utilizam um banco SQLite **in-memory** (`:memory:`) configurado em `conftest.py`, garantindo isolamento total do banco de produção.
