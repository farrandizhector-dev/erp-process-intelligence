import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { AutomationData } from '../types'
import PageContainer from '../components/layout/PageContainer'
import KPICard from '../components/shared/KPICard'
import DataTable from '../components/shared/DataTable'
import { fmtNumber, fmtPct, tierColor } from '../utils/formatters'

export default function AutomationCandidates() {
  const { data, loading, error } = useData<AutomationData>('automation_candidates.json')

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const activities = [...data.activities].sort((a, b) => b.automation_score - a.automation_score)

  const tierCounts: Record<string, number> = {}
  for (const a of activities) {
    tierCounts[a.automation_tier] = (tierCounts[a.automation_tier] ?? 0) + 1
  }

  const scatterOption = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params: { data: [number, number, number, string, string] }) => {
        const d = params.data
        return `${d[3]}<br/>Executions: ${fmtNumber(d[0])}<br/>Score: ${fmtPct(d[1])}<br/>Hours Saved/mo: ${fmtNumber(d[2])}<br/>Tier: ${d[4]}`
      },
    },
    xAxis: {
      type: 'log',
      name: 'Total Executions',
      nameTextStyle: { color: '#6b7280' },
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#2a2a3d' } },
    },
    yAxis: {
      type: 'value',
      name: 'Automation Score',
      nameTextStyle: { color: '#6b7280' },
      axisLabel: { color: '#6b7280', formatter: '{value}' },
      splitLine: { lineStyle: { color: '#2a2a3d' } },
      min: 0,
      max: 1,
    },
    series: [
      {
        type: 'scatter',
        data: activities.map(a => [
          Math.max(1, a.total_executions),
          a.automation_score,
          a.estimated_hours_saved_monthly,
          a.activity,
          a.automation_tier,
        ]),
        symbolSize: (d: number[]) => Math.max(8, Math.min(40, Math.sqrt(d[2] || 1) * 2)),
        itemStyle: {
          color: (p: { data: (number | string)[] }) => tierColor(String(p.data[4])),
          opacity: 0.8,
        },
      },
    ],
  }

  const tableColumns = [
    { key: 'activity', label: 'Activity' },
    { key: 'stage', label: 'Stage' },
    {
      key: 'automation_tier',
      label: 'Tier',
      render: (v: unknown) => (
        <span
          className="px-2 py-0.5 rounded text-xs font-medium"
          style={{ color: tierColor(String(v)), backgroundColor: `${tierColor(String(v))}22` }}
        >
          {String(v).replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'automation_score',
      label: 'Score',
      render: (v: unknown) => <span className="font-mono text-xs text-primary">{Number(v).toFixed(3)}</span>,
    },
    {
      key: 'total_executions',
      label: 'Executions',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtNumber(Number(v))}</span>,
    },
    {
      key: 'estimated_hours_saved_monthly',
      label: 'Hours Saved/mo',
      render: (v: unknown, row?: Record<string, unknown>) => {
        const hrs = Number(v)
        if (hrs === 0 && row && Number(row.human_executions) === 0) {
          return <span className="text-muted text-xs">—</span>
        }
        return <span className="font-mono text-xs text-success">{hrs > 0 ? fmtNumber(hrs) : '< 1'}</span>
      },
    },
  ]

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard title="Total Activities" value={fmtNumber(activities.length)} color="#22d3ee" />
          <KPICard
            title="Quick Wins"
            value={fmtNumber(tierCounts.quick_win ?? 0)}
            color="#10b981"
          />
          <KPICard
            title="Medium Effort"
            value={fmtNumber(tierCounts.medium_effort ?? 0)}
            color="#22d3ee"
          />
          <KPICard
            title="Complex"
            value={fmtNumber(tierCounts.complex ?? 0)}
            color="#f59e0b"
          />
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-2">Automation Opportunity Bubble Chart</h2>
          <div className="text-xs text-muted mb-4">
            X = executions (log), Y = automation score, size = estimated hours saved/mo, color = tier
          </div>
          <ReactECharts option={scatterOption} style={{ height: '400px' }} />
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            Ranked Automation Candidates
          </h2>
          <DataTable
            columns={tableColumns as Parameters<typeof DataTable>[0]['columns']}
            data={activities as unknown as Record<string, unknown>[]}
            maxRows={50}
          />
        </div>
      </div>
    </PageContainer>
  )
}
