import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { CompanyBenchmarksData } from '../types'
import PageContainer from '../components/layout/PageContainer'
import DataTable from '../components/shared/DataTable'
import { fmtNumber, fmtPct, fmtDays } from '../utils/formatters'
import { CHART_COLORS } from '../utils/colors'

export default function SubsidiaryBenchmark() {
  const { data, loading, error } = useData<CompanyBenchmarksData>('company_benchmarks.json')

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const radarOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: {
      data: data.companies.map(c => c.company),
      textStyle: { color: '#6b7280' },
      bottom: 0,
    },
    radar: {
      indicator: [
        { name: 'Speed', max: 1 },
        { name: 'Compliance', max: 1 },
        { name: 'Efficiency', max: 1 },
        { name: 'Automation', max: 1 },
        { name: 'Volume', max: 1 },
      ],
      axisName: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#2a2a3d' } },
      splitArea: { areaStyle: { color: ['#12121a', '#1a1a28'] } },
      axisLine: { lineStyle: { color: '#2a2a3d' } },
    },
    series: [
      {
        type: 'radar',
        data: data.companies.map((c, i) => ({
          name: c.company,
          value: [c.radar.speed, c.radar.compliance, c.radar.efficiency, c.radar.automation, c.radar.volume],
          lineStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
          areaStyle: { color: CHART_COLORS[i % CHART_COLORS.length], opacity: 0.1 },
          itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
        })),
      },
    ],
  }

  const tableColumns = [
    { key: 'company', label: 'Company' },
    {
      key: 'case_count',
      label: 'Cases',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtNumber(Number(v))}</span>,
    },
    {
      key: 'avg_duration_days',
      label: 'Avg Duration',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtDays(Number(v))}</span>,
    },
    {
      key: 'median_duration_days',
      label: 'Median Duration',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtDays(Number(v))}</span>,
    },
    {
      key: 'compliance_rate',
      label: 'Compliance',
      render: (v: unknown) => (
        <span
          className="font-mono text-xs"
          style={{ color: Number(v) >= 90 ? '#10b981' : Number(v) >= 75 ? '#f59e0b' : '#ef4444' }}
        >
          {fmtPct(Number(v))}
        </span>
      ),
    },
    {
      key: 'rework_rate',
      label: 'Rework Rate',
      render: (v: unknown) => (
        <span
          className="font-mono text-xs"
          style={{ color: Number(v) > 20 ? '#ef4444' : Number(v) > 10 ? '#f59e0b' : '#10b981' }}
        >
          {fmtPct(Number(v))}
        </span>
      ),
    },
    {
      key: 'touchless_rate',
      label: 'Touchless',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtPct(Number(v))}</span>,
    },
    {
      key: 'automation_coverage',
      label: 'Automation',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtPct(Number(v))}</span>,
    },
    { key: 'primary_flow_type', label: 'Primary Flow' },
  ]

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Company Radar Comparison</h2>
          <ReactECharts option={radarOption} style={{ height: '500px' }} />
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Company Benchmarks Table</h2>
          <DataTable
            columns={tableColumns as Parameters<typeof DataTable>[0]['columns']}
            data={data.companies as unknown as Record<string, unknown>[]}
          />
        </div>
      </div>
    </PageContainer>
  )
}
