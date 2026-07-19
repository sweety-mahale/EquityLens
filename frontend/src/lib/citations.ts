import { isDataUIPart, type UIMessage } from 'ai'

export type CitationPayload = {
  citationIndex: number
  chunkId: string
  excerpt: string
  ticker: string
  companyName?: string
  // Indian-market fields (primary)
  documentType?: string    // e.g. 'annual_report', 'quarterly_results'
  financialYear?: string   // e.g. 'FY2025' or 'Q3FY24'
  // Legacy SEC fields (kept for backward compat)
  form?: string
  filingDate?: string
  page?: string
  section?: string
}

export type PipelineStage =
  | 'analyzing'
  | 'searching'
  | 'reading'
  | 'verifying'
  | 'streaming'

export type PipelineStatus = {
  stage: PipelineStage
  message: string
}

function isCitationData(data: unknown): data is CitationPayload {
  if (typeof data !== 'object' || data === null) {
    return false
  }

  const record = data as Record<string, unknown>
  return (
    typeof record.citationIndex === 'number' &&
    typeof record.chunkId === 'string' &&
    typeof record.excerpt === 'string' &&
    typeof record.ticker === 'string'
  )
}

export function isCitationPart(
  part: UIMessage['parts'][number],
): part is UIMessage['parts'][number] & { type: 'data-citation'; data: CitationPayload } {
  return isDataUIPart(part) && part.type === 'data-citation' && isCitationData(part.data)
}

export function isStatusPart(
  part: unknown,
): part is { type: 'data-status'; data: PipelineStatus } {
  if (typeof part !== 'object' || part === null) {
    return false
  }

  const record = part as Record<string, unknown>
  if (record.type !== 'data-status' || typeof record.data !== 'object' || record.data === null) {
    return false
  }

  const data = record.data as Record<string, unknown>
  return typeof data.stage === 'string' && typeof data.message === 'string'
}

export function citationsFromMessage(message: UIMessage): CitationPayload[] {
  return message.parts
    .filter(isCitationPart)
    .map((part) => part.data)
    .sort((a, b) => a.citationIndex - b.citationIndex)
}

export function textFromMessage(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
}

/** Human-readable document type label for display. */
function _docTypeLabel(citation: CitationPayload): string {
  if (citation.documentType) {
    const labels: Record<string, string> = {
      annual_report: 'Annual Report',
      quarterly_results: 'Quarterly Results',
      investor_presentation: 'Investor Presentation',
      earnings_call: 'Earnings Call',
      corporate_announcement: 'Corporate Announcement',
    }
    return labels[citation.documentType] ?? citation.documentType
  }
  return citation.form ?? 'Document'
}

/** Short chip label shown on citation buttons. */
export function citationLabel(citation: CitationPayload): string {
  const docType = _docTypeLabel(citation)
  const fy = citation.financialYear ?? citation.filingDate ?? ''
  const parts = [citation.ticker, docType, fy]
  if (citation.page) {
    parts.push(`p.${citation.page}`)
  }
  return parts.filter(Boolean).join(' · ')
}

export function citationHeader(citation: CitationPayload): string {
  const company = citation.companyName ?? citation.ticker
  const docType = _docTypeLabel(citation)
  const fy = citation.financialYear ?? (citation.filingDate ? `filed ${citation.filingDate}` : '')
  return `${company} · ${docType} · ${fy}`
}

export function citationSubtitle(citation: CitationPayload): string | null {
  const parts: string[] = []
  if (citation.page) {
    parts.push(`Page ${citation.page}`)
  }
  if (citation.section) {
    parts.push(citation.section)
  }
  return parts.length > 0 ? parts.join(' · ') : null
}

export function citationByIndex(
  citations: CitationPayload[],
  index: number,
): CitationPayload | undefined {
  return citations.find((citation) => citation.citationIndex === index)
}
