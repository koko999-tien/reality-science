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

export interface FindingResult {
  job_id: string;
  state: FindingState;
  diagnostic_code: string;
  message: string;
  symbolic_simplification?: string;
  dimensions_verified: boolean;
  diagnostics: string[];
}
