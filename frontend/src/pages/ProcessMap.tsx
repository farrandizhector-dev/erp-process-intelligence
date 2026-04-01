import { useState, useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { useData } from '../hooks/useData'
import { ProcessFlowData, ProcessFlowEdge } from '../types'
import PageContainer from '../components/layout/PageContainer'
import { STAGE_COLORS } from '../utils/colors'

const FLOW_TYPES = ['all', '3way_invoice_before_gr', '3way_invoice_after_gr', 'consignment', '2way']

const FLOW_LABELS: Record<string, string> = {
  all: 'All Flows',
  '3way_invoice_before_gr': '3-Way (Invoice before GR)',
  '3way_invoice_after_gr': '3-Way (Invoice after GR)',
  consignment: 'Consignment',
  '2way': '2-Way',
}

/**
 * ECharts Sankey requires a strict DAG (no self-loops, no cycles).
 * This function greedily builds a DAG from the input edges, keeping
 * the highest-count edges and discarding any that would form a cycle.
 */
function buildDAG(edges: ProcessFlowEdge[]): ProcessFlowEdge[] {
  // Remove self-loops, sort highest-count first
  const sorted = [...edges]
    .filter(e => e.source !== e.target)
    .sort((a, b) => b.count - a.count)

  // adjacency[u] = set of nodes reachable FROM u in the current DAG
  const adjacency = new Map<string, Set<string>>()

  function canReach(from: string, to: string): boolean {
    if (from === to) return true
    const stack = [from]
    const visited = new Set<string>()
    while (stack.length > 0) {
      const curr = stack.pop()!
      if (curr === to) return true
      if (visited.has(curr)) continue
      visited.add(curr)
      for (const n of adjacency.get(curr) ?? []) stack.push(n)
    }
    return false
  }

  const result: ProcessFlowEdge[] = []
  for (const edge of sorted) {
    // Adding source→target is safe only if target cannot already reach source
    if (!canReach(edge.target, edge.source)) {
      result.push(edge)
      if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set())
      adjacency.get(edge.source)!.add(edge.target)
    }
  }
  return result
}

function fmtCount(n: number): string {
  return n >= 1_000 ? `${(n / 1_000).toFixed(1)}k` : String(n)
}

export default function ProcessMap() {
  const { data, loading, error } = useData<ProcessFlowData>('process_flow.json')
  const [selectedFlow, setSelectedFlow] = useState('all')

  // ── HOOKS must all be called before any early return ──────────────────────
  const dagEdges = useMemo<ProcessFlowEdge[]>(() => {
    if (!data) return []
    const byFlowType = data.by_flow_type ?? {}
    const raw =
      selectedFlow === 'all'
        ? data.edges
        : (byFlowType[selectedFlow]?.edges ?? data.edges)
    return buildDAG(raw)
  }, [data, selectedFlow])
  // ─────────────────────────────────────────────────────────────────────────

  if (loading || error || !data) {
    return <PageContainer loading={loading} error={error} />
  }

  const byFlowType = data.by_flow_type ?? {}
  const activeNodeIds = new Set(dagEdges.flatMap(e => [e.source, e.target]))
  const allNodes =
    selectedFlow === 'all' ? data.nodes : (byFlowType[selectedFlow]?.nodes ?? data.nodes)
  const nodes = allNodes.filter(n => activeNodeIds.has(n.id))

  const bottleneckCount = dagEdges.filter(e => e.is_bottleneck).length

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (params: {
        dataType: string
        data: { name?: string; source?: string; target?: string; value?: number }
      }) => {
        if (params.dataType === 'edge') {
          const val = params.data.value ?? 0
          return `<b>${params.data.source}</b><br/>↓<br/><b>${params.data.target}</b><br/>Count: ${val.toLocaleString()}`
        }
        return params.data.name ?? ''
      },
    },
    series: [
      {
        type: 'sankey',
        // NOTE: 'layout' is a graph-series property, NOT valid for sankey.
        // Sankey uses automatic layout controlled by nodeAlign + layoutIterations.
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'left',
        layoutIterations: 32,
        nodeWidth: 18,
        nodeGap: 8,
        data: nodes.map(n => ({
          name: n.id,
          itemStyle: { color: STAGE_COLORS[n.stage] ?? '#6b7280' },
        })),
        links: dagEdges.map(e => ({
          source: e.source,
          target: e.target,
          value: Math.max(1, e.count),
          lineStyle: {
            color: e.is_bottleneck ? '#ef4444' : '#4b5563',
            opacity: e.is_bottleneck ? 0.7 : 0.45,
          },
        })),
        label: {
          color: '#e2e8f0',
          fontSize: 10,
          fontFamily: 'Inter, sans-serif',
        },
        itemStyle: {
          borderWidth: 0,
        },
        left: '2%',
        right: '18%',
        top: '2%',
        bottom: '2%',
      },
    ],
  }

  return (
    <PageContainer>
      <div className="space-y-6">
        {/* Flow type filter tabs */}
        <div className="flex items-center gap-2 flex-wrap">
          {FLOW_TYPES.map(ft => (
            <button
              key={ft}
              onClick={() => setSelectedFlow(ft)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                selectedFlow === ft
                  ? 'bg-primary text-background'
                  : 'bg-surface border border-border text-muted hover:text-slate-200'
              }`}
            >
              {FLOW_LABELS[ft] ?? ft}
            </button>
          ))}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-surface rounded-lg border border-border p-4 text-center">
            <div className="text-2xl font-mono font-bold text-primary">{nodes.length}</div>
            <div className="text-xs text-muted mt-1">Active Nodes</div>
          </div>
          <div className="bg-surface rounded-lg border border-border p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-200">{dagEdges.length}</div>
            <div className="text-xs text-muted mt-1">Flow Edges (DAG)</div>
          </div>
          <div className="bg-surface rounded-lg border border-border p-4 text-center">
            <div className="text-2xl font-mono font-bold text-critical">{bottleneckCount}</div>
            <div className="text-xs text-muted mt-1">Bottleneck Edges</div>
          </div>
        </div>

        {/* Sankey chart */}
        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-1">Process Flow — Sankey</h2>
          <div className="text-xs text-muted mb-4">
            Node colors = process stage · <span className="text-critical">Red edges</span> = bottleneck (P90 &gt; 7 days) ·{' '}
            {fmtCount(dagEdges.reduce((s, e) => s + e.count, 0))} total transitions shown
          </div>
          <ReactECharts
            option={option}
            style={{ height: '620px' }}
            notMerge
            lazyUpdate={false}
          />
        </div>

        {/* Stage legend */}
        <div className="bg-surface rounded-lg border border-border p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Stage Legend</h2>
          <div className="flex flex-wrap gap-4">
            {Object.entries(STAGE_COLORS).map(([stage, color]) => (
              <div key={stage} className="flex items-center gap-2 text-xs">
                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
                <span className="text-muted">{stage}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
