# Arquitetura de Integração

## Visão Geral

O **Caffeine Ratio** é uma aplicação web que classifica produtos pela relação cafeína/preço, ajudando o usuário a encontrar o melhor custo-benefício de cafeína. A arquitetura segue o padrão de camadas com separação clara entre apresentação, lógica de negócios, persistência e integração com APIs externas.

```
┌──────────────────────────────────────────────────────┐
│                  Frontend (Next.js)                   │
│   SearchBar  ·  RankedList  ·  ProductCard  ·  Form  │
└──────────────────────┬───────────────────────────────┘
                       │  HTTP / REST (JSON)
                       ▼
┌──────────────────────────────────────────────────────┐
│               Backend (FastAPI)                       │
│  Router → Service (CRUD + Ratio) → SQLAlchemy ORM    │
│                    │                                  │
│            External API Service                       │
└─────┬──────────────┼─────────────────────────────────┘
      │              │  HTTP (httpx)
      ▼              ▼
┌──────────┐  ┌─────────────────────────────────┐
│  SQLite  │  │  Open Food Facts  ·  USDA API   │
│  (WAL)   │  │  (enriquecimento de dados)      │
└──────────┘  └─────────────────────────────────┘
```

## Camadas

### 1. Apresentação (Frontend)

| Tecnologia | Versão |
|------------|--------|
| Next.js    | 16.x   |
| React      | 19.x   |
| TypeScript | 5.x    |
| Tailwind CSS | 4.x  |

O frontend utiliza o **App Router** do Next.js com componentes client-side (`"use client"`). A comunicação com o backend é feita via uma classe `ApiClient` centralizada em `lib/api.ts`.

### 2. Lógica de Negócios (Backend)

| Tecnologia | Versão |
|------------|--------|
| Python     | 3.11+  |
| FastAPI    | 0.115.6 |
| Pydantic   | 2.10.4 |
| SQLAlchemy | 2.0.36 |
| httpx      | 0.28.1 |

O backend é uma API REST organizada em camadas:

- **Router** (`routers/products.py`) — define os endpoints HTTP
- **CRUD** (`crud.py`) — operações de banco de dados
- **Services** — cálculo de ratio (`services/ratio.py`) e consulta a APIs externas (`services/external_api.py`)
- **Schemas** (`schemas.py`) — validação de entrada/saída com Pydantic
- **Models** (`models.py`) — modelo ORM SQLAlchemy

### 3. Persistência (Banco de Dados)

SQLite com modo **WAL** (Write-Ahead Logging) para garantias ACID. Configurado via PRAGMAs no evento `connect` do SQLAlchemy:

```python
PRAGMA journal_mode=WAL
PRAGMA foreign_keys=ON
```

### 4. Integração com APIs Externas

APIs externas são utilizadas para **sugerir o teor de cafeína** de um produto. O preço é sempre informado pelo usuário.

## Módulos e Componentes

### Backend — Módulos

| Módulo | Arquivo | Responsabilidade |
|--------|---------|------------------|
| App Entry | `main.py` | Inicialização, CORS, middleware de logging, tratamento de exceções |
| Database | `database.py` | Engine SQLAlchemy, sessão, PRAGMAs SQLite |
| Models | `models.py` | Modelo `Product` com constraints (currency, price > 0, caffeine >= 0) |
| Schemas | `schemas.py` | Validação Pydantic: `ProductCreate`, `ProductUpdate`, `ProductResponse`, `CaffeineLookupResult`, `ErrorResponse` |
| CRUD | `crud.py` | Operações: criar, ler, listar, atualizar, deletar, buscar, ranking |
| Router | `routers/products.py` | 8 endpoints REST sob `/api/v1/products` |
| Ratio | `services/ratio.py` | Cálculo: `caffeine_mg / (price_cents / 100)` |
| External API | `services/external_api.py` | Consulta Open Food Facts (primário) e USDA (fallback) |

### Frontend — Componentes

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| `RankedList` | `components/RankedList.tsx` | Lista principal: busca produtos ranqueados, gerencia estados de loading/erro/vazio, integra busca e formulário |
| `SearchBar` | `components/SearchBar.tsx` | Campo de busca com debounce (300ms) e botão de limpar |
| `ProductCard` | `components/ProductCard.tsx` | Card de produto: nome, preço formatado, cafeína, ratio, badge de moeda, botão de exclusão |
| `AddProductForm` | `components/AddProductForm.tsx` | Formulário de criação com auto-sugestão de cafeína via lookup externo |
| `ApiClient` | `lib/api.ts` | Cliente HTTP centralizado com tratamento de erros tipado |

## Serviços e Integrações

### Endpoints da API (Backend)

Todos sob o prefixo `/api/v1/products`:

| Método | Rota | Descrição | Status |
|--------|------|-----------|--------|
| POST | `/` | Criar produto | 201 |
| GET | `/` | Listar todos | 200 |
| GET | `/{id}` | Buscar por ID | 200 / 404 |
| PUT | `/{id}` | Atualizar produto | 200 / 404 |
| DELETE | `/{id}` | Remover produto | 204 / 404 |
| GET | `/search?q=` | Buscar por nome (case-insensitive) | 200 |
| GET | `/ranked` | Listar ordenado por ratio (desc) | 200 |
| GET | `/lookup?q=` | Consultar cafeína em APIs externas | 200 |

Endpoint de saúde: `GET /health` → `{"status": "ok"}`

### Integração com Open Food Facts (Primária)

- **URL**: `https://world.openfoodfacts.org/cgi/search.pl`
- **Autenticação**: nenhuma
- **Dados extraídos**: `product.nutriments.caffeine_100g` (convertido para mg por porção)
- **Limite**: 5 resultados por consulta
- **Timeout**: 5 segundos

### Integração com USDA FoodData Central (Fallback)

A integração com o USDA utiliza um fluxo em duas etapas para obter dados de cafeína:

1. **Busca** (POST `https://api.nal.usda.gov/fdc/v1/foods/search`): pesquisa alimentos filtrados por `dataType: ["Survey (FNDDS)", "SR Legacy"]`, que são os tipos de dados que contêm informações nutricionais completas (incluindo cafeína). Alimentos do tipo "Branded" só possuem nutrientes de rótulo e não incluem cafeína.
2. **Detalhes em lote** (POST `https://api.nal.usda.gov/fdc/v1/foods`): busca os dados de cafeína (nutriente número 262) para todos os `fdcId` retornados na etapa anterior em uma única requisição.

- **Autenticação**: chave de API via variável de ambiente `USDA_API_KEY` (padrão: `DEMO_KEY`). Obtenha uma chave gratuita em [https://api.data.gov/signup/](https://api.data.gov/signup/)
- **Limite**: 5 resultados por consulta
- **Timeout**: 5 segundos (por requisição)

### Estratégia de Fallback

```
1. Consultar Open Food Facts
   ├── Sucesso com resultados → retornar
   ├── Sucesso sem resultados → ir para 2
   ├── Timeout → ir para 2
   └── Erro HTTP / outro → ir para 2

2. Consultar USDA
   ├── Sucesso → retornar
   └── Falha → retornar lista vazia []
```

## Software Utilizado

| Camada | Tecnologia | Propósito |
|--------|------------|-----------|
| Frontend | Next.js 16 + React 19 | Interface do usuário, SSR/CSR |
| Frontend | TypeScript 5 | Tipagem estática |
| Frontend | Tailwind CSS 4 | Estilização utilitária |
| Backend | FastAPI 0.115.6 | Framework web assíncrono |
| Backend | Pydantic 2.10.4 | Validação e serialização |
| Backend | SQLAlchemy 2.0.36 | ORM e gerenciamento de sessões |
| Backend | httpx 0.28.1 | Cliente HTTP assíncrono |
| Persistência | SQLite (WAL) | Banco de dados relacional embarcado |
| Testes | pytest 8.3.4 | Framework de testes |
| Testes | pytest-asyncio 0.25.0 | Suporte a testes assíncronos |
| Runtime | Uvicorn 0.34.0 | Servidor ASGI |

## Fluxo de Dados

### Criar Produto

```
Usuário preenche formulário
  → Frontend POST /api/v1/products (JSON)
    → Router recebe ProductCreate (validado por Pydantic)
      → CRUD calcula ratio via services/ratio.py
        → ratio = caffeine_mg / (price_cents / 100.0)
      → CRUD insere no SQLite (commit + refresh)
    → Router retorna ProductResponse (201)
  → Frontend adiciona card à lista ordenada
```

### Consultar Cafeína (Auto-sugestão)

```
Usuário digita nome do produto (≥ 3 caracteres)
  → Frontend GET /api/v1/products/lookup?q=... (após 1s de debounce)
    → Router chama external_api.lookup_caffeine()
      → Tenta Open Food Facts (GET search)
        → Sucesso? Retorna resultados
        → Falha? Tenta USDA como fallback:
          1. POST search (filtrado por Survey/SR Legacy)
          2. POST foods (busca cafeína em lote por fdcId)
    → Router retorna List[CaffeineLookupResult]
  → Frontend exibe sugestões e auto-preenche campo de cafeína
```

### Ranking

```
Página carrega
  → Frontend GET /api/v1/products/ranked
    → CRUD consulta SQLite ORDER BY caffeine_currency_ratio DESC
    → Router retorna lista ordenada
  → Frontend renderiza cards com posição (#1, #2, #3...)
```
