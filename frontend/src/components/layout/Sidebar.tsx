import { NavLink } from 'react-router-dom'
import { BarChart3, GitBranch, ShieldCheck, Clock, Bot, Search, Building2, AlertTriangle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const navItems: { Icon: LucideIcon; label: string; path: string }[] = [
  { Icon: BarChart3, label: 'Executive Overview', path: '/' },
  { Icon: GitBranch, label: 'Process Map', path: '/process-map' },
  { Icon: ShieldCheck, label: 'Compliance', path: '/compliance' },
  { Icon: Clock, label: 'Bottlenecks', path: '/bottlenecks' },
  { Icon: Bot, label: 'Automation', path: '/automation' },
  { Icon: Search, label: 'Case Drilldown', path: '/cases' },
  { Icon: Building2, label: 'Benchmarks', path: '/benchmarks' },
  { Icon: AlertTriangle, label: 'SLA Risk', path: '/sla-risk' },
]

export default function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 h-screen w-[220px] bg-surface border-r border-border flex flex-col z-50">
      <div className="px-4 py-5 border-b border-border">
        <div className="text-primary font-sans text-sm font-bold tracking-wider">ERP PROCESS</div>
        <div className="text-muted text-xs mt-0.5">Intelligence Platform</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {navItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-surface-elevated border-l-2 border-primary text-primary'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-surface-elevated border-l-2 border-transparent'
              }`
            }
          >
            <item.Icon size={16} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-border">
        <div className="text-muted text-xs">BPI Challenge 2019</div>
      </div>
    </aside>
  )
}
