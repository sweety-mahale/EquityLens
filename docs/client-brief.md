# Client Brief — InsightBridge Research

## The Client

**InsightBridge Research** is an independent equity research firm based in Mumbai with approximately **35 research analysts** covering Indian listed companies. The firm provides institutional-grade research to mutual funds, portfolio management services (PMS), alternative investment funds (AIFs), family offices, and wealth management firms across India.

InsightBridge does not manage investments or execute trades. Their business is producing high-quality equity research, financial analysis, sector reports, and providing direct analyst access to institutional clients.

## How InsightBridge Makes Money

- Analysts specialize in sectors such as Banking, IT, Pharmaceuticals, FMCG, Infrastructure, Energy, and Manufacturing.
- Each analyst covers approximately 12–18 Indian listed companies.
- They publish company research reports, earnings summaries, valuation models, and sector outlook reports.
- Institutional clients pay annual subscriptions for research access and analyst consultations.
- The firm's reputation depends entirely on delivering accurate, evidence-backed research.

## How They Add Value

Institutional investors don't have time to manually review hundreds of pages of financial disclosures released every quarter.

Instead, InsightBridge analysts carefully review:

- Annual Reports
- Quarterly Results
- Investor Presentations
- Earnings Call Transcripts
- Corporate Announcements
- Regulatory Disclosures from NSE/BSE
- IPO Prospectuses (DRHP/RHP)

They transform thousands of pages of disclosures into concise investment insights and research reports that help portfolio managers make informed decisions.

The firm's competitive advantage is not having more information than everyone else—it is finding relevant information faster and presenting it clearly.

## The Problem

Every analyst spends nearly **half of every working week** reading and organizing company disclosures before they can begin any meaningful research.

A typical workflow looks like this:

1. Download annual reports from company websites or stock exchanges.
2. Read Management Discussion & Analysis (MD&A).
3. Review Risk Factors.
4. Compare segment revenue across previous years.
5. Search earnings call transcripts for management commentary.
6. Copy important paragraphs into research notes.
7. Compare wording changes between multiple financial years.

Only after completing this repetitive document intake can analysts begin writing their research.

This document intake work is:

- Time-consuming
- Highly repetitive
- Essential for producing quality research
- Repeated across multiple analysts covering related sectors

For example, multiple analysts may independently review the same Reliance Industries Annual Report while preparing sector-specific research.

Hiring additional analysts does not solve the problem because document review scales linearly with company coverage.

InsightBridge wants to eliminate this bottleneck.

## What They Want

InsightBridge wants an internal AI-powered assistant called **EquityLens** (Research Copilot).

The application should allow analysts to:

- Ask questions in plain English across the firm's document library.
- Search across multiple companies and multiple financial years simultaneously.
- Receive answers supported by precise document citations.
- View the original paragraph and page number supporting every answer.
- Continue previous research conversations.
- Access the system securely through a web application using their company email.

The system should become the firm's first stop before manually opening hundreds of PDF documents.

## Example Analyst Questions

The initial document corpus contains Annual Reports, Investor Presentations, and Earnings Call Transcripts for major Indian listed companies between FY2021 and FY2025.

The assistant should answer questions such as:

1. Across Reliance Industries' FY2021–FY2025 Annual Reports, how has the contribution of Digital Services, Retail, and Oil-to-Chemicals changed?
2. Compare Infosys' discussion of Artificial Intelligence and Generative AI across FY2022–FY2025. How has management's messaging evolved?
3. How has TCS described employee attrition, hiring trends, and productivity improvements over the last five financial years?
4. Compare HDFC Bank and ICICI Bank's disclosures regarding retail lending, credit quality, and Gross NPA trends from FY2021–FY2025.
5. Across Tata Motors' Annual Reports, how has management discussed electric vehicles, Jaguar Land Rover, and capital investment priorities?
6. Which companies introduced significant new risk disclosures related to Artificial Intelligence, cybersecurity, geopolitical risks, supply chain disruptions, or data privacy?
7. Compare capital expenditure trends for Reliance Industries, Tata Steel, Larsen & Toubro, and Adani Enterprises. What do the filings indicate about future investment priorities?
8. Summarize the latest geographic revenue exposure for Infosys, Wipro, TCS, and HCLTech, highlighting major year-over-year changes.
9. Compare commentary on cloud services and digital transformation across Infosys, TCS, and Wipro between FY2022 and FY2025.
10. If an analyst asks whether company disclosures prove that AI investments directly improved profitability, what evidence exists in the available documents, and where should the assistant refuse to make unsupported conclusions?

## What "Trust" Means

InsightBridge's business depends on research accuracy.

The assistant must:

- **Never generate information** that is not present in the document corpus.
- **Clearly state** when sufficient evidence does not exist.
- **Provide citations** for every factual statement.
- **Display the exact supporting paragraph and page number** for verification.
- **Distinguish facts** from assumptions or interpretations.

A missing answer is acceptable. A hallucinated answer is unacceptable.

## Document Corpus

The document library consists of publicly available corporate disclosures from major Indian listed companies.

Documents include:

- Annual Reports
- Quarterly Financial Results
- Investor Presentations
- Earnings Call Transcripts
- Corporate Announcements
- Shareholding Pattern filings
- IPO Prospectuses (DRHP/RHP)

The initial pilot focuses on approximately 50 Nifty 100 companies covering FY2021–FY2025.

## Constraints

- **Document source:** Public corporate disclosures available through company Investor Relations portals and Indian stock exchange filings (NSE/BSE).
- **Users:** Approximately 35 research analysts and research partners.
- **Authentication:** Company email and password (no SSO required).
- **Hosting:** Must run efficiently on a small-to-medium cloud deployment.
- **Ingestion:** Incremental ingestion as new company filings become available.

## Out of Scope

The first release will not include:

- Stock recommendations
- Buy/Sell/Hold suggestions
- Portfolio management
- Live market prices
- Financial forecasting
- News summarization
- Social media analysis
- External web search
- Multi-tenant SaaS functionality
- Mobile application

The assistant should answer questions only from the approved document corpus.

## Definition of Done

A pilot group of five senior research analysts uses the application for one week while preparing company research.

The pilot is considered successful if:

1. Analysts report saving at least three hours per week on document review.
2. Every answer includes verifiable citations.
3. Analysts trust the system enough to use it as their primary document search tool before manually reviewing filings.
4. No critical hallucinations are observed during the pilot.
