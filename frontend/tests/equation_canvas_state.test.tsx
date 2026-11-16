import React, { StrictMode } from "react";
import { act, renderHook } from "@testing-library/react";
import { useEquationCanvas } from "@/hooks/useEquationCanvas";
import { validateEquationAst } from "@/lib/api";
import type { FindingResult, VariableSpec } from "@/types/contracts";

jest.mock("@/lib/api", () => ({ validateEquationAst: jest.fn() }));

const finding: FindingResult = {
  job_id: "current-run", state: "PASS", diagnostic_code: "DIMENSIONS_MATCH",
  message: "Backend result", dimensions_verified: true, diagnostics: [],
};
const variable: VariableSpec = { symbol: "x", name: "Length", unit: "meter", domain: "real" };
const wrapper = ({ children }: React.PropsWithChildren) => <StrictMode>{children}</StrictMode>;
const validate = validateEquationAst as jest.MockedFunction<typeof validateEquationAst>;

function deferred() {
  let resolve!: (result: FindingResult) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<FindingResult>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function setup() {
  const hook = renderHook(useEquationCanvas, { wrapper });
  act(() => hook.result.current.replaceCanvas({ node_type: "constant", value: 1 }, []));
  return hook;
}

describe("canvas state under React StrictMode", () => {
  beforeEach(() => { validate.mockReset(); validate.mockResolvedValue(finding); });

  it("batches multiple node edits without losing updates or leaking stale root previews", async () => {
    const { result } = setup();
    await act(async () => { await result.current.handleValidate(); });
    const originalEdge = result.current.edges[0];
    act(() => {
      result.current.handleNodeDataChange("node_1", { value: 2 });
      result.current.onNodesChange([
        { id: "node_1", type: "position", position: { x: 35, y: 70 } },
        { id: "node_1", type: "select", selected: true },
      ]);
      result.current.onEdgesChange([{ type: "remove", id: originalEdge.id }]);
      result.current.onEdgesChange([{ type: "add", item: { ...originalEdge, selected: true } }]);
      result.current.handleAddNode("constant");
      result.current.handleAddNode("constant");
    });
    expect(result.current.nodes).toHaveLength(4);
    expect(new Set(result.current.nodes.map((node) => node.id)).size).toBe(4);
    expect(result.current.translationError).toMatch(/Disconnected/);
    expect(result.current.validationResult).toBeNull();
    expect(result.current.computedResult.value).toBeNull();
    expect(result.current.nodes.find((node) => node.type === "equationRootNode")?.data)
      .toMatchObject({ latex: "", computedValue: undefined });
    expect(result.current.nodes.find((node) => node.id === "node_1")).toMatchObject({
      position: { x: 35, y: 70 }, selected: true, data: { value: 2 },
    });
    expect(result.current.edges).toEqual([{ ...originalEdge, selected: true }]);
    expect(validate).toHaveBeenCalledTimes(1);
    act(() => result.current.onNodesChange(result.current.nodes.filter((node) => node.id.startsWith("draft_")).map((node) => ({ type: "remove", id: node.id }))));
    expect(result.current.computedResult.value).toBe(2);
    expect(result.current.currentAst).toEqual({ node_type: "constant", value: 2 });
    expect(result.current.validationResult).toBeNull();
    await act(async () => { await result.current.handleValidate(); });
    expect(validate).toHaveBeenLastCalledWith({ expression_ast: { node_type: "constant", value: 2 }, variables: [] });
    expect(validate).toHaveBeenCalledTimes(2);
  });

  it("applies two connection events in one batch against the latest graph", async () => {
    const { result } = setup();
    act(() => result.current.replaceCanvas(null, []));
    act(() => {
      result.current.handleAddNode("constant");
      result.current.handleAddNode("binary_op");
    });
    const [source, target] = result.current.nodes;
    act(() => {
      result.current.onConnect({ source: source.id, sourceHandle: "output", target: target.id, targetHandle: "left" });
      result.current.onConnect({ source: source.id, sourceHandle: "output", target: target.id, targetHandle: "right" });
    });
    expect(result.current.edges).toHaveLength(2);
    expect(result.current.computedResult.value).toBe(2);
    expect(result.current.translationError).toBeNull();
    await act(async () => { await result.current.handleValidate(); });
    expect(validate).toHaveBeenCalledTimes(1);
  });

  it("does not overwrite a batched semantic edit when auto-layout runs", () => {
    const { result } = setup();
    act(() => {
      result.current.handleNodeDataChange("node_1", { value: 7 });
      result.current.handleAutoLayout();
    });
    expect(result.current.currentAst).toEqual({ node_type: "constant", value: 7 });
    expect(result.current.computedResult.value).toBe(7);
    act(() => {
      result.current.handleAddNode("constant");
      result.current.handleAutoLayout();
    });
    expect(result.current.nodes).toHaveLength(3);
    expect(result.current.translationError).toMatch(/Disconnected/);
    expect(result.current.currentAst).toBeNull();
  });

  it("preserves shared operands, edge identity and pending validation when layout precedes an edit", async () => {
    const { result } = setup();
    act(() => result.current.replaceCanvas(null, []));
    act(() => {
      result.current.handleAddNode("constant");
      result.current.handleAddNode("binary_op");
    });
    const [source, target] = result.current.nodes;
    act(() => {
      result.current.onConnect({ source: source.id, sourceHandle: "output", target: target.id, targetHandle: "left" });
      result.current.onConnect({ source: source.id, sourceHandle: "output", target: target.id, targetHandle: "right" });
    });
    const originalEdges = result.current.edges;
    const pending = deferred();
    validate.mockReturnValueOnce(pending.promise);
    let request!: Promise<void>;
    act(() => { request = result.current.handleValidate(); });
    act(() => result.current.handleAutoLayout());
    expect(result.current.nodes.map((node) => node.id)).toEqual([source.id, target.id]);
    expect(result.current.edges).toBe(originalEdges);
    expect(result.current.nodes[0].position).not.toEqual(source.position);
    expect(result.current.computedResult.value).toBe(2);
    expect(result.current.isValidating).toBe(true);
    await act(async () => { pending.resolve(finding); await request; });
    expect(result.current.validationResult).toEqual(finding);

    act(() => {
      result.current.handleAutoLayout();
      result.current.handleNodeDataChange(source.id, { value: 2 });
    });
    expect(result.current.nodes.map((node) => node.id)).toEqual([source.id, target.id]);
    expect(result.current.edges).toBe(originalEdges);
    expect(result.current.computedResult.value).toBe(4);
    expect(result.current.validationResult).toBeNull();
    await act(async () => { await result.current.handleValidate(); });
    expect(validate).toHaveBeenLastCalledWith({
      expression_ast: {
        node_type: "binary_op", op: "+",
        left: { node_type: "constant", value: 2 }, right: { node_type: "constant", value: 2 },
      },
      variables: [],
    });
  });

  it("validates the updated snapshot when an edit and validation occur in one batch", async () => {
    const { result } = setup();
    const pending = deferred();
    validate.mockReturnValueOnce(pending.promise);
    let request!: Promise<void>;
    act(() => {
      result.current.handleNodeDataChange("node_1", { value: 2 });
      request = result.current.handleValidate();
    });
    expect(result.current.computedResult.value).toBe(2);
    expect(validate).toHaveBeenCalledWith({ expression_ast: { node_type: "constant", value: 2 }, variables: [] });
    await act(async () => { pending.resolve(finding); await request; });
    expect(result.current.validationResult).toEqual(finding);
  });

  it("blocks validation when a used declaration is removed in the same batch", async () => {
    const { result } = setup();
    act(() => result.current.replaceCanvas({ node_type: "variable", value: "x" }, [variable]));
    await act(async () => { await result.current.handleValidate(); });
    expect(result.current.validationResult).toEqual(finding);
    await act(async () => {
      result.current.handleVariablesChange([]);
      await result.current.handleValidate();
    });
    expect(validate).toHaveBeenCalledTimes(1);
    expect(result.current.currentAst).toBeNull();
    expect(result.current.translationError).toMatch(/Symbol 'x' is undeclared/);
    expect(result.current.validationResult).toBeNull();
    expect(result.current.isValidating).toBe(false);
  });

  it.each(["removed", "renamed"])("recomputes every preview immediately when a used declaration is %s", async (change) => {
    const { result } = setup();
    act(() => result.current.replaceCanvas({ node_type: "variable", value: "x" }, [variable]));
    await act(async () => { await result.current.handleValidate(); });
    expect(result.current.currentLatex).toBe("x");
    act(() => result.current.handleVariablesChange(change === "removed" ? [] : [{ ...variable, symbol: "y" }]));
    expect(result.current.translationError).toMatch(/Symbol 'x' is undeclared/);
    expect(result.current.currentAst).toBeNull();
    expect(result.current.currentLatex).toBe("");
    expect(result.current.computedResult).toEqual({ value: null, error: null });
    expect(result.current.nodes.find((node) => node.type === "equationRootNode")?.data)
      .toMatchObject({ latex: "", computedValue: undefined });
    expect(result.current.validationResult).toBeNull();
    await act(async () => { await result.current.handleValidate(); });
    expect(validate).toHaveBeenCalledTimes(1);
    act(() => result.current.handleVariablesChange([{ ...variable, unit: "second", domain: "positive_real" }]));
    expect(result.current.translationError).toBeNull();
    expect(result.current.currentAst).toEqual({ node_type: "variable", value: "x" });
    expect(result.current.currentLatex).toBe("x");
    expect(result.current.nodes.find((node) => node.type === "equationRootNode")?.data).toMatchObject({ latex: "x" });
    expect(result.current.validationResult).toBeNull();
    await act(async () => { await result.current.handleValidate(); });
    expect(validate.mock.calls[1][0].variables[0]).toMatchObject({ unit: "second", domain: "positive_real" });
  });

  it.each(["unit", "domain"])("clears a completed finding immediately after a %s-only edit", async (field) => {
    const { result } = setup();
    const ast = { node_type: "variable", value: "x" } as const;
    act(() => result.current.replaceCanvas(ast, [variable]));
    await act(async () => { await result.current.handleValidate(); });
    expect(result.current.validationResult).toEqual(finding);
    const updated: VariableSpec = field === "unit"
      ? { ...variable, unit: "second" }
      : { ...variable, domain: "positive_real" };

    act(() => result.current.handleVariablesChange([updated]));

    expect(result.current.currentAst).toEqual(ast);
    expect(result.current.currentLatex).toBe("x");
    expect(result.current.variables).toEqual([updated]);
    expect(result.current.validationResult).toBeNull();
    expect(result.current.isValidating).toBe(false);
    expect(result.current.translationError).toBeNull();
    expect(validate).toHaveBeenCalledTimes(1);
  });

  it.each(["unit", "domain"])("validates new %s declarations when editing and validating in one batch", async (field) => {
    const { result } = setup();
    const ast = { node_type: "variable", value: "x" } as const;
    act(() => result.current.replaceCanvas(ast, [variable]));
    const updated: VariableSpec = field === "unit"
      ? { ...variable, unit: "second" }
      : { ...variable, domain: "positive_real" };

    await act(async () => {
      result.current.handleVariablesChange([updated]);
      await result.current.handleValidate();
    });

    expect(validate).toHaveBeenCalledTimes(1);
    expect(validate).toHaveBeenCalledWith({ expression_ast: ast, variables: [updated] });
    expect(result.current.currentAst).toEqual(ast);
    expect(result.current.variables).toEqual([updated]);
    expect(result.current.validationResult).toEqual(finding);
  });

  it.each(["unit", "domain"])("invalidates pending findings after a used declaration's %s changes even when the AST is unchanged", async (field) => {
    const { result } = setup();
    const ast = { node_type: "variable", value: "x" } as const;
    act(() => result.current.replaceCanvas(ast, [variable]));
    await act(async () => { await result.current.handleValidate(); });
    expect(result.current.validationResult).toEqual(finding);

    const old = deferred();
    const current = deferred();
    validate.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise);
    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => { first = result.current.handleValidate(); });
    const updated: VariableSpec = field === "unit"
      ? { ...variable, unit: "second" }
      : { ...variable, domain: "positive_real" };
    act(() => result.current.handleVariablesChange([updated]));
    expect(result.current.currentAst).toEqual(ast);
    expect(result.current.currentLatex).toBe("x");
    expect(result.current.translationError).toBeNull();
    expect(result.current.validationResult).toBeNull();
    expect(result.current.isValidating).toBe(false);

    await act(async () => { old.resolve({ ...finding, job_id: "obsolete-declaration-run" }); await first; });
    expect(result.current.validationResult).toBeNull();
    expect(result.current.isValidating).toBe(false);
    act(() => { second = result.current.handleValidate(); });
    expect(validate).toHaveBeenLastCalledWith({ expression_ast: ast, variables: [updated] });
    expect(result.current.isValidating).toBe(true);
    const currentFinding = { ...finding, job_id: "updated-declaration-run" };
    await act(async () => { current.resolve(currentFinding); await second; });
    expect(result.current.validationResult).toEqual(currentFinding);
    expect(result.current.isValidating).toBe(false);
  });

  it.each(["node", "variables", "edge", "preset"])("ignores a late success after a %s semantic edit", async (edit) => {
    const { result } = setup();
    const old = deferred();
    validate.mockReturnValueOnce(old.promise);
    let request!: Promise<void>;
    act(() => { request = result.current.handleValidate(); });
    act(() => {
      if (edit === "node") result.current.handleNodeDataChange("node_1", { value: 4 });
      if (edit === "variables") result.current.handleVariablesChange([variable]);
      if (edit === "edge") result.current.onEdgesChange([{ type: "remove", id: result.current.edges[0].id }]);
      if (edit === "preset") result.current.replaceCanvas({ node_type: "constant", value: 6 }, []);
    });
    expect(result.current.isValidating).toBe(false);
    await act(async () => { old.resolve(finding); await request; });
    expect(result.current.validationResult).toBeNull();
    expect(result.current.isValidating).toBe(false);
    if (edit === "node") expect(result.current.computedResult.value).toBe(4);
    if (edit === "edge") expect(result.current.computedResult.value).toBeNull();
    if (edit === "preset") expect(result.current.computedResult.value).toBe(6);
  });

  it("ignores a stale rejection and finally while a newer request is pending", async () => {
    const { result } = setup();
    const old = deferred();
    const current = deferred();
    validate.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise);
    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => { first = result.current.handleValidate(); });
    act(() => result.current.handleNodeDataChange("node_1", { value: 3 }));
    act(() => { second = result.current.handleValidate(); });
    await act(async () => { old.reject(new Error("Obsolete transport error")); await first; });
    expect(result.current.isValidating).toBe(true);
    expect(result.current.translationError).toBeNull();
    await act(async () => { current.resolve(finding); await second; });
    expect(result.current.validationResult?.job_id).toBe("current-run");
    expect(result.current.isValidating).toBe(false);
  });

  it.each(["success", "rejection"])("keeps the newer finding when an older %s arrives last", async (outcome) => {
    const { result } = setup();
    const old = deferred();
    const current = deferred();
    validate.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise);
    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => { first = result.current.handleValidate(); });
    act(() => result.current.handleNodeDataChange("node_1", { value: 3 }));
    act(() => { second = result.current.handleValidate(); });
    await act(async () => { current.resolve(finding); await second; });
    await act(async () => {
      if (outcome === "success") old.resolve({ ...finding, job_id: "obsolete-run", state: "FAIL" });
      else old.reject(new Error("Obsolete transport error"));
      await first;
    });
    expect(result.current.validationResult).toEqual(finding);
    expect(result.current.isValidating).toBe(false);
    expect(result.current.translationError).toBeNull();
    expect(result.current.computedResult.value).toBe(3);
  });

  it.each(["success", "rejection"])("ignores a late %s after an edit is undone to the original snapshot", async (outcome) => {
    const { result } = setup();
    const old = deferred();
    validate.mockReturnValueOnce(old.promise);
    let request!: Promise<void>;

    act(() => { request = result.current.handleValidate(); });
    act(() => result.current.handleNodeDataChange("node_1", { value: 2 }));
    act(() => result.current.handleNodeDataChange("node_1", { value: 1 }));

    expect(result.current.computedResult.value).toBe(1);
    expect(result.current.validationResult).toBeNull();
    await act(async () => {
      if (outcome === "success") old.resolve(finding);
      else old.reject(new Error("Obsolete transport error"));
      await request;
    });
    expect(result.current.validationResult).toBeNull();
    expect(result.current.isValidating).toBe(false);
    expect(result.current.translationError).toBeNull();
    expect(result.current.currentAst).toEqual({ node_type: "constant", value: 1 });
    expect(validate).toHaveBeenCalledTimes(1);
  });

  it.each(["success", "rejection"] as const)("ignores a settled late %s after clearing the canvas", async (outcome) => {
    const { result } = setup();
    const pending = deferred();
    validate.mockReturnValueOnce(pending.promise);
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);
    let request!: Promise<void>;

    try {
      act(() => { request = result.current.handleValidate(); });
      expect(result.current.isValidating).toBe(true);
      act(() => result.current.handleClear());
      expect(result.current.nodes).toEqual([]);
      expect(result.current.validationResult).toBeNull();
      expect(result.current.isValidating).toBe(false);

      await act(async () => {
        if (outcome === "success") pending.resolve(finding);
        else pending.reject(new Error("Obsolete transport error"));
        await request;
      });

      expect(result.current.validationResult).toBeNull();
      expect(result.current.isValidating).toBe(false);
      expect(result.current.translationError).toBeNull();
      expect(result.current.currentAst).toBeNull();
      expect(result.current.currentLatex).toBe("");
      expect(result.current.computedResult).toEqual({ value: null, error: null });
      expect(result.current.edges).toEqual([]);
      expect(validate).toHaveBeenCalledTimes(1);
    } finally {
      confirm.mockRestore();
    }
  });

  it("preserves both pending and completed findings during position/selection/measurement/layout changes", async () => {
    const { result } = setup();
    const pending = deferred();
    validate.mockReturnValueOnce(pending.promise);
    let request!: Promise<void>;
    act(() => { request = result.current.handleValidate(); });
    act(() => {
      result.current.onNodesChange([
        { id: "node_1", type: "position", position: { x: 24, y: 72 } },
        { id: "node_1", type: "select", selected: true },
        { id: "node_1", type: "dimensions", dimensions: { width: 180, height: 70 } },
      ]);
      result.current.onEdgesChange([{ id: result.current.edges[0].id, type: "select", selected: true }]);
    });
    expect(result.current.isValidating).toBe(true);
    expect(result.current.nodes.find((node) => node.id === "node_1")).toMatchObject({
      position: { x: 24, y: 72 }, selected: true, measured: { width: 180, height: 70 },
    });
    expect(result.current.edges[0].selected).toBe(true);
    await act(async () => { pending.resolve(finding); await request; });
    act(() => {
      result.current.onNodesChange([
        { id: "node_1", type: "position", position: { x: 48, y: 96 } },
        { id: "node_1", type: "select", selected: false },
        { id: "node_1", type: "dimensions", dimensions: { width: 190, height: 80 } },
      ]);
      result.current.onEdgesChange([{ id: result.current.edges[0].id, type: "select", selected: false }]);
    });
    expect(result.current.nodes.find((node) => node.id === "node_1")).toMatchObject({
      position: { x: 48, y: 96 }, selected: false, measured: { width: 190, height: 80 },
    });
    expect(result.current.edges[0].selected).toBe(false);
    expect(result.current.validationResult).toEqual(finding);
    act(() => result.current.handleAutoLayout());
    expect(result.current.validationResult).toEqual(finding);
    expect(result.current.computedResult.value).toBe(1);
    expect(result.current.nodes.find((node) => node.type === "equationRootNode")?.data)
      .toMatchObject({ latex: result.current.currentLatex, computedValue: 1 });
    expect(validate).toHaveBeenCalledTimes(1);
  });
});
