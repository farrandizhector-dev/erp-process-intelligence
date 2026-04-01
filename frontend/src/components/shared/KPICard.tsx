interface KPICardProps {
  title: string
  value: string
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  color?: string
}

export default function KPICard({ title, value, subtitle, trend, color }: KPICardProps) {
  const trendIcon = trend === 'up' ? '↑' : trend === 'down' ? '↓' : null
  const trendColor = trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#6b7280'

  return (
    <div className="bg-surface rounded-lg border border-border p-4 flex flex-col gap-1">
      <div className="text-xs text-muted uppercase tracking-wider">{title}</div>
      <div
        className="text-2xl font-mono font-bold"
        style={{ color: color ?? '#f1f5f9' }}
      >
        {value}
      </div>
      {(subtitle || trendIcon) && (
        <div className="text-xs text-muted flex items-center gap-1">
          {trendIcon && (
            <span style={{ color: trendColor }}>{trendIcon}</span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
