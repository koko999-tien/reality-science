"use client";

import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  Connection,
  type OnNodesChange,
  type OnEdgesChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { MathCanvasNode, MathCanvasEdge } from "@/types/canvas";
import { VariableSpec } from "@/types/contracts";
import { ConstantNode } from "./nodes/ConstantNode";
import { VariableNode } from "./nodes/VariableNode";
import { BinaryOpNode } from "./nodes/BinaryOpNode";
import { UnaryOpNode } from "./nodes/UnaryOpNode";
import { FunctionCallNode } from "./nodes/FunctionCallNode";
import { EquationRootNode } from "./nodes/EquationRootNode";
import { PulseFlowEdge } from "./edges/PulseFlowEdge";
import { CanvasToolbar, NodeTypeToAdd } from "./CanvasToolbar";

interface SymbolicCanvasProps {
  nodes: MathCanvasNode[];
  edges: MathCanvasEdge[];
  onNodesChange: OnNodesChange<MathCanvasNode>;
  onEdgesChange: OnEdgesChange;
  onConnect: (connection: Connection) => void;
  declaredVariables: VariableSpec[];
  onNodeDataChange: (nodeId: string, updatedData: Record<string, unknown>) => void;
  onAddNode: (type: NodeTypeToAdd) => void;
  onAutoLayout?: () => void;
  onClear?: () => void;
  onValidate?: () => void;
  isValidating?: boolean;
  className?: string;
}

const nodeTypes = {
  constantNode: ConstantNode,
  variableNode: VariableNode,
  binaryOpNode: BinaryOpNode,
  unaryOpNode: UnaryOpNode,
  functionCallNode: FunctionCallNode,
  equationRootNode: EquationRootNode,
};

const edgeTypes = {
  pulseFlow: PulseFlowEdge,
  default: PulseFlowEdge,
  smoothstep: PulseFlowEdge,
};

export const SymbolicCanvas: React.FC<SymbolicCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  declaredVariables,
  onNodeDataChange,
  onAddNode,
  onAutoLayout,
  onClear,
  onValidate,
  isValidating = false,
  className = "",
}) => {
  // Enrich nodes with callbacks and declared variables so nodes can update their state
  const enrichedNodes = useMemo(() => {
    return nodes.map((node) => {
      const baseData = node.data || {};
      let enrichedData = { ...baseData };

      if (node.type === "constantNode") {
        enrichedData = {
          ...baseData,
          onChange: (newVal: number | string) => {
            onNodeDataChange(node.id, { value: newVal });
          },
        };
      } else if (node.type === "variableNode") {
        enrichedData = {
          ...baseData,
          availableSymbols: declaredVariables,
          onChange: (newSym: string) => {
            const found = declaredVariables.find((v) => v.symbol === newSym);
            onNodeDataChange(node.id, {
              symbol: newSym,
              name: found?.name,
              unit: found?.unit,
            });
          },
        };
      } else if (node.type === "binaryOpNode") {
        enrichedData = {
          ...baseData,
          onChange: (newOp: string) => {
            onNodeDataChange(node.id, { op: newOp });
          },
        };
      } else if (node.type === "unaryOpNode") {
        enrichedData = {
          ...baseData,
          onChange: (newOp: string) => {
            onNodeDataChange(node.id, { op: newOp });
          },
        };
      } else if (node.type === "functionCallNode") {
        enrichedData = {
          ...baseData,
          onChange: (newFunc: string) => {
            onNodeDataChange(node.id, { func: newFunc });
          },
        };
      } else if (node.type === "equationRootNode") {
        enrichedData = {
          ...baseData,
          onValidate,
        };
      }

      return {
        ...node,
        data: enrichedData,
      } as MathCanvasNode;
    });
  }, [nodes, declaredVariables, onNodeDataChange, onValidate]);

  return (
    <div
      className={`relative flex flex-col h-full w-full rounded-2xl border border-white/[0.08] bg-slate-950 shadow-tactile-card overflow-hidden ${className}`}
      data-testid="symbolic-canvas-container"
    >
      {/* Canvas Top Toolbar */}
      <div className="absolute top-4 left-4 right-4 z-10 pointer-events-auto">
        <CanvasToolbar
          onAddNode={onAddNode}
          onAutoLayout={onAutoLayout}
          onClear={onClear}
          onValidate={onValidate}
          isValidating={isValidating}
        />
      </div>

      {/* Main Flow Canvas with Cyber Grid */}
      <div className="flex-1 w-full h-[650px] min-h-[500px]">
        <ReactFlow
          nodes={enrichedNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          attributionPosition="bottom-right"
          className="bg-slate-950"
          defaultEdgeOptions={{
            type: "pulseFlow",
            animated: true,
            style: { stroke: "#0ea5e9", strokeWidth: 2 },
          }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1.2}
            color="#334155"
            className="opacity-70"
          />
          <Controls
            position="bottom-left"
            showInteractive={false}
            className="!border !border-slate-800 !bg-slate-900/90 !backdrop-blur-md !text-slate-200 !rounded-lg !shadow-xl [&>button]:!border-b-slate-800 [&>button]:!fill-slate-300"
          />
          <MiniMap
            position="bottom-right"
            nodeStrokeWidth={3}
            zoomable
            pannable
            maskColor="rgba(2, 6, 23, 0.75)"
            className="!border !border-slate-800 !bg-slate-900/80 !backdrop-blur-md !rounded-xl !shadow-2xl overflow-hidden"
          />
        </ReactFlow>
      </div>
    </div>
  );
};
