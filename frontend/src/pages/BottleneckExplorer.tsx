import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { BottlenecksData } from '../types'
import PageContainer from '../components/layout/PageContainer'
import DataTable from '../components/shared/DataTable'
import { fmtHours, fmtNumber } from '../utils/formatters'

export default function BottleneckExplorer() {
  const { data, loading, error } = useData<BottlenecksData>('bottlenecks.json')

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  // Sort all bottlenecks by p90_wait_hours, then cap chart at a reasonable scale.
  // Extreme outliers (e.g. multi-year waits from data artefacts) are kept in the
  // table but excluded from the bar chart so other bars remain legible.
  const allSorted = [...data.top_bottlenecks].sort((a, b) => b.p90_wait_hours - a.p90_wait_hours)
  const values = allSorted.map(b => b.p90_wait_hours)
  // Use median × 20 as the chart cap — keeps most bars visible while hiding extreme outliers
  const medianVal = values[Math.floor(values.length / 2)] ?? 0
  const chartCap = medianVal * 20
  const top10 = allSorted.filter(b => b.p90_wait_hours <= chartCap).slice(0, 10)

  const barOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: '30%', right: '8%', top: '5%', bottom: '5%' },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#6b7280', formatter: (v: number) => fmtHours(v) },
      splitLine: { lineStyle: { color: '#2a2a3d' } },
    },
    yAxis: {
      type: 'category',
      data: top10.map(b => `${b.from_activity.slice(0, 20)}→${b.to_activity.slice(0, 20)}`).reverse(),
      axisLabel: { color: '#6b7280', fontSize: 10 },
      axisLine: { lineStyle: { color: '#2a2a3d' } },
    },
    series: [
      {
        type: 'bar',
        data: top10.map(b => b.p90_wait_hours).reverse(),
        itemStyle: { color: '#ef4444' },
        label: {
          show: true,
          position: 'right',
          formatter: (p: { value: number }) => fmtHours(p.value),
          color: '#f1f5f9',
          fontSize: 11,
        },
      },
    ],
  }

  const totalTransitions = data.transitions.length
  const bottleneckCount = data.transitions.filter(t => t.is_bottleneck).length

  const transitionColumns = [
    { key: 'from_activity', label: 'From Activity' },
    { key: 'to_activity', label: 'To Activity' },
    {
      key: 'median_wait_hours',
      label: 'Median Wait',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtHours(Number(v))}</span>,
    },
    {
      key: 'p90_wait_hours',
      label: 'P90 Wait',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtHours(Number(v))}</span>,
    },
    {
      key: 'count',
      label: 'Count',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtNumber(Number(v))}</span>,
    },
    {
      key: 'is_bottleneck',
      label: 'Bottleneck',
      render: (v: unknown) =>
        v ? (
          <span className="px-2 py-0.5 rounded text-xs bg-critical/20 text-critical">Yes</span>
        ) : (
          <span className="text-muted text-xs">—</span>
        ),
    },
  ]

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-surface rounded-lg border border-border p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-200">{totalTransitions}</div>
            <div className="text-xs text-muted mt-1">Total Transitions</div>
          </div>
          <div className="bg-surface rounded-lg border border-border p-4 text-center">
            <div className="text-2xl font-mono font-bold text-critical">{bottleneckCount}</div>
            <div className="text-xs text-muted mt-1">Bottleneck Transitions</div>
          </div>
          <div className="bg-surface rounded-lg border border-border p-4 text-center">
            <div className="text-2xl font-mono font-bold text-warning">
              {totalTransitions > 0 ? ((bottleneckCount / totalTransitions) * 100).toFixed(1) : 0}%
            </div>
            <div className="text-xs text-muted mt-1">Bottleneck Rate</div>
          </div>
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Top 10 Bottlenecks (P90 Wait Hours)</h2>
          <ReactECharts option={barOption} style={{ height: '400px' }} />
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">All Transitions</h2>
          <DataTable
            columns={transitionColumns as Parameters<typeof DataTable>[0]['columns']}
            data={data.transitions as unknown as Record<string, unknown>[]}
            maxRows={50}
          />
        </div>
      </div>
    </PageContainer>
  )
}
