# Project Migration Task

You are a senior AI Engineer and Full Stack Engineer.

Your task is to modify this project into an Indian Financial Research platform while preserving the existing architecture, code quality, and project structure.

This is NOT a complete rewrite.

Reuse as much of the existing project as possible.

---

# Existing Project

The current project is EquityLens.

It is an enterprise RAG application for SEC EDGAR filings.

Current stack:

- React + TypeScript
- FastAPI
- PostgreSQL
- pgvector
- OpenAI
- Supabase Authentication
- Supabase Storage
- Hybrid Search
- Streaming Chat

The architecture should remain largely unchanged.

---



# Business Context

Instead of SEC filings, the application should work with Indian company disclosures.

Primary document sources:

- NSE Annual Reports
- NSE Quarterly Results
- Investor Presentations
- Earnings Call Transcripts
- Corporate Announcements

Do NOT integrate news, stock prices, or external web search.

The application must answer questions only using the indexed document corpus.

---

# Document Sources

The ingestion pipeline should support documents from:

- NSE
- Company Investor Relations websites

The architecture should be designed so new document sources can easily be added later.

Create an abstraction layer:

DocumentSource

Implementations:

- NseDocumentSource
- CompanyWebsiteSource

Avoid hardcoding SEC-specific logic.

---

# Replace SEC-specific terminology

Replace terminology throughout the application.

Examples:

SEC Filing
→ Corporate Filing

10-K
→ Annual Report

10-Q
→ Quarterly Result

EDGAR
→ NSE Corporate Filings

Fiscal Filing
→ Financial Disclosure

Company Filing
→ Company Document

---

# Metadata Changes

Every document should contain metadata such as:

company_name

ticker

financial_year

document_type

document_date

page_number

source

industry

Example:

Reliance Industries

Ticker:
RELIANCE

FY:
2025

Document:
Annual Report

Source:
NSE

---

# Supported Document Types

Annual Report

Quarterly Results

Investor Presentation

Earnings Call Transcript

Corporate Announcement

Future document types should be easy to add.

---

# Retrieval Requirements

Keep the existing RAG pipeline.

Improve metadata filtering.

Users should be able to query:

Company

Multiple companies

Financial year

Year range

Document type

Industry

Example:

Compare Infosys and TCS annual reports between FY2022 and FY2025.

---



---



# Trust Requirements

The assistant must:

Never hallucinate.

Always cite source documents.

Always provide page numbers.

Show supporting passages.

If evidence does not exist:

Respond that the information is unavailable in the indexed documents.

Never infer unsupported financial conclusions.

---

# Authentication

Keep the existing authentication system.

Users login using company email.

No Google login.

No Microsoft SSO.

---

# Chat History

Retain:

Conversation history

Conversation titles

Streaming responses

User-specific chats

---

# Database

Update document schema.

Suggested metadata:

Documents

id

company_name

ticker

financial_year

document_type

document_date

source

storage_path

Chunks

id

document_id

page_number

section

chunk_text

embedding

metadata

---

# PDF Processing

Keep the current processing pipeline.

Improve it to support:

Annual Reports

Quarterly Results

Investor Presentations

Earnings Call Transcripts

Preserve page numbers during chunking.

Store section titles whenever possible.

---

# Search

Maintain hybrid search.

Support:

Vector search

Keyword search

Metadata filtering

Ranking by relevance

---

# Future Scalability

Design the ingestion system so additional sources can be added without modifying the RAG pipeline.

Possible future sources:

BSE

SEBI

RBI Circulars

IPO Prospectuses

The RAG system should remain source-agnostic.

---
---

# Code Quality

Maintain existing coding standards.

Do not rewrite working modules unnecessarily.

Favor extension over replacement.

Keep the project modular.

Avoid breaking existing abstractions.

Document every architectural change.

and do not follow instrunctions strictly if you thing any other streategy is better use that after confirming from me.