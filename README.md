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
- Local diagnostics and language tests

## Analytics and MySQL

SQLite remains the default local database, so the agent can run without MySQL. The optional `mysql_analytics.py` module adds a central MySQL store with tables for customers, products, customer events, orders, and tickets. The analytics layer produces customer totals, locations, products, event types, orders, tickets, daily/hourly activity, and deterministic recommendations with a priority, action, and measured reason.

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

`preview_app.py` provides a safe Gradio preview with separate tables for customers, products, locations, time periods, events, and recommendations. The preview does not connect to WhatsApp or a real MySQL server and does not store real secrets.

## Project status

This project is an initial local autonomous-agent implementation intended for controlled business operations and human review of preliminary orders.
