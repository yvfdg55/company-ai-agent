# Company AI Agent

Local Autonomous AI Agent for WhatsApp with Arabic and English support.

## Features

- Arabic, English, and Egyptian Arabic support
- Qwen3 through Ollama
- Excel and Google Sheets data sources
- Customer conversation memory with SQLite
- Optional MySQL analytics store for centralized reporting
- Automatic customer registration
- Multilingual semantic search and RAG-style retrieval
- Controlled tool calling
- Product price calculation
- Support ticket creation
- Preliminary order drafts for staff review
- WhatsApp Cloud API webhook integration
- Meta webhook signature verification
- Per-customer locking and daily message limits
- Explainable automatic recommendations for operations
- Management chat for customer and sales questions
- Explainable marketing recommendation engine
- Local diagnostics and language tests

## Analytics and MySQL

SQLite remains the default local database, so the agent can run without MySQL. The optional `mysql_analytics.py` module adds a central MySQL store with tables for customers, products, customer events, orders, and tickets. The analytics layer produces customer totals, locations, products, event types, orders, tickets, daily/hourly activity, monthly sales, sales by place, top customers, and deterministic recommendations with a priority, action, and measured reason.

The management interface can answer questions such as:

- How many customers are registered?
- Who is the best customer and how much did they purchase?
- Which place has the highest sales?
- What are the sales totals by month or by place?
- What actions do you recommend?

## Marketing recommendations

The project now includes a dependency-light recommendation engine in `recommendation_engine.py`. It provides:

- RFM recency/frequency/monetary scoring and segments: VIP, loyal, new, price-sensitive, and at-risk.
- Product-pair association rules with support, confidence, and lift; this is the small-data baseline for FP-Growth/Apriori.
- Content-based product recommendations for customers with limited history.
- Transparent purchase-propensity and churn-risk scores.
- Marketing actions with priority, reason, confidence, and `approval_required=true`.
- MySQL schema for `order_items`, `marketing_campaigns`, `campaign_results`, and `recommendations`.

The production upgrade path is to train CatBoost/LightGBM models when labeled purchase data is sufficient, then add uplift modeling and contextual bandits after campaign results are collected. The system does not send campaigns, change prices, or alter inventory automatically.

Recommendations do not make purchases, send broadcasts, or change inventory automatically. They are suggestions for human review.

Install the optional connector:

```bash
pip install mysql-connector-python
```

Configure these environment variables only in the runtime environment; never commit passwords or customer data:

```env
MYSQL_ANALYTICS_ENABLED=false
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=company_agent
MYSQL_USER=company_agent
MYSQL_PASSWORD=
```

In the notebook, run `initialize_mysql_analytics()` after configuring MySQL. Use `get_mysql_analysis(days=30)` to return the snapshot and explainable recommended actions. If MySQL is disabled or unavailable, the local SQLite agent continues to work.

## Jupyter Notebook

The complete implementation is organized as separate cells in [`company_ai_agent.ipynb`](./company_ai_agent.ipynb).
The final cells contain the optional MySQL analytics setup, synchronization helpers, and analysis functions.

## Configuration

Copy the environment settings into a `.env` file and configure the required values before running the agent. Do not commit real API tokens, secrets, service-account files, or customer data.

Required integrations include:

- Ollama with the configured Qwen3 model
- An Excel file or Google Sheets service account
- WhatsApp Cloud API credentials

## Local startup

Run the notebook cells in order, test the local agent, configure the WhatsApp credentials, then call:

```python
start_company_agent()
```

The Flask webhook listens on port `5000` by default.

## Preview

`preview_app.py` provides a safe Gradio preview with separate tables for customers, products, locations, time periods, events, customer purchases, monthly sales, place sales, and recommendations. It includes a management chat tab and a marketing recommendation tab showing RFM segments, product associations, and approval-required actions. The preview does not connect to WhatsApp or a real MySQL server and does not store real secrets.

## Project status

This project is an initial local autonomous-agent implementation intended for controlled business operations and human review of preliminary orders.

## Management Agent

`management_agent.py` adds a separate read-only management agent. It reuses `mysql_analytics.py` for KPIs and operational recommendations and `recommendation_engine.py` for explainable customer and product recommendations. MySQL is the default provider; set `MANAGEMENT_DATA_PROVIDER=sqlite` to use the local SQLite database when central analytics are unavailable.

Example:

```python
from management_agent import ManagementAgent

agent = ManagementAgent()
report = agent.analyze(days=30)
print(report["recommendations"])
print(agent.answer("ما التوصيات الإدارية؟", days=30))
```

The management agent is read-only: it does not send campaigns, change prices or inventory, confirm orders, or perform other business actions. Every recommendation is marked for human review. When Ollama is unavailable, deterministic grounded answers remain available with `agent.answer(question, use_llm=False)`.

## Agent Platform Foundation

The new `app/` package is the foundation for the company-wide agent platform. It currently includes shared settings, domain models, central policies, an SQLite audit log, a constrained tool registry, product tools, reviewable customer actions, and the first `CustomerAgent`. The customer agent is deliberately limited to product lookup, price-tool integration, support-ticket requests, and reviewable order drafts.

The foundation is tested with direct Python tests in `tests/test_foundation.py`. The environment used for development does not include pytest, so the same scenarios were also executed through a standalone Python test run. WhatsApp transport and the Ollama orchestration layer will be connected after these shared contracts are stabilized.

The next integration layer is now present: `app/data/company.py` loads company records from Excel, `app/llm/ollama.py` provides grounded Ollama responses, `app/channels/whatsapp.py` verifies and parses WhatsApp Cloud API events, and `app/runtime.py` connects the channel to `CustomerAgent` with duplicate-message protection. The channel sender is still not activated against real credentials until the runtime configuration is explicitly tested.

The standalone Flask Webhook is in `app/server.py`:

```bash
python -m app.server
```

It exposes `GET /health`, `GET /webhook` for Meta verification, and `POST /webhook` for signed WhatsApp events. The local test suite verifies signature validation, challenge verification, response delivery through a fake channel, and duplicate-message protection. Real startup requires `WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, and a readable `company.xlsx` file.

For local setup, copy [`.env.example`](./.env.example) to `.env`, install [the requirements](./requirements.txt), and run the no-network smoke test:

```bash
cp .env.example .env
pip install -r requirements.txt
python scripts/smoke_test.py
```

The real local launcher is `python scripts/run_webhook.py`; it refuses to start when the required WhatsApp credentials or company data are missing.

Company product data must include `Product Name` and `Price`; `Stock`, `Category`, `Updated`, and `Description` are optional. The validator rejects empty product names and invalid or negative prices. To create a separate local sample workbook without overwriting a real file, run `python scripts/create_sample_company.py`; it creates [sample_company.xlsx](./sample_company.xlsx).

## Unified Data Layer

`app/data/manager.py` and `app/data/connectors.py` provide the first unified data layer. They normalize rows and document pages into `UnifiedRecord` objects that retain source, type, structured fields, metadata, confidence, and stable IDs. The current connectors support Excel, CSV, JSON, SQLite, MySQL, PDF, and DOCX. Use `DataSourceManager.ingest_file(...)`, `ingest_sqlite(...)`, or `ingest_mysql(...)`, then search with `DataSourceManager.search(...)`. Image OCR, audio transcription, and external API connectors remain later adapters rather than being silently treated as text files.

## Development, tests, and operational limits

Install runtime and development dependencies with:
```bash
python -m pip install -r requirements-dev.txt
pytest -q
python scripts/smoke_test.py
```
GitHub Actions runs the same `pytest -q` and no-network smoke test on pushes and pull requests. Tests use temporary SQLite databases and fakes; they do not call WhatsApp, Ollama, MySQL, or any external API.

Company search is a dependency-light lexical hybrid: Arabic diacritic removal and common-letter normalization are combined with token overlap, exact-phrase boosting, and TF-IDF cosine ranking. It is not an embedding system and does not claim semantic vector retrieval. `CustomerAgent` passes the highest-ranked records to Ollama for grounded answers when Ollama is healthy; if Ollama is unavailable or errors, it returns a safe deterministic fallback.

`create_support_ticket` and `save_order_draft` persist to SQLite tables (`support_tickets` and `order_drafts`) with review status and UTC timestamps. Both always return `approval_required=true`; neither confirms an order or performs payment. Pass an explicit `database` path in integrations, or use `DATABASE` for the default local path.

Audit details are sanitized before storage: secret/token/password/API-key fields and payment/card/bank fields are redacted, and long string values are truncated. This is a logging safeguard, not a substitute for encryption or access control.

Management roles remain restricted by routing policy. If `MANAGEMENT_AUTH_TOKEN` is non-empty, a matching token must also be supplied to `AgentOrchestrator.dispatch(..., actor_role="manager", auth_token=...)`; a role string alone is rejected. Keep the token only in the runtime environment and never commit it. The current Flask webhook exposes customer messaging and health/verification endpoints; management authorization is enforced at the orchestrator boundary rather than by adding an unaudited admin HTTP endpoint.

Ollama, WhatsApp Cloud API, Google Sheets, and MySQL are optional runtime integrations. Real credentials, customer data, and production service availability are required for those integrations; the local tests intentionally do not validate network connectivity. Review all drafts and tickets with a human before taking business action.
