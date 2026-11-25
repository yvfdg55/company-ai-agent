# Company AI Agent

Local Autonomous AI Agent for WhatsApp with Arabic and English support.

## Features

- Arabic, English, and Egyptian Arabic support
- Qwen3 through Ollama
- Excel and Google Sheets data sources
- Customer conversation memory with SQLite
- Multilingual semantic search and RAG-style retrieval
- Controlled tool calling
- Product price calculation
- Support ticket creation
- Preliminary order drafts for staff review
- WhatsApp Cloud API webhook integration
- Meta webhook signature verification
- Per-customer locking and daily message limits
- Local diagnostics and language tests

## Jupyter Notebook

The complete implementation is organized as separate cells in [`company_ai_agent.ipynb`](./company_ai_agent.ipynb).

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

## Project status

This project is an initial local autonomous-agent implementation intended for controlled business operations and human review of preliminary orders.
