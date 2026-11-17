/**
 * E2E Modernization Test Suite — REALITY SCIENCE Frontend UI/UX
 *
 * Covers 4 Tiers of verification:
 * - Tier 1: Feature Coverage (Landing hero, Preset demo, Navbar, Presets bar, PulseFlowEdge, Dark glass nodes)
 * - Tier 2: Boundary & Corner Cases (Dimensional mismatch, Singularities, Missing operands, Cycle & depth limits)
 * - Tier 3: Cross-Feature Combinations (Preset -> AST translation, Dark tokens, Variable live-sync)
 * - Tier 4: Real-World Application Scenarios (Local draft workflow, backend-only results)
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import fs from "fs";
import path from "path";

// Contracts & Libraries
import { ExprNode, VariableSpec, FindingResult } from "@/types/contracts";
import { MathCanvasNode, MathCanvasEdge } from "@/types/canvas";
import { graphToAst, astToGraph, TranslationError } from "@/lib/ast_graph_converter";
import { exprNodeToLatex } from "@/lib/ast";
import { validateEquationAst } from "@/lib/api";
import { CANONICAL_PRESETS, ScientificPreset } from "@/lib/presets";
import { getSmoothStepPath, Position } from "@xyflow/react";

// Core Components
import { Navbar } from "@/components/layout/Navbar";
import HomePage from "@/app/page";
import EquationEditorPage from "@/app/(dashboard)/projects/[slug]/editor/page";
import { VariableDeclarationPanel } from "@/components/equations/VariableDeclarationPanel";
import { ValidationStatusBar } from "@/components/equations/ValidationStatusBar";
import { LayerPipelineMatrix } from "@/components/equations/LayerPipelineMatrix";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { ScientificPresetsBar } from "@/components/equations/canvas/ScientificPresetsBar";
import { PulseFlowEdge } from "@/components/equations/canvas/edges/PulseFlowEdge";

// Custom Nodes
import { ConstantNode } from "@/components/equations/canvas/nodes/ConstantNode";
import { VariableNode } from "@/components/equations/canvas/nodes/VariableNode";
import { BinaryOpNode } from "@/components/equations/canvas/nodes/BinaryOpNode";
import { UnaryOpNode } from "@/components/equations/canvas/nodes/UnaryOpNode";
import { FunctionCallNode } from "@/components/equations/canvas/nodes/FunctionCallNode";
import { EquationRootNode } from "@/components/equations/canvas/nodes/EquationRootNode";

// Mock Next.js Navigation
jest.mock("next/navigation", () => ({
  useParams: () => ({ slug: "general-relativity" }),
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
  }),
  usePathname: () => "/projects/general-relativity/editor",
}));

// Mock @xyflow/react to avoid jsdom layout/SVG bounding box crashes
jest.mock("@xyflow/react", () => {
  const actual = jest.requireActual("@xyflow/react");
  return {
    ...actual,
    ReactFlow: ({ nodes, edges, children }: any) => (
      <div
        data-testid="xyflow-mock-canvas"
        data-node-count={nodes?.length || 0}
        data-edge-count={edges?.length || 0}
      >
        {nodes?.map((node: any) => (
          <div
            key={node.id}
            data-testid={`canvas-node-${node.id}`}
            data-node-type={node.type}
          >
            {node.data?.label || node.data?.symbol || node.data?.value || node.data?.op || node.id}
          </div>
        ))}
        {edges?.map((edge: any) => (
          <div
            key={edge.id}
            data-testid={`canvas-edge-${edge.id}`}
            data-edge-type={edge.type}
          >
            {edge.id}
          </div>
        ))}
        {children}
      </div>
    ),
    Controls: () => <div data-testid="xyflow-controls" />,
    MiniMap: () => <div data-testid="xyflow-minimap" />,
    Background: () => <div data-testid="xyflow-background" />,
    Handle: ({ id, position }: any) => (
      <div data-testid={`handle-${id || "default"}`} data-position={position} />
    ),
  };
});

describe("E2E Modernization Test Suite", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // =========================================================================
  // TIER 1: FEATURE COVERAGE
  // =========================================================================
  describe("Tier 1: Feature Coverage", () => {
    describe("1.1 Landing page hero, typography, and primary CTAs", () => {
      it("renders scientific brand title and mission statement", () => {
        render(<HomePage />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toHaveTextContent(/REALITY SCIENCE/i);
        expect(screen.getByText(/keep the evidence that supports a result in view/i)).toBeInTheDocument();
        expect(screen.getByText("Illustrative example", { exact: true })).toBeInTheDocument();
        expect(screen.getByText(/not run/i)).toBeInTheDocument();
      });

      it("provides direct navigation into projects and studio without raw API docs confusion", () => {
        render(<HomePage />);
        const exploreLink = screen.getByRole("link", { name: /Explore research projects/i });
        expect(exploreLink).toHaveAttribute("href", expect.stringMatching(/\/projects/));
      });

      it("answers user feedback Screenshot 1 by maintaining clean client-side navigation", () => {
        render(<HomePage />);
        const links = screen.getAllByRole("link");
        const hrefs = links.map((l) => l.getAttribute("href"));
        expect(hrefs.some((h) => h?.includes("/projects"))).toBe(true);
        expect(hrefs.every((h) => !h?.includes("/docs"))).toBe(true);
      });
    });

    describe("1.2 Illustrative equation presets", () => {
      it("keeps example ASTs available without asserting verification outcomes", () => {
        const heroLaws = CANONICAL_PRESETS.slice(0, 4);
        expect(heroLaws.length).toBe(4);

        for (const preset of heroLaws) {
          expect(preset.formulaLatex).toBeTruthy();
          expect(preset.variables.length).toBeGreaterThan(0);
          expect(preset.ast.node_type).toBe("binary_op");

          const graph = astToGraph(preset.ast, preset.variables);
          expect(graphToAst(graph.nodes, graph.edges, preset.variables)).toEqual(preset.ast);
        }
      });
    });

    describe("1.3 Research workspace navbar", () => {
      it("renders glassmorphic container with high-tech border and backdrop blur", () => {
        const { container } = render(<Navbar />);
        const header = container.querySelector("header");
        expect(header).toBeInTheDocument();
        expect(header?.className).toContain("backdrop-blur-xl");
        expect(header?.className).toContain("bg-slate-950/80");
        expect(header?.className).toContain("border-b");
      });

      it("does not display unobserved engine status", () => {
        render(<Navbar />);
        expect(screen.queryByRole("status")).not.toBeInTheDocument();
      });

      it("includes project and source repository links", () => {
        render(<Navbar />);
        const projectsLink = screen.getByRole("link", { name: /Projects/i });
        expect(projectsLink).toHaveAttribute("href", "/projects");

        const githubLink = screen.getByRole("link", { name: /GitHub Repository/i });
        expect(githubLink).toHaveAttribute("href", "https://github.com/TienNguyenD/Reality_Science");
        expect(githubLink).toHaveAttribute("target", "_blank");
        expect(githubLink).toHaveAttribute("rel", "noopener noreferrer");
      });
    });

    describe("1.4 Studio Canvas 1-Click Presets Bar (ScientificPresetsBar)", () => {
      it("verifies all 6 canonical scientific presets across 5 disciplines", () => {
        const categories = CANONICAL_PRESETS.map((p) => p.category);
        expect(categories).toContain("Classical");
        expect(categories).toContain("Relativistic");
        expect(categories).toContain("Astrophysics");
        expect(categories).toContain("Thermodynamics");
        expect(categories).toContain("Oscillations");
        expect(CANONICAL_PRESETS.length).toBe(6);
      });

      it("converts all presets into connected React Flow DAGs with equation roots", () => {
        for (const preset of CANONICAL_PRESETS) {
          const { nodes, edges } = astToGraph(preset.ast, preset.variables);
          expect(nodes.length).toBeGreaterThanOrEqual(3);
          expect(edges.length).toBeGreaterThanOrEqual(2);
          const rootNode = nodes.find((n) => n.type === "equationRootNode");
          expect(rootNode).toBeDefined();
        }
      });

      it("mounts ScientificPresetsBar and triggers onSelectPreset with canonical preset data", () => {
        const onSelect = jest.fn();
        render(<ScientificPresetsBar onSelectPreset={onSelect} />);

        // Verify presets bar container exists
        expect(screen.getByTestId("scientific-presets-bar")).toBeInTheDocument();

        // Verify all 6 preset options are present
        for (const preset of CANONICAL_PRESETS) {
          expect(screen.getByText(new RegExp(preset.name, "i"))).toBeInTheDocument();
        }

        // Click Einstein preset button
        const einsteinBtn = screen.getByText(/Einstein Mass-Energy/i);
        fireEvent.click(einsteinBtn);

        expect(onSelect).toHaveBeenCalledTimes(1);
        expect(onSelect).toHaveBeenCalledWith(
          expect.objectContaining({
            id: "einstein-energy",
            name: "Einstein Mass-Energy",
          })
        );
      });

      it("assigns type 'pulseFlowEdge' and animated=true to all generated canvas edges", () => {
        const ast: ExprNode = {
          node_type: "binary_op",
          op: "+",
          left: { node_type: "variable", value: "x" },
          right: { node_type: "constant", value: 10 },
        };

        const { edges } = astToGraph(ast, [{ symbol: "x", name: "X", unit: "meter" }]);
        expect(edges.length).toBeGreaterThanOrEqual(2);
        for (const edge of edges) {
          expect(edge.type).toBe("pulseFlowEdge");
          expect(edge.animated).toBe(true);
        }
      });
    });

    describe("1.5 Custom PulseFlowEdge SVG path with glowing cyan stroke & pulse styling", () => {
      it("validates SVG smoothstep path calculation algorithm for pulse edge connections", () => {
        const [edgePath] = getSmoothStepPath({
          sourceX: 50,
          sourceY: 50,
          sourcePosition: Position.Right,
          targetX: 250,
          targetY: 150,
          targetPosition: Position.Left,
          borderRadius: 16,
        });

        expect(edgePath).toBeTruthy();
        expect(edgePath).toMatch(/^M\s*50/);
      });

      it("mounts PulseFlowEdge and renders animated glowing SVG paths without fallback dummy checks", () => {
        const { container } = render(
          <svg>
            <PulseFlowEdge
              id="test-edge-1"
              sourceX={10}
              sourceY={20}
              targetX={100}
              targetY={200}
              sourcePosition={Position.Right}
              targetPosition={Position.Left}
              selected={true}
            />
          </svg>
        );

        // Gradient & filter defs
        expect(container.querySelector("linearGradient#pulse-grad-test-edge-1")).toBeInTheDocument();
        expect(container.querySelector("filter#photon-glow-test-edge-1")).toBeInTheDocument();

        // Ambient and base edges
        const paths = container.querySelectorAll("path");
        expect(paths.length).toBeGreaterThanOrEqual(2);
        const basePath = paths[1];
        expect(basePath.getAttribute("class")).toContain("stroke-cyan-400");
        expect(basePath.getAttribute("class")).toContain("animate-pulse-flow");

        // Energy quantum photon circle with animateMotion
        const circle = container.querySelector("circle");
        expect(circle).toBeInTheDocument();
        expect(circle?.getAttribute("fill")).toBe("#38bdf8");
        expect(circle?.querySelector("animateMotion")).toBeInTheDocument();
      });
    });

    describe("1.6 Dark glassmorphic canvas nodes with neon aura & KaTeX chips", () => {
      it("BinaryOpNode renders with operator selector and input/output handles", () => {
        const onChange = jest.fn();
        render(
          <BinaryOpNode
            id="b_test"
            data={{ op: "*", onChange }}
            type="binaryOpNode"
            zIndex={1}
            isConnectable={true}
            positionAbsoluteX={0}
            positionAbsoluteY={0}
            selected={false}
            dragging={false}
            selectable={true}
            deletable={true}
            draggable={true}
          />
        );

        const select = screen.getByLabelText("Binary operator for node b_test");
        expect(select).toHaveValue("*");
        expect(screen.getByTestId("handle-left")).toBeInTheDocument();
        expect(screen.getByTestId("handle-right")).toBeInTheDocument();
        expect(screen.getByTestId("handle-output")).toBeInTheDocument();

        fireEvent.change(select, { target: { value: "/" } });
        expect(onChange).toHaveBeenCalledWith("/");
      });

      it("VariableNode renders symbol selector, unit badge, and output handle", () => {
        const onChange = jest.fn();
        const vars = [{ symbol: "m", name: "Mass", unit: "kilogram" }];
        render(
          <VariableNode
            id="v_test"
            data={{ symbol: "m", availableSymbols: vars, onChange }}
            type="variableNode"
            zIndex={1}
            isConnectable={true}
            positionAbsoluteX={0}
            positionAbsoluteY={0}
            selected={false}
            dragging={false}
            selectable={true}
            deletable={true}
            draggable={true}
          />
        );

        const select = screen.getByLabelText("Variable symbol for node v_test");
        expect(select).toHaveValue("m");
        expect(screen.getByText("[kilogram]")).toBeInTheDocument();
        expect(screen.getByTestId("handle-output")).toBeInTheDocument();
      });

      it("ConstantNode renders numeric input with accessible label", () => {
        const onChange = jest.fn();
        render(
          <ConstantNode
            id="c_test"
            data={{ value: 299792458, onChange }}
            type="constantNode"
            zIndex={1}
            isConnectable={true}
            positionAbsoluteX={0}
            positionAbsoluteY={0}
            selected={false}
            dragging={false}
            selectable={true}
            deletable={true}
            draggable={true}
          />
        );

        const input = screen.getByLabelText("Constant value for node c_test");
        expect(input).toHaveValue(299792458);
        fireEvent.change(input, { target: { value: "300000000" } });
        expect(onChange).toHaveBeenCalledWith("300000000");
      });

      it("EquationRootNode renders KaTeX preview and validate button", () => {
        const onValidate = jest.fn();
        render(
          <EquationRootNode
            id="root_test"
            data={{ name: "R", latex: "E = m \\cdot c^2", onValidate }}
            type="equationRootNode"
            zIndex={1}
            isConnectable={true}
            positionAbsoluteX={0}
            positionAbsoluteY={0}
            selected={false}
            dragging={false}
            selectable={true}
            deletable={true}
            draggable={true}
          />
        );

        expect(screen.getByText(/Equation Root/i)).toBeInTheDocument();
        const validateBtn = screen.getByRole("button", { name: /Validate equation/i });
        fireEvent.click(validateBtn);
        expect(onValidate).toHaveBeenCalledTimes(1);
      });
    });
  });

  // =========================================================================
  // TIER 2: BOUNDARY & CORNER CASES
  // =========================================================================
  describe("Tier 2: Boundary & Corner Cases", () => {
    describe("2.1 Dimensional violation detection (meter + second)", () => {
      it("renders a dimensional finding returned by the validation API", async () => {
        const originalFetch = (global as any).fetch;
        (global as any).fetch = jest.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            job_id: "verify-test-mismatch",
            state: "FAIL",
            diagnostic_code: "DIMENSIONAL_MISMATCH",
            message: "Cannot add quantities with dimensions [length] and [time].",
            dimensions_verified: false,
            diagnostics: ["Incompatible dimension addition"],
            layer_findings: {
              3: {
                layer: 3,
                name: "Dimensional Analysis",
                state: "FAIL",
                diagnostic_code: "DIMENSIONAL_MISMATCH",
                message: "Cannot add meter and second.",
                diagnostics: ["Incompatible dimension addition"],
              },
            },
          }),
        });

        const meterPlusSecondAst: ExprNode = {
          node_type: "binary_op",
          op: "+",
          left: { node_type: "variable", value: "x" },
          right: { node_type: "variable", value: "t" },
        };

        const variables: VariableSpec[] = [
          { symbol: "x", name: "Position", unit: "meter" },
          { symbol: "t", name: "Time", unit: "second" },
        ];

        // Call the real API client function
        const result = await validateEquationAst({
          expression_ast: meterPlusSecondAst,
          variables,
        });

        expect(result.state).toBe("FAIL");
        expect(result.diagnostic_code).toBe("DIMENSIONAL_MISMATCH");
        expect(result.dimensions_verified).toBe(false);
        expect(result.layer_findings?.[3]?.state).toBe("FAIL");

        // Verify UI displays the real API result
        render(<ValidationStatusBar result={result} isValidating={false} onValidate={jest.fn()} />);
        const badge = screen.getByTestId("finding-state-badge");
        expect(badge).toHaveTextContent("FAIL");
        expect(screen.getByText("DIMENSIONAL_MISMATCH")).toBeInTheDocument();
        expect(screen.getByText(/Cannot add quantities with dimensions/i)).toBeInTheDocument();

        (global as any).fetch = originalFetch;
      });

      it("does not return a scientific result when the backend is unavailable", async () => {
        const originalFetch = (global as any).fetch;
        (global as any).fetch = jest.fn().mockRejectedValue(new Error("Network connection refused"));

        const meterPlusSecondAst: ExprNode = {
          node_type: "binary_op",
          op: "+",
          left: { node_type: "variable", value: "x" },
          right: { node_type: "variable", value: "t" },
        };

        const variables: VariableSpec[] = [
          { symbol: "x", name: "Position", unit: "meter" },
          { symbol: "t", name: "Time", unit: "second" },
        ];

        await expect(validateEquationAst({
          expression_ast: meterPlusSecondAst,
          variables,
        })).rejects.toThrow(/Network connection refused/);
        expect((global as any).fetch).toHaveBeenCalledTimes(1);

        (global as any).fetch = originalFetch;
      });

      it("renders FAIL state with DIMENSIONAL_MISMATCH when units are incompatible", () => {
        const mismatchResult: FindingResult = {
          job_id: "test-mismatch-1",
          state: "FAIL",
          diagnostic_code: "DIMENSIONAL_MISMATCH",
          message: "Cannot add quantities with dimensions [length] and [time].",
          dimensions_verified: false,
          diagnostics: ["Operands to '+' must have identical dimensions."],
          layer_findings: {
            1: { layer: 1, name: "Syntax", state: "PASS", diagnostic_code: "OK", message: "Valid", diagnostics: [] },
            2: { layer: 2, name: "Boundaries", state: "PASS", diagnostic_code: "OK", message: "Valid", diagnostics: [] },
            3: {
              layer: 3,
              name: "Dimensional Analysis",
              state: "FAIL",
              diagnostic_code: "DIMENSIONAL_MISMATCH",
              message: "Unit conflict: meter vs second",
              diagnostics: ["Incompatible dimension addition"],
            },
          },
        };

        render(
          <ValidationStatusBar
            result={mismatchResult}
            isValidating={false}
            onValidate={jest.fn()}
          />
        );

        const badge = screen.getByTestId("finding-state-badge");
        expect(badge).toHaveTextContent("FAIL");
        expect(screen.getByText("DIMENSIONAL_MISMATCH")).toBeInTheDocument();
        expect(
          screen.getByText("Cannot add quantities with dimensions [length] and [time].")
        ).toBeInTheDocument();
      });

      it("displays dimensional failure in LayerPipelineMatrix", () => {
        const mismatchResult: FindingResult = {
          job_id: "test-mismatch-2",
          state: "FAIL",
          diagnostic_code: "DIMENSIONAL_MISMATCH",
          message: "Dimensional violation",
          dimensions_verified: false,
          diagnostics: ["Dimensional violation"],
          layer_findings: {
            3: {
              layer: 3,
              name: "Dimensional Analysis",
              state: "FAIL",
              diagnostic_code: "DIMENSIONAL_MISMATCH",
              message: "meter + second rejected",
              diagnostics: ["Dimensional inconsistency detected by Pint"],
            },
          },
        };

        render(<LayerPipelineMatrix layers={mismatchResult.layer_findings} />);
        expect(screen.getByText(/Dimensional Analysis/i)).toBeInTheDocument();
        expect(screen.getByText("FAIL")).toBeInTheDocument();
      });
    });

    describe("2.2 Mathematical singularity & domain extremes", () => {
      it("constructs division by zero AST (x / 0) and verifies boundary warning handling", () => {
        const divByZeroAst: ExprNode = {
          node_type: "binary_op",
          op: "/",
          left: { node_type: "variable", value: "x" },
          right: { node_type: "constant", value: 0 },
        };

        const latex = exprNodeToLatex(divByZeroAst);
        expect(latex).toContain("0");

        const singularityResult: FindingResult = {
          job_id: "singularity-1",
          state: "WARNING",
          diagnostic_code: "POTENTIAL_SINGULARITY",
          message: "Expression contains explicit division by zero.",
          dimensions_verified: true,
          diagnostics: ["Expression contains explicit division by zero."],
          layer_findings: {
            2: {
              layer: 2,
              name: "Boundary & Singularities",
              state: "WARNING",
              diagnostic_code: "DIVISION_BY_ZERO",
              message: "Constant zero in denominator detected.",
              diagnostics: ["Denominator evaluates to 0"],
            },
          },
        };

        render(
          <ValidationStatusBar
            result={singularityResult}
            isValidating={false}
            onValidate={jest.fn()}
          />
        );

        const badge = screen.getByTestId("finding-state-badge");
        expect(badge).toHaveTextContent("WARNING");
        expect(screen.getByText("POTENTIAL_SINGULARITY")).toBeInTheDocument();
      });

      it("handles domain violations such as sqrt of negative constant", () => {
        const sqrtNegAst: ExprNode = {
          node_type: "function_call",
          func: "sqrt",
          args: [{ node_type: "constant", value: -16 }],
        };

        const latex = exprNodeToLatex(sqrtNegAst);
        expect(latex).toContain("\\sqrt{-16}");

        const domainViolationResult: FindingResult = {
          job_id: "domain-1",
          state: "FAIL",
          diagnostic_code: "DOMAIN_ERROR",
          message: "sqrt argument must be non-negative in real domain.",
          dimensions_verified: true,
          diagnostics: ["sqrt argument must be non-negative in real domain."],
          layer_findings: {
            2: {
              layer: 2,
              name: "Boundary & Singularities",
              state: "FAIL",
              diagnostic_code: "DOMAIN_ERROR",
              message: "Non-negative domain restriction violated.",
              diagnostics: ["Input value -16 < 0 for sqrt"],
            },
          },
        };

        render(
          <ValidationStatusBar
            result={domainViolationResult}
            isValidating={false}
            onValidate={jest.fn()}
          />
        );

        const badge = screen.getByTestId("finding-state-badge");
        expect(badge).toHaveTextContent("FAIL");
        expect(screen.getByText("DOMAIN_ERROR")).toBeInTheDocument();
      });
    });

    describe("2.3 Incomplete canvas graphs & missing operand handling", () => {
      const vars: VariableSpec[] = [
        { symbol: "v", name: "Velocity", unit: "meter / second", domain: "real" },
      ];

      it("throws TranslationError if EquationRootNode has no incoming connection", () => {
        const nodes: MathCanvasNode[] = [
          { id: "root1", type: "equationRootNode", position: { x: 0, y: 0 }, data: { name: "R" } },
        ];
        expect(() => graphToAst(nodes, [], vars)).toThrow(TranslationError);
        expect(() => graphToAst(nodes, [], vars)).toThrow(/Root node is not connected to an expression/i);
      });

      it("throws TranslationError when BinaryOpNode is missing left operand", () => {
        const nodes: MathCanvasNode[] = [
          { id: "v1", type: "variableNode", position: { x: 0, y: 0 }, data: { symbol: "v" } },
          { id: "op1", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "+" } },
        ];
        const edges: MathCanvasEdge[] = [
          { id: "e1", source: "v1", sourceHandle: "output", target: "op1", targetHandle: "right" },
        ];
        expect(() => graphToAst(nodes, edges, vars)).toThrow(TranslationError);
        expect(() => graphToAst(nodes, edges, vars)).toThrow(/missing left operand/i);
      });

      it("throws TranslationError when BinaryOpNode is missing right operand", () => {
        const nodes: MathCanvasNode[] = [
          { id: "v1", type: "variableNode", position: { x: 0, y: 0 }, data: { symbol: "v" } },
          { id: "op1", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "+" } },
        ];
        const edges: MathCanvasEdge[] = [
          { id: "e1", source: "v1", sourceHandle: "output", target: "op1", targetHandle: "left" },
        ];
        expect(() => graphToAst(nodes, edges, vars)).toThrow(TranslationError);
        expect(() => graphToAst(nodes, edges, vars)).toThrow(/missing right operand/i);
      });

      it("throws TranslationError if variable node has empty symbol", () => {
        const nodes: MathCanvasNode[] = [
          { id: "v_empty", type: "variableNode", position: { x: 0, y: 0 }, data: { symbol: "" } },
        ];
        expect(() => graphToAst(nodes, [], vars)).toThrow(TranslationError);
        expect(() => graphToAst(nodes, [], vars)).toThrow(/Variable node has no symbol selected/i);
      });
    });

    describe("2.4 AST cycle detection & recursion depth guardrails (>15 depth)", () => {
      const vars: VariableSpec[] = [
        { symbol: "x", name: "Position", unit: "meter", domain: "real" },
      ];

      it("detects and rejects direct cycle (op1 -> op2 -> op1)", () => {
        const nodes: MathCanvasNode[] = [
          { id: "op1", type: "binaryOpNode", position: { x: 0, y: 0 }, data: { op: "+" } },
          { id: "op2", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "*" } },
          { id: "c1", type: "constantNode", position: { x: 0, y: 100 }, data: { value: 1 } },
        ];
        const edges: MathCanvasEdge[] = [
          { id: "e1", source: "op2", sourceHandle: "output", target: "op1", targetHandle: "left" },
          { id: "e2", source: "c1", sourceHandle: "output", target: "op1", targetHandle: "right" },
          { id: "e3", source: "op1", sourceHandle: "output", target: "op2", targetHandle: "left" },
          { id: "e4", source: "c1", sourceHandle: "output", target: "op2", targetHandle: "right" },
        ];

        expect(() => graphToAst(nodes, edges, vars)).toThrow(TranslationError);
        expect(() => graphToAst(nodes, edges, vars)).toThrow(/Cyclic graph detected/i);
      });

      it("rejects AST chain exceeding recursion depth guardrail (>15 depth)", () => {
        const nodes: MathCanvasNode[] = [
          { id: "c0", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 1 } },
        ];
        const edges: MathCanvasEdge[] = [];

        // Build a chain of 16 unary operators (depth = 16)
        for (let i = 1; i <= 16; i++) {
          nodes.push({
            id: `neg_${i}`,
            type: "unaryOpNode",
            position: { x: i * 20, y: 0 },
            data: { op: "neg" },
          });
          const prevId = i === 1 ? "c0" : `neg_${i - 1}`;
          edges.push({
            id: `e_${i}`,
            source: prevId,
            sourceHandle: "output",
            target: `neg_${i}`,
            targetHandle: "left",
          });
        }

        expect(() => graphToAst(nodes, edges, vars)).toThrow(TranslationError);
        expect(() => graphToAst(nodes, edges, vars)).toThrow(/AST recursion depth exceeded guardrail limit/i);
      });
    });
  });

  // =========================================================================
  // TIER 3: CROSS-FEATURE COMBINATIONS
  // =========================================================================
  describe("Tier 3: Cross-Feature Combinations", () => {
    describe("3.1 Preset selection and AST translation", () => {
      it("round-trips Einstein E = mc^2 without fabricating a verification result", () => {
        const einstein = CANONICAL_PRESETS.find((p) => p.id === "einstein-energy")!;
        expect(einstein).toBeDefined();

        // 1. Convert AST to React Flow DAG
        const { nodes, edges } = astToGraph(einstein.ast, einstein.variables);
        expect(nodes.length).toBeGreaterThanOrEqual(4);
        expect(edges.length).toBeGreaterThanOrEqual(3);

        // 2. Convert graph back to canonical AST
        const roundTripAst = graphToAst(nodes, edges, einstein.variables);
        expect(roundTripAst).toEqual(einstein.ast);

        // 3. LaTeX parity check
        const latex = exprNodeToLatex(roundTripAst);
        expect(latex).toContain("m");
        expect(latex).toContain("c");

        expect(roundTripAst).toEqual(einstein.ast);
      });

      it("round-trips Newton's Gravity AST and declared variables", () => {
        const gravity = CANONICAL_PRESETS.find((p) => p.id === "newton-gravity")!;
        const { nodes, edges } = astToGraph(gravity.ast, gravity.variables);
        const roundTripAst = graphToAst(nodes, edges, gravity.variables);

        expect(roundTripAst).toEqual(gravity.ast);
        expect(gravity.variables.map((variable) => variable.symbol)).toContain("G");
      });
    });

    describe("3.2 Dark mode theme tokens -> glass styling classes", () => {
      it("verifies tailwind obsidian and neon science tokens in globals.css", () => {
        const globalsCssPath = path.resolve(__dirname, "../src/app/globals.css");
        const globalsCss = fs.readFileSync(globalsCssPath, "utf-8");

        expect(globalsCss).toContain("@import \"katex/dist/katex.min.css\";");
        expect(globalsCss).toContain(".dark");
        expect(globalsCss).toContain("--background: #030712");
        expect(globalsCss).toContain(".glass-panel");
        expect(globalsCss).toContain(".glass-card");
        expect(globalsCss).toContain(".glow-cyan");
        expect(globalsCss).toContain(".animate-pulse-flow");
      });

      it("verifies tailwind config dark mode configuration", () => {
        const tailwindConfigPath = path.resolve(__dirname, "../tailwind.config.ts");
        const tailwindConfig = fs.readFileSync(tailwindConfigPath, "utf-8");

        expect(tailwindConfig).toMatch(/darkMode:\s*["']class["']/);
        expect(tailwindConfig).toContain("#030712");
        expect(tailwindConfig).toContain("glow-cyan");
      });
    });

    describe("3.3 Variable manifest symbol changes -> Live canvas node sync", () => {
      it("synchronizes declared variables in manifest with VariableNode select dropdown", () => {
        const initialVars: VariableSpec[] = [
          { symbol: "x", name: "Position", unit: "meter", domain: "real" },
          { symbol: "v", name: "Velocity", unit: "meter / second", domain: "real" },
        ];
        const onVarsChange = jest.fn();

        const { rerender } = render(
          <div>
            <VariableDeclarationPanel
              variables={initialVars}
              onVariablesChange={onVarsChange}
              usedSymbols={new Set(["x"])}
            />
            <VariableNode
              id="node_v"
              data={{ symbol: "x", availableSymbols: initialVars, onChange: jest.fn() }}
              type="variableNode"
              zIndex={1}
              isConnectable={true}
              positionAbsoluteX={0}
              positionAbsoluteY={0}
              selected={false}
              dragging={false}
              selectable={true}
              deletable={true}
              draggable={true}
            />
          </div>
        );

        expect(screen.getByText(/Symbol-First Declaration Panel/i)).toBeInTheDocument();
        expect(screen.getByText(/2 declared/i)).toBeInTheDocument();
        expect(screen.getByLabelText("Variable symbol for node node_v")).toHaveValue("x");

        // Add variable to manifest
        const updatedVars: VariableSpec[] = [
          ...initialVars,
          { symbol: "E", name: "Energy", unit: "joule", domain: "positive_real" },
        ];

        rerender(
          <div>
            <VariableDeclarationPanel
              variables={updatedVars}
              onVariablesChange={onVarsChange}
              usedSymbols={new Set(["x"])}
            />
            <VariableNode
              id="node_v"
              data={{ symbol: "x", availableSymbols: updatedVars, onChange: jest.fn() }}
              type="variableNode"
              zIndex={1}
              isConnectable={true}
              positionAbsoluteX={0}
              positionAbsoluteY={0}
              selected={false}
              dragging={false}
              selectable={true}
              deletable={true}
              draggable={true}
            />
          </div>
        );

        expect(screen.getByText(/3 declared/i)).toBeInTheDocument();
        const select = screen.getByLabelText("Variable symbol for node node_v");
        expect(select.querySelectorAll("option").length).toBe(3);
      });
    });
  });

  // =========================================================================
  // TIER 4: REAL-WORLD APPLICATION SCENARIOS
  // =========================================================================
  describe("Tier 4: Real-World Application Scenarios", () => {
    describe("4.1 Local equation draft workflow", () => {
      it("does not treat an unknown route slug as a project record", async () => {
        const originalFetch = global.fetch;
        global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404,
          statusText: "Not Found", json: async () => ({ detail: "Project not found" }) });
        try {
        // Mount EquationEditorPage
        render(
          <EquationEditorPage
            params={Promise.resolve({ slug: "general-relativity" })}
          />
        );

        await screen.findByText(/Stored project records could not be loaded: Failed to fetch project: Project not found/);
        expect(screen.getByText("Project records are unavailable.")).toBeInTheDocument();

        // Failed hydration must not substitute sample mathematics or writable content.
        const canvas = screen.getByTestId("xyflow-mock-canvas");
        expect(canvas).toBeInTheDocument();
        expect(canvas).toHaveAttribute("data-node-count", "0");

        // 3. Trigger verification action via text query
        const validateBtn = screen.getByText(/Run Compute Verification/i);
        expect(validateBtn).toBeInTheDocument();
        expect(validateBtn).toBeDisabled();

        await waitFor(() => {
          expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
        });
        expect(screen.queryByText("PASS")).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Save draft" })).not.toBeInTheDocument();
        expect(global.fetch).toHaveBeenCalledTimes(1);
        } finally { global.fetch = originalFetch; }
      });
    });

    describe("4.2 Network resilience and backend-only results", () => {
  it("surfaces backend unavailability instead of manufacturing a validation result", async () => {
        // Mock global fetch network error
        const originalFetch = (global as any).fetch;
        (global as any).fetch = jest.fn().mockRejectedValue(new Error("Network connection refused"));

        const payload = {
          expression_ast: CANONICAL_PRESETS[1].ast, // E = mc^2
          variables: CANONICAL_PRESETS[1].variables,
        };

        await expect(validateEquationAst(payload)).rejects.toThrow(/Network connection refused/);

        if (originalFetch) {
          (global as any).fetch = originalFetch;
        } else {
          delete (global as any).fetch;
        }
      });

      it("keeps state untested when no backend result exists", () => {
        render(<ValidationStatusBar result={null} isValidating={false} onValidate={jest.fn()} />);
        expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
        expect(screen.queryByText("PREFLIGHT_OK")).not.toBeInTheDocument();
      });
    });
  });
});
