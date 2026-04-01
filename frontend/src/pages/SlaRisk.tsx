import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { SlaRiskData } from '../types'
import PageContainer from '../components/layout/PageContainer'
import KPICard from '../components/shared/KPICard'
import DataTable from '../components/shared/DataTable'
import { fmtNumber, fmtPct, riskColor } from '../utils/formatters'

export default function SlaRisk() {
  const { data, loading, error } = useData<SlaRiskData>('sla_risk.json')

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const m = data.model_metrics
  const sortedFeatures = [...data.feature_importance].sort((a, b) => b.importance - a.importance)

  const featureBarOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: '25%', right: '8%', top: '5%', bottom: '5%' },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#2a2a3d' } },
    },
    yAxis: {
      type: 'category',
      data: sortedFeatures.map(f => f.feature).reverse(),
      axisLabel: { color: '#6b7280', fontSize: 11 },
      axisLine: { lineStyle: { color: '#2a2a3d' } },
    },
    series: [
      {
        type: 'bar',
        data: sortedFeatures.map(f => f.importance).reverse(),
        itemStyle: { color: '#22d3ee' },
        label: {
          show: true,
          position: 'right',
          color: '#f1f5f9',
          fontSize: 11,
        },
      },
    ],
  }

  const caseColumns = [
    { key: 'case_id', label: 'Case ID' },
    { key: 'flow_type', label: 'Flow Type' },
    {
      key: 'sla_risk_score',
      label: 'Risk Score',
      render: (v: unknown) => (
        <span className="font-mono text-xs" style={{ color: Number(v) > 0.7 ? '#ef4444' : '#f59e0b' }}>
          {Number(v).toFixed(4)}
        </span>
      ),
    },
    {
      key: 'sla_risk_actual',
      label: 'Actual',
      render: (v: unknown) => (
        <span
          className="px-1.5 py-0.5 rounded text-xs"
          style={{ color: riskColor(String(v)), backgroundColor: `${riskColor(String(v))}22` }}
        >
          {String(v)}
        </span>
      ),
    },
    {
      key: 'sla_risk_predicted',
      label: 'Predicted',
      render: (v: unknown) => <span className="text-xs text-muted">{String(v)}</span>,
    },
  ]

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <KPICard
            title="AUC-ROC"
            value={m.auc_roc.toFixed(4)}
            color="#22d3ee"
            subtitle="Model discrimination"
          />
          <KPICard
            title="PR-AUC"
            value={m.pr_auc.toFixed(4)}
            color="#818cf8"
            subtitle="Precision-recall area"
          />
          <KPICard
            title="F1 Score"
            value={m.f1.toFixed(4)}
            color="#10b981"
            subtitle="Harmonic mean"
          />
          <KPICard
            title="Precision"
            value={m.precision.toFixed(4)}
            subtitle={`${fmtPct(m.positive_rate)} positive rate`}
          />
          <KPICard
            title="Recall"
            value={m.recall.toFixed(4)}
            subtitle={`${fmtNumber(m.n_test)} test samples`}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Feature Importance</h2>
            <ReactECharts option={featureBarOption} style={{ height: '400px' }} />
          </div>
          <div className="bg-surface rounded-lg border border-border p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-2">Model Summary</h2>
            <div className="space-y-3 text-sm mt-4">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">Training samples</span>
                <span className="font-mono">{fmtNumber(m.n_train)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">Test samples</span>
                <span className="font-mono">{fmtNumber(m.n_test)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">Positive rate</span>
                <span className="font-mono">{fmtPct(m.positive_rate)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">AUC-ROC</span>
                <span className="font-mono text-primary">{m.auc_roc.toFixed(4)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">PR-AUC</span>
                <span className="font-mono text-primary">{m.pr_auc.toFixed(4)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">Precision</span>
                <span className="font-mono">{m.precision.toFixed(4)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted">Recall</span>
                <span className="font-mono">{m.recall.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">F1</span>
                <span className="font-mono text-success">{m.f1.toFixed(4)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">At-Risk Cases</h2>
          <DataTable
            columns={caseColumns as Parameters<typeof DataTable>[0]['columns']}
            data={data.at_risk_cases as unknown as Record<string, unknown>[]}
            maxRows={50}
          />
        </div>
      </div>
    </PageContainer>
  )
}
