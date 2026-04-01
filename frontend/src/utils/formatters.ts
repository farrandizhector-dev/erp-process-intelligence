export const fmtNumber = (n: number, decimals = 0) =>
  n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })

export const fmtPct = (n: number, decimals = 1) => `${(n).toFixed(decimals)}%`

export const fmtHours = (h: number) =>
  h >= 24 ? `${(h / 24).toFixed(1)}d` : `${h.toFixed(1)}h`

export const fmtDays = (d: number) => `${d.toFixed(1)}d`

export const tierColor = (tier: string): string => {
  const map: Record<string, string> = {
    quick_win: '#10b981',
    medium_effort: '#22d3ee',
    complex: '#f59e0b',
    not_recommended: '#6b7280',
  }
  return map[tier] ?? '#6b7280'
}

export const riskColor = (risk: string): string => {
  const map: Record<string, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#10b981',
  }
  return map[risk] ?? '#6b7280'
}

export const severityColor = (s: string): string => {
  const map: Record<string, string> = {
    critical: '#ef4444',
    warning: '#f59e0b',
    info: '#22d3ee',
  }
  return map[s] ?? '#6b7280'
}
