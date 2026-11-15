export type NodeType = "constant" | "variable" | "binary_op" | "unary_op" | "function_call";
export type OperatorType = "+" | "-" | "*" | "/" | "**" | "neg";
export type AllowedFunction = "sqrt" | "sin" | "cos" | "exp" | "log";

export interface UnitSpec {
  name: string;
  symbol: string;
  dimensionality: string;
  scale_factor?: number;
}

export interface VariableSpec {
  symbol: string;
  name: string;
  unit: string;
  domain?: "real" | "positive_real" | "integer" | "complex";
  latex_presentation?: string;
}

export interface ExprNode {
  node_type: NodeType;
  value?: number | string;
  op?: OperatorType;
  func?: AllowedFunction;
  left?: ExprNode;
  right?: ExprNode;
  args?: ExprNode[];
}

export type FindingState =
  | "PASS"
  | "FAIL"
  | "WARNING"
  | "NOT_APPLICABLE"
  | "INSUFFICIENT_DATA"
  | "NEEDS_EXPERT_REVIEW"
  | "NOT_YET_TESTED";

export interface LayerFinding {
  layer: number;
  name: string;
  state: FindingState;
  diagnostic_code: string;
  message: string;
  diagnostics: string[];
  details?: Record<string, unknown>;
  execution_time_ms?: number;
}

export interface FindingResult {
  job_id: string;
  state: FindingState;
  diagnostic_code: string;
  message: string;
  symbolic_simplification?: string;
  dimensions_verified: boolean;
  diagnostics: string[];
  details?: Record<string, unknown>;
  layer?: number;
  layer_findings?: Record<number, LayerFinding>;
}

export interface PipelineValidationReport {
  job_id: string;
  version_id?: string;
  target_entity_type: string;
  target_entity_id: string;
  overall_state: FindingState;
  summary: string;
  symbolic_simplification?: string;
  dimensions_verified: boolean;
  layers: Record<number, LayerFinding>;
  diagnostics: string[];
  total_execution_time_ms: number;
}

export interface EquationModel {
  id: string;
  version_id: string;
  label: string;
  latex_raw: string;
  canonical_ast_json: Record<string, unknown>;
  sympy_expr?: string;
  created_at: string;
}

export interface VariableModel {
  id: string;
  version_id: string;
  symbol: string;
  name: string;
  unit: string;
  domain: string;
  latex_presentation?: string;
  created_at: string;
}

export interface ClaimModel {
  id: string;
  version_id: string;
  claim_code: string;
  statement: string;
  claim_type: string;
  target_variable?: string;
  epistemic_state: string;
  confidence_score: number;
  created_at: string;
}

export interface ValidationFindingModel {
  id: string;
  run_id: string;
  layer: number;
  target_entity_type: string;
  target_entity_id: string;
  job_id: string;
  state: FindingState;
  diagnostic_code: string;
  message: string;
  symbolic_simplification?: string;
  dimensions_verified: boolean;
  diagnostics: any;
  created_at: string;
}

export interface ValidationRunModel {
  id: string;
  version_id: string;
  status: string;
  overall_state: FindingState;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  findings: ValidationFindingModel[];
}

export interface ResearchVersionModel {
  id: string;
  project_id: string;
  version_number: number;
  title: string;
  content_hash?: string;
  publication_status: string;
  is_frozen: boolean;
  created_at: string;
}

export interface ResearchProjectModel {
  id: string;
  slug: string;
  title: string;
  description?: string;
  visibility: string;
  is_frozen: boolean;
  created_at: string;
  versions?: ResearchVersionModel[];
}
