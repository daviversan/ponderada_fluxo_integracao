# Caffeine Ratio

Aplicação web que classifica produtos pelo **ratio cafeína/preço** — encontre o melhor custo-benefício de cafeína.

## Estrutura do Projeto

```
ponderada_fluxo_integracao/
├── backend/                   # API REST (FastAPI + SQLite)
│   ├── app/
│   │   ├── main.py            # Entry point, CORS, middleware, exception handlers
│   │   ├── database.py        # SQLAlchemy engine, sessão, PRAGMAs
│   │   ├── models.py          # Modelo Product (ORM)
│   │   ├── schemas.py         # Schemas Pydantic
│   │   ├── crud.py            # Operações CRUD
│   │   ├── routers/
│   │   │   └── products.py    # Endpoints REST
│   │   └── services/
│   │       ├── ratio.py       # Cálculo de ratio cafeína/preço
│   │       └── external_api.py # Integração Open Food Facts + USDA
│   ├── tests/                 # Testes (pytest)
│   └── requirements.txt
├── frontend/                  # Interface web (Next.js)
│   └── src/
│       ├── app/               # Páginas (App Router)
│       ├── components/        # SearchBar, RankedList, ProductCard, AddProductForm
│       └── lib/api.ts         # Cliente HTTP
└── docs/
    ├── INTEGRATION.md         # Arquitetura de integração
    └── QUALITY_CONTROL.md     # Controle de qualidade
```

## Pré-requisitos

- **Python** 3.11+
- **Node.js** 18+
- **npm** ou **yarn**

## Instalação e Execução

### Backend

```bash
cd backend
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz do projeto (opcional):

```env
USDA_API_KEY=sua_chave_aqui    # Padrão: DEMO_KEY
DATABASE_URL=sqlite:///./products.db
```

> **Chave da API USDA**: a aplicação funciona com a `DEMO_KEY` padrão, mas possui limites de uso mais restritivos. Para uso em produção, obtenha uma chave gratuita em [https://api.data.gov/signup/](https://api.data.gov/signup/). Basta informar nome e e-mail — a chave é enviada instantaneamente.

Iniciar o servidor:

```bash
uvicorn app.main:app --reload --port 8000
```

O backend estará disponível em `http://localhost:8000`. Documentação interativa em `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend estará disponível em `http://localhost:3000`.

## Referência da API

Todos os endpoints estão sob o prefixo `/api/v1/products`.

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/` | Criar produto |
| `GET` | `/` | Listar todos os produtos |
| `GET` | `/{id}` | Buscar produto por ID |
| `PUT` | `/{id}` | Atualizar produto |
| `DELETE` | `/{id}` | Remover produto |
| `GET` | `/search?q=termo` | Buscar por nome |
| `GET` | `/ranked` | Listar ordenado por ratio (maior primeiro) |
| `GET` | `/lookup?q=termo` | Consultar cafeína em APIs externas |

### Criar Produto

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Red Bull 250ml",
    "price_cents": 599,
    "caffeine_mg": 80,
    "currency": "USD"
  }'
```

Resposta (201):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Red Bull 250ml",
  "price_cents": 599,
  "caffeine_mg": 80,
  "caffeine_currency_ratio": 13.36,
  "currency": "USD"
}
```

### Ranking

```bash
curl http://localhost:8000/api/v1/products/ranked
```

Retorna a lista de produtos ordenada por `caffeine_currency_ratio` decrescente.

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Testes

```bash
cd backend
pytest -v
```

Os testes utilizam banco SQLite in-memory e cobrem:

- Cálculo de ratio (unitário)
- Operações CRUD + integridade do banco (integração)
- Todos os endpoints HTTP (integração com mock de APIs externas)

## Tecnologias

| Camada | Stack |
|--------|-------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Backend | FastAPI, SQLAlchemy, Pydantic, httpx |
| Banco de Dados | SQLite (modo WAL) |
| APIs Externas | Open Food Facts, USDA FoodData Central |
| Testes | pytest, pytest-asyncio |
