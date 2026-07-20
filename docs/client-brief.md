# Client brief — EquityLens

## The client

**EquityLens** is an independent investment research platform used by equity research analysts who sell deep research to institutional clients (hedge funds, mutual funds, portfolio managers).

## How analysts add value

- Analysts each cover ~15 public companies in specific industries (IT services, banking, retail, auto, energy, etc.).
- They produce written research reports, financial models, and trend analysis.
- Their clients don't have the bandwidth to read every Annual Report, Quarterly Result, Investor Presentation, and Earnings Transcript.
- EquityLens turns thousands of filing pages into structured insights that analysts can act on.

## What they want

An internal chatbot — **EquityLens** — where any analyst can:

- Ask questions in plain English about any filing in the curated Indian corporate filing corpus.
- Get a grounded answer that cites specific source filing passages.
- Trust the answer enough to base downstream analysis on it.
- Use it from a browser, logged in with their email address.
- See their own past conversations.

## Example analyst questions

The corpus contains Indian corporate filings (Annual Reports, Quarterly Results, Investor Presentations) for large-cap Indian companies across FY2022–FY2025. The bot handles questions like:

1. Compare Infosys and TCS annual revenue growth and operating margin trends from FY2022 to FY2025.

1. Across Apple's 2021–2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change, and which category appears to have contributed most to any mix shift?
2. For Amazon, compare AWS operating income and margin against North America and International from 2021–2025. In which years did AWS appear to fund losses or weaker profitability elsewhere?
3. How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business from fiscal 2021 through fiscal 2025?
4. Across Microsoft's 2021–2025 filings, what changed in the way the company describes Azure, AI infrastructure, and cloud capacity constraints?
5. For Alphabet, how did Google Search, YouTube ads, Google Network, subscriptions/platforms/devices, and Google Cloud revenue trends differ across the available 10-Ks?
6. Which of the five companies added, removed, or materially changed risk-factor language related to AI, cloud infrastructure, export controls, supply chain concentration, or regulation between 2021 and 2025?
7. For Apple and NVIDIA, what do the filings say about supplier concentration or dependence on third-party manufacturing, and did the wording become more or less urgent over time?
8. Compare capital expenditures and purchase commitments for Microsoft, Alphabet, Amazon, and NVIDIA. What do the filings imply about the scale and timing of AI/cloud infrastructure investment?
9. For each company, summarize the most important geographic revenue exposures disclosed in the latest 10-K, then identify any year-over-year changes that could matter to an analyst.
10. If an analyst asks whether the filings prove that generative AI improved margins for any of these companies, what evidence exists in the corpus, and where should the bot refuse to infer beyond the filings?

## What "trust" means here

This is a research firm. Their entire business is being right. The bot must:

- **Never invent facts.** If the answer isn't in the corpus, it says so.
- **Always cite.** Every claim links to the source filing + page.
- **Show the underlying passage** so the analyst can verify in one click.

A wrong but confident answer is worse than no answer. Hallucinations kill the product.

## Constraints

- Corpus: SEC filings (10-Ks and 10-Qs) for S&P 500 companies, 2020–2025
- Source: SEC EDGAR (public domain)
- Users: ~40 Driftwood analysts, plus a few partners
- Login: Driftwood email addresses (no SSO required)
- Hosting: must run on a small/medium cloud footprint; Driftwood has no infra team

## Out of scope (explicitly)

- Trading recommendations or stock picks
- External data sources (no news, no social, no alternative data)
- Anything generating analysis not grounded in the corpus
- Multi-tenant / multi-client. This is Driftwood-internal only.
- Billing, plans, paywalls
- Mobile app

## Definition of done

The analyst pilot group (5 senior analysts) tries it for a week and reports it saves them at least 3 hours per analyst per week. If yes, Driftwood rolls it out firm-wide.
