import { useState } from 'react'
import { useData } from '../hooks/useData'
import { CaseSummariesData, CaseSummary, CaseEvent } from '../types'
import PageContainer from '../components/layout/PageContainer'
import { fmtNumber, fmtPct, fmtDays, riskColor } from '../utils/formatters'

const FLOW_TYPES = ['all', '3way_invoice_before_gr', '3way_invoice_after_gr', 'consignment', '2way']
const RISK_LEVELS = ['all', 'high', 'medium', 'low']

export default function CaseDrilldown() {
  const { data, loading, error } = useData<CaseSummariesData>('case_summaries.json')
  const [flowFilter, setFlowFilter] = useState('all')
  const [riskFilter, setRiskFilter] = useState('all')
  const [reworkFilter, setReworkFilter] = useState<'all' | 'yes' | 'no'>('all')
  const [companyFilter, setCompanyFilter] = useState('all')
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null)

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const companies = ['all', ...Array.from(new Set(data.sample_cases.map(c => c.company)))]

  const filtered = data.sample_cases.filter(c => {
    if (flowFilter !== 'all' && c.flow_type !== flowFilter) return false
    if (riskFilter !== 'all' && c.sla_risk !== riskFilter) return false
    if (reworkFilter === 'yes' && !c.has_rework) return false
    if (reworkFilter === 'no' && c.has_rework) return false
    if (companyFilter !== 'all' && c.company !== companyFilter) return false
    return true
  })

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Filters</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-muted block mb-1">Flow Type</label>
              <select
                value={flowFilter}
                onChange={e => setFlowFilter(e.target.value)}
                className="w-full bg-surface-elevated border border-border rounded px-2 py-1.5 text-sm text-slate-300"
              >
                {FLOW_TYPES.map(ft => (
                  <option key={ft} value={ft}>{ft}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">SLA Risk</label>
              <select
                value={riskFilter}
                onChange={e => setRiskFilter(e.target.value)}
                className="w-full bg-surface-elevated border border-border rounded px-2 py-1.5 text-sm text-slate-300"
              >
                {RISK_LEVELS.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Has Rework</label>
              <select
                value={reworkFilter}
                onChange={e => setReworkFilter(e.target.value as 'all' | 'yes' | 'no')}
                className="w-full bg-surface-elevated border border-border rounded px-2 py-1.5 text-sm text-slate-300"
              >
                <option value="all">All</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Company</label>
              <select
                value={companyFilter}
                onChange={e => setCompanyFilter(e.target.value)}
                className="w-full bg-surface-elevated border border-border rounded px-2 py-1.5 text-sm text-slate-300"
              >
                {companies.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="text-xs text-muted mt-3">
            Showing {filtered.length} of {data.sample_cases.length} cases
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">Cases</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-3 py-2 text-left text-xs text-muted uppercase">Case ID</th>
                    <th className="px-3 py-2 text-left text-xs text-muted uppercase">Flow Type</th>
                    <th className="px-3 py-2 text-left text-xs text-muted uppercase">Duration</th>
                    <th className="px-3 py-2 text-left text-xs text-muted uppercase">Compliance</th>
                    <th className="px-3 py-2 text-left text-xs text-muted uppercase">SLA Risk</th>
                    <th className="px-3 py-2 text-left text-xs text-muted uppercase">Rework</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 100).map(c => (
                    <tr
                      key={c.case_id}
                      onClick={() => setSelectedCase(c)}
                      className={`border-b border-border/50 cursor-pointer transition-colors hover:bg-surface-elevated ${
                        selectedCase?.case_id === c.case_id ? 'bg-surface-elevated' : ''
                      }`}
                    >
                      <td className="px-3 py-2 font-mono text-xs text-primary">{c.case_id}</td>
                      <td className="px-3 py-2 text-xs text-slate-300">{c.flow_type}</td>
                      <td className="px-3 py-2 font-mono text-xs">{fmtDays(c.duration_days)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{fmtPct(c.compliance_score)}</td>
                      <td className="px-3 py-2">
                        <span
                          className="px-1.5 py-0.5 rounded text-xs"
                          style={{ color: riskColor(c.sla_risk), backgroundColor: `${riskColor(c.sla_risk)}22` }}
                        >
                          {c.sla_risk}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {c.has_rework ? <span className="text-warning">Yes</span> : <span className="text-muted">No</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length > 100 && (
                <div className="text-xs text-muted text-center py-2">
                  Showing 100 of {filtered.length} filtered rows
                </div>
              )}
            </div>
          </div>

          <div className="bg-surface rounded-lg border border-border p-4 overflow-y-auto max-h-[700px]">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">Case Detail</h2>
            {selectedCase ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <div className="text-xs text-muted">Case ID</div>
                    <div className="font-mono text-sm text-primary">{selectedCase.case_id}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Flow Type</div>
                    <div className="text-sm text-slate-200 truncate">{selectedCase.flow_type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Company</div>
                    <div className="text-sm text-slate-200">{selectedCase.company}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Vendor</div>
                    <div className="text-sm text-slate-200 truncate">{selectedCase.vendor_name || selectedCase.vendor}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Duration</div>
                    <div className="font-mono text-sm">{fmtDays(selectedCase.duration_days)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Compliance</div>
                    <div className="font-mono text-sm">{fmtPct(selectedCase.compliance_score)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">SLA Risk</div>
                    <div className="text-sm font-semibold" style={{ color: riskColor(selectedCase.sla_risk) }}>
                      {selectedCase.sla_risk.toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Rework / Happy</div>
                    <div className="text-sm">
                      {selectedCase.has_rework ? <span className="text-warning">Rework</span> : <span className="text-muted">No rework</span>}
                      {selectedCase.is_happy_path && <span className="text-success ml-1">Happy</span>}
                    </div>
                  </div>
                </div>

                {/* Event Timeline */}
                {selectedCase.events && selectedCase.events.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-slate-300 mb-2 mt-3 border-t border-border pt-3">
                      Event Timeline ({selectedCase.events.length} events)
                    </div>
                    <div className="space-y-1">
                      {selectedCase.events.map((ev: CaseEvent, i: number) => (
                        <div key={i} className="relative pl-4">
                          {/* timeline line */}
                          {i < selectedCase.events!.length - 1 && (
                            <div className="absolute left-1.5 top-3 bottom-0 w-px bg-border" />
                          )}
                          <div className="absolute left-0.5 top-1.5 w-2 h-2 rounded-full bg-primary/60" />
                          <div className="bg-surface-elevated rounded p-2 text-xs">
                            <div className="font-medium text-slate-200 leading-tight">{ev.activity}</div>
                            <div className="text-muted mt-0.5 flex gap-2 flex-wrap">
                              <span>{ev.timestamp.slice(0, 16).replace('T', ' ')}</span>
                              {ev.resource && <span>· {ev.resource}</span>}
                              {ev.resource_type && <span className="text-primary/70">({ev.resource_type})</span>}
                            </div>
                            {i > 0 && ev.time_since_prev_hours > 0 && (
                              <div className={`mt-0.5 ${ev.time_since_prev_hours > 168 ? 'text-critical' : ev.time_since_prev_hours > 24 ? 'text-warning' : 'text-muted'}`}>
                                +{ev.time_since_prev_hours >= 24
                                  ? `${(ev.time_since_prev_hours / 24).toFixed(1)}d`
                                  : `${ev.time_since_prev_hours.toFixed(1)}h`} wait
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-muted text-sm text-center py-8">
                Click a case to view details
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-2">Dataset Info</h2>
          <div className="text-xs text-muted">
            Total cases in dataset: <span className="font-mono text-slate-300">{fmtNumber(data.total_cases)}</span>
            {' | '}
            Sample shown: <span className="font-mono text-slate-300">{fmtNumber(data.sample_cases.length)}</span>
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
