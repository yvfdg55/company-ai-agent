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
