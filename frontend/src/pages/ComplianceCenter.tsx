import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { ComplianceSummary } from '../types'
import PageContainer from '../components/layout/PageContainer'
import DataTable from '../components/shared/DataTable'
import { fmtPct, fmtNumber, severityColor } from '../utils/formatters'
import { CHART_COLORS } from '../utils/colors'

export default function ComplianceCenter() {
  const { data, loading, error } = useData<ComplianceSummary>('compliance_summary.json')

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const overallRate = data.overall_rate

  const gaugeOption = {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'gauge',
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            color: [
              [overallRate / 100, '#22d3ee'],
              [1, '#2a2a3d'],
            ],
            width: 18,
          },
        },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#2a2a3d' } },
        axisLabel: { color: '#6b7280', fontSize: 12 },
        pointer: { itemStyle: { color: '#22d3ee' } },
        detail: {
          formatter: '{value}%',
          fontSize: 28,
          color: '#22d3ee',
          fontFamily: 'JetBrains Mono, monospace',
          offsetCenter: [0, '60%'],
        },
        title: { color: '#6b7280', offsetCenter: [0, '85%'] },
        data: [{ value: overallRate.toFixed(1), name: 'Overall Compliance' }],
      },
    ],
  }

  const companyBarOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: data.by_company.map(c => c.company),
      axisLabel: { color: '#6b7280', rotate: 30, fontSize: 11 },
      axisLine: { lineStyle: { color: '#2a2a3d' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#6b7280', formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#2a2a3d' } },
      min: 0,
      max: 100,
    },
    series: [
      {
        type: 'bar',
        data: data.by_company.map((c, i) => ({
          value: c.compliance_rate,
          itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
        })),
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
          color: '#f1f5f9',
          fontSize: 11,
        },
      },
    ],
  }

  const ruleColumns = [
    { key: 'rule_id', label: 'Rule ID' },
    { key: 'rule_name', label: 'Rule' },
    {
      key: 'severity',
      label: 'Severity',
      render: (v: unknown) => (
        <span
          className="px-2 py-0.5 rounded text-xs font-medium"
          style={{ backgroundColor: `${severityColor(String(v))}22`, color: severityColor(String(v)) }}
        >
          {String(v)}
        </span>
      ),
    },
    {
      key: 'pass_rate',
      label: 'Pass Rate',
      render: (v: unknown) => (
        <div className="flex items-center gap-2">
          <div className="w-20 bg-border rounded-full h-1.5">
            <div
              className="h-1.5 rounded-full"
              style={{ width: `${Number(v)}%`, backgroundColor: Number(v) > 90 ? '#10b981' : '#f59e0b' }}
            />
          </div>
          <span className="font-mono text-xs">{fmtPct(Number(v))}</span>
        </div>
      ),
    },
    {
      key: 'violation_count',
      label: 'Violations',
      render: (v: unknown) => <span className="font-mono text-xs text-critical">{fmtNumber(Number(v))}</span>,
    },
  ]

  const vendorColumns = [
    { key: 'vendor', label: 'Vendor ID' },
    { key: 'vendor_name', label: 'Name' },
    {
      key: 'violation_count',
      label: 'Violations',
      render: (v: unknown) => <span className="font-mono text-xs text-critical">{fmtNumber(Number(v))}</span>,
    },
    {
      key: 'violation_rate',
      label: 'Violation Rate',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtPct(Number(v))}</span>,
    },
    {
      key: 'case_count',
      label: 'Cases',
      render: (v: unknown) => <span className="font-mono text-xs">{fmtNumber(Number(v))}</span>,
    },
  ]

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4 text-center">Overall Compliance Rate</h2>
            <ReactECharts option={gaugeOption} style={{ height: '300px' }} />
          </div>
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Compliance by Company</h2>
            <ReactECharts option={companyBarOption} style={{ height: '300px' }} />
          </div>
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Compliance Rules</h2>
          <DataTable
            columns={ruleColumns as Parameters<typeof DataTable>[0]['columns']}
            data={data.by_rule as unknown as Record<string, unknown>[]}
          />
        </div>

        {data.top_violating_vendors && data.top_violating_vendors.length > 0 && (
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Top Violating Vendors</h2>
            <DataTable
              columns={vendorColumns as Parameters<typeof DataTable>[0]['columns']}
              data={data.top_violating_vendors as unknown as Record<string, unknown>[]}
              maxRows={20}
            />
          </div>
        )}
      </div>
    </PageContainer>
  )
}
