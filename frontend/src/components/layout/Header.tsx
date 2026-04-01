import { useLocation } from 'react-router-dom'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Executive Overview',
  '/process-map': 'Process Map',
  '/compliance': 'Compliance Center',
  '/bottlenecks': 'Bottleneck Explorer',
  '/automation': 'Automation Candidates',
  '/cases': 'Case Drilldown',
  '/benchmarks': 'Subsidiary Benchmark',
  '/sla-risk': 'SLA Risk',
}

export default function Header() {
  const location = useLocation()
  const title = PAGE_TITLES[location.pathname] ?? 'ERP Process Intelligence'

  return (
    <header className="fixed top-0 left-[220px] right-0 h-12 bg-surface border-b border-border flex items-center px-6 z-40">
      <h1 className="text-sm font-semibold text-slate-200">{title}</h1>
      <div className="ml-auto text-xs text-muted font-mono">BPI 2019</div>
    </header>
  )
}
