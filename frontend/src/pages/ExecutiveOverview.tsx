import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { ExecutiveKPIs } from '../types'
import PageContainer from '../components/layout/PageContainer'
import KPICard from '../components/shared/KPICard'
import { fmtNumber, fmtPct, fmtDays } from '../utils/formatters'

export default function ExecutiveOverview() {
  const { data, loading, error } = useData<ExecutiveKPIs>('executive_kpis.json')

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['Cases', 'Compliance Rate (%)'],
      textStyle: { color: '#6b7280' },
    },
    xAxis: {
      type: 'category',
      data: data.monthly_trend.map(t => t.month),
      axisLabel: { color: '#6b7280', rotate: 45, fontSize: 11 },
      axisLine: { lineStyle: { color: '#2a2a3d' } },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Cases',
        nameTextStyle: { color: '#6b7280' },
        axisLabel: { color: '#6b7280' },
        splitLine: { lineStyle: { color: '#2a2a3d' } },
      },
      {
        type: 'value',
        name: 'Compliance %',
        nameTextStyle: { color: '#6b7280' },
        axisLabel: { color: '#6b7280', formatter: '{value}%' },
        splitLine: { show: false },
        min: 60,
        max: 100,
      },
    ],
    series: [
      {
        name: 'Cases',
        type: 'bar',
        data: data.monthly_trend.map(t => t.cases),
        itemStyle: { color: '#22d3ee', opacity: 0.7 },
      },
      {
        name: 'Compliance Rate (%)',
        type: 'line',
        yAxisIndex: 1,
        data: data.monthly_trend.map(t => t.compliance_rate),
        lineStyle: { color: '#10b981', width: 2 },
        itemStyle: { color: '#10b981' },
        symbol: 'circle',
        symbolSize: 4,
      },
    ],
  }

  const SLA_RISK_COLORS: Record<string, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#10b981',
  }

  const slaDistribution = data.sla_risk_distribution
  const donutOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      orient: 'vertical',
      right: 20,
      textStyle: { color: '#6b7280' },
    },
    series: [
      {
        type: 'pie',
        radius: ['50%', '70%'],
        data: Object.entries(slaDistribution).map(([key, val]) => ({
          name: key,
          value: val,
          itemStyle: { color: SLA_RISK_COLORS[key] ?? '#6b7280' },
        })),
        label: { color: '#f1f5f9' },
      },
    ],
  }

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KPICard
            title="Total Cases"
            value={fmtNumber(data.total_cases)}
            subtitle={`${fmtNumber(data.total_events)} events`}
            color="#22d3ee"
          />
          <KPICard
            title="Compliance Rate"
            value={fmtPct(data.compliance_rate)}
            color={data.compliance_rate >= 90 ? '#10b981' : '#f59e0b'}
          />
          <KPICard
            title="Avg Duration"
            value={fmtDays(data.avg_case_duration_days)}
            color="#f1f5f9"
          />
          <KPICard
            title="Rework Rate"
            value={fmtPct(data.rework_rate)}
            color={data.rework_rate > 10 ? '#ef4444' : '#f59e0b'}
          />
          <KPICard
            title="Happy Path Rate"
            value={fmtPct(data.happy_path_rate)}
            color={data.happy_path_rate > 30 ? '#10b981' : '#f59e0b'}
          />
          <KPICard
            title="Automation Coverage"
            value={fmtPct(data.automation_coverage)}
            color="#22d3ee"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Monthly Trends</h2>
            <ReactECharts option={trendOption} style={{ height: '360px' }} />
          </div>
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">SLA Risk Distribution</h2>
            <ReactECharts option={donutOption} style={{ height: '360px' }} />
          </div>
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Additional KPIs</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard title="Touchless Rate" value={fmtPct(data.touchless_rate)} />
            <KPICard title="High SLA Risk Rate" value={fmtPct(data.high_sla_risk_rate)} color="#ef4444" />
            <KPICard title="Total Events" value={fmtNumber(data.total_events)} />
            <KPICard
              title="SLA Risk (High)"
              value={fmtNumber(data.sla_risk_distribution.high ?? 0)}
              color="#ef4444"
            />
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
