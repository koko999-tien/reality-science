import type { Node, Edge } from "@xyflow/react";
import type { OperatorType, AllowedFunction } from "@/types/contracts";

export interface ConstantNodeData {
  value: number | string;
  onChange?: (val: number | string) => void;
  [key: string]: unknown;
}

export interface VariableNodeData {
  symbol: string;
  name?: string;
  unit?: string;
  onChange?: (symbol: string) => void;
  availableSymbols?: Array<{ symbol: string; name?: string; unit?: string }>;
  [key: string]: unknown;
}

export interface BinaryOpNodeData {
  op: OperatorType;
  onChange?: (op: OperatorType) => void;
  [key: string]: unknown;
}

export interface UnaryOpNodeData {
  op: "neg";
  onChange?: (op: "neg") => void;
  [key: string]: unknown;
}

export interface FunctionCallNodeData {
  func: AllowedFunction;
  onChange?: (func: AllowedFunction) => void;
  [key: string]: unknown;
}

export interface EquationRootNodeData {
  name?: string;
  latex?: string;
  onValidate?: () => void;
  [key: string]: unknown;
}

export type ConstantNode = Node<ConstantNodeData, "constantNode">;
export type VariableNode = Node<VariableNodeData, "variableNode">;
export type BinaryOpNode = Node<BinaryOpNodeData, "binaryOpNode">;
export type UnaryOpNode = Node<UnaryOpNodeData, "unaryOpNode">;
export type FunctionCallNode = Node<FunctionCallNodeData, "functionCallNode">;
export type EquationRootNode = Node<EquationRootNodeData, "equationRootNode">;

export type MathCanvasNode =
  | ConstantNode
  | VariableNode
  | BinaryOpNode
  | UnaryOpNode
  | FunctionCallNode
  | EquationRootNode;

export type MathCanvasEdge = Edge;
