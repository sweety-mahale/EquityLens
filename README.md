# EquityLens

**Enterprise RAG Platform for Financial Document Intelligence**

An internal AI platform that lets analysts query corporate financial documents in plain English and receive accurate, source-cited answers.

---

## The Client

**InsightBridge Research** *(fictional)* is an independent Indian equity research firm with approximately **35 research analysts** covering publicly listed companies across sectors including Banking, IT, FMCG, Energy, Infrastructure, Manufacturing, and Pharmaceuticals.

Analysts spend nearly **half of every working week** reading corporate filings before they can begin writing research reports. This repetitive document review slows research productivity and limits the number of companies each analyst can effectively cover.

EquityLens eliminates this bottleneck by transforming thousands of pages of corporate disclosures into a searchable knowledge base powered by Retrieval-Augmented Generation (RAG).

> 📄 Full project brief: `docs/client-brief.md`

---

# Solution

EquityLens provides a centralized AI-powered platform where analysts can:

- Search corporate disclosures using natural language
- Compare multiple companies across multiple financial years
- Retrieve answers with supporting evidence
- View page-level citations and original document passages
- Continue previous research conversations
- Trust every response because it is grounded in the indexed corpus

The platform is designed to improve research productivity without generating unsupported financial conclusions.

---

# Built with RAG Architecture

EquityLens uses a **Retrieval-Augmented Generation (RAG)** architecture.

Instead of relying solely on an LLM's internal knowledge, the system retrieves relevant document chunks from a vector database and provides them as context before generating a response.

This approach helps:

- Reduce hallucinations
- Improve factual accuracy
- Generate grounded responses
- Provide page-level citations
- Display supporting document passages
- Support multi-company and multi-year comparisons

---

# System Architecture

```text
                               +----------------------+
                               |   React Frontend     |
                               |  (Analyst Portal)    |
                               +----------+-----------+
                                          |
                                   HTTPS / REST API
                                          |
                                          ▼
                              +-------------------------+
                              |      FastAPI API        |
                              | Authentication & Chat   |
                              +-----------+-------------+
                                          |
                  +-----------------------+------------------------+
                  |                                                |
                  ▼                                                ▼
       +----------------------+                      +------------------------+
       |   Supabase Auth      |                      | Conversation History   |
       |  (Email Login)       |                      | PostgreSQL             |
       +----------------------+                      +------------------------+
                                          |
                                          ▼
                          +-------------------------------+
                          |      RAG Retrieval Layer      |
                          +---------------+---------------+
                                          |
                        +-----------------+------------------+
                        |                                    |
                        ▼                                    ▼
              Hybrid Search                     Metadata Filtering
       (Vector + Keyword Search)      Company • FY • Document Type
                        |                                    |
                        +-----------------+------------------+
                                          |
                                          ▼
                          +-------------------------------+
                          | PostgreSQL + pgvector         |
                          | Document Chunks & Embeddings  |
                          +-------------------------------+
                                          ▲
                                          |
                           Document Ingestion Pipeline
                                          ▲
                                          |
          +-----------------------------------------------------------+
          | Annual Reports | Quarterly Results | Investor Presentations|
          | Earnings Calls | Corporate Announcements                  |
          +-----------------------------------------------------------+
                                          ▲
                                          |
                 NSE • Company Investor Relations Websites
```

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Frontend | React + TypeScript (Vite) |
| Backend | FastAPI |
| Authentication | Supabase Auth |
| Database | PostgreSQL |
| Vector Database | pgvector |
| Retrieval | Hybrid Search (Vector + Full-Text Search) |
| Embedding Model | OpenAI Embeddings |
| LLM | OpenAI GPT |
| Storage | Supabase Storage |
| Deployment | Railway |

---

# Core Features

- Enterprise RAG architecture
- Hybrid Retrieval (Semantic + Keyword Search)
- Natural language document search
- Multi-company comparison
- Multi-year financial analysis
- Metadata-aware retrieval
- Source-backed answers
- Page-level citations
- Supporting document passages
- Conversation history
- Secure analyst authentication

---

# Supported Documents

The platform currently supports indexing:

- Annual Reports
- Quarterly Results
- Investor Presentations
- Earnings Call Transcripts
- Corporate Announcements

Future document sources:

- BSE Filings
- SEBI Circulars
- RBI Circulars
- IPO Prospectuses (DRHP/RHP)

---

# Sample Dataset

The initial corpus contains publicly available financial disclosures for leading Indian companies, including:

- Reliance Industries
- TCS
- Infosys
- HDFC Bank
- ICICI Bank
- Wipro
- Hindustan Unilever
- Bajaj Finance

Document coverage spans **FY2022–FY2025**, enabling cross-company and year-over-year analysis.
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |


