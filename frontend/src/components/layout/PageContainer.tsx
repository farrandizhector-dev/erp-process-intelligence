import { ReactNode } from 'react'

interface PageContainerProps {
  children?: ReactNode
  loading?: boolean
  error?: string | null
}

export default function PageContainer({ children, loading, error }: PageContainerProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-critical p-6 bg-surface rounded-lg border border-border">
        <div className="font-semibold mb-1">Error loading data</div>
        <div className="text-sm text-muted">{error}</div>
      </div>
    )
  }

  return (
    <div className="max-w-[1600px] w-full">
      {children}
    </div>
  )
}
