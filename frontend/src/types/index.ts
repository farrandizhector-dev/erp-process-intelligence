// Executive KPIs
export interface MonthlyTrend {
  month: string
  cases: number
  compliance_rate: number
  avg_duration: number
}

export interface ExecutiveKPIs {
  total_cases: number
  total_events: number
  compliance_rate: number
  avg_case_duration_days: number
  rework_rate: number
  happy_path_rate: number
  touchless_rate: number
  automation_coverage: number
  high_sla_risk_rate: number
  sla_risk_distribution: Record<string, number>
  monthly_trend: MonthlyTrend[]
}

// Process Flow
export interface ProcessFlowNode {
  id: string
  stage: string
  stage_name: string
  frequency: number
  avg_duration_hours: number
}

export interface ProcessFlowEdge {
  source: string
  target: string
  count: number
  median_wait_hours: number
  is_bottleneck: boolean
}

export interface ProcessFlowByType {
  nodes: ProcessFlowNode[]
  edges: ProcessFlowEdge[]
}

export interface ProcessFlowData {
  nodes: ProcessFlowNode[]
  edges: ProcessFlowEdge[]
  by_flow_type: Record<string, ProcessFlowByType>
}

// Variants
export interface Variant {
  variant_id: number
  sequence: string[]
  case_count: number
  case_percentage: number
  median_duration_days: number
  p90_duration_days: number
  compliance_rate: number
  is_happy_path: boolean
  dominant_flow_type: string
}

export interface VariantConcentration {
  top5_coverage: number
  top10_coverage: number
  top20_coverage: number
}

export interface VariantsData {
  total_variants: number
  top_variants: Variant[]
  concentration: VariantConcentration
}

// Compliance
export interface ComplianceRule {
  rule_id: string
  rule_name: string
  severity: string
  pass_rate: number
  violation_count: number
}

export interface ComplianceByCompany {
  company: string
  compliance_rate: number
  case_count: number
  critical_violations: number
}

export interface ComplianceHeatmap {
  company: string
  flow_type: string
  compliance_rate: number
  case_count: number
}

export interface ViolatingVendor {
  vendor: string
  vendor_name: string
  violation_count: number
  case_count: number
  violation_rate: number
}

export interface ComplianceSummary {
  overall_rate: number
  by_rule: ComplianceRule[]
  by_company: ComplianceByCompany[]
  heatmap: ComplianceHeatmap[]
  top_violating_vendors: ViolatingVendor[]
}

// Bottlenecks
export interface BottleneckTransition {
  from_activity: string
  to_activity: string
  from_stage: string
  to_stage: string
  count: number
  median_wait_hours: number
  p90_wait_hours: number
  is_bottleneck: boolean
}

export interface TopBottleneck {
  from_activity: string
  to_activity: string
  count: number
  p90_wait_hours: number
  impact_score: number
}

export interface BottlenecksData {
  transitions: BottleneckTransition[]
  top_bottlenecks: TopBottleneck[]
}

// Automation
export interface AutomationActivity {
  activity: string
  stage: string
  total_executions: number
  human_executions: number
  batch_ratio: number
  volume_score: number
  batch_gap_score: number
  input_uniformity: number
  timing_regularity: number
  error_reduction: number
  wait_reduction: number
  automation_score: number
  automation_tier: string
  estimated_hours_saved_monthly: number
}

export interface AutomationData {
  activities: AutomationActivity[]
}

// Case Summaries
export interface CaseEvent {
  activity: string
  timestamp: string
  resource: string
  resource_type: string
  stage: string
  time_since_prev_hours: number
}

export interface CaseSummary {
  case_id: string
  flow_type: string
  company: string
  vendor: string
  vendor_name: string
  duration_days: number
  event_count: number
  compliance_score: number
  has_rework: boolean
  variant_id: number
  is_happy_path: boolean
  sla_risk: string
  events?: CaseEvent[]
}

export interface CaseSummariesData {
  total_cases: number
  sample_cases: CaseSummary[]
}

// Company Benchmarks
export interface CompanyRadar {
  speed: number
  compliance: number
  efficiency: number
  automation: number
  volume: number
}

export interface CompanyBenchmark {
  company: string
  case_count: number
  avg_duration_days: number
  median_duration_days: number
  compliance_rate: number
  rework_rate: number
  touchless_rate: number
  automation_coverage: number
  primary_flow_type: string
  radar: CompanyRadar
}

export interface CompanyBenchmarksData {
  companies: CompanyBenchmark[]
  peer_comparison_dimensions: string[]
}

// SLA Risk
export interface ModelMetrics {
  auc_roc: number
  pr_auc: number
  precision: number
  recall: number
  f1: number
  n_train: number
  n_test: number
  positive_rate: number
}

export interface FeatureImportance {
  feature: string
  importance: number
}

export interface AtRiskCase {
  case_id: string
  flow_type: string
  sla_risk_actual: string
  sla_risk_score: number
  sla_risk_predicted: string
}

export interface SlaRiskData {
  model_metrics: ModelMetrics
  feature_importance: FeatureImportance[]
  at_risk_cases: AtRiskCase[]
}
