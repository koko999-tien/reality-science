import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import EquationEditorPage from "@/app/(dashboard)/projects/[slug]/editor/page";
import {
  fetchProjectBySlug,
  fetchVersionEquations,
  fetchVersionVariables,
  fetchVersionDraft,
  validateEquationAst,
} from "@/lib/api";
import { EquationModel, FindingResult, ResearchProjectModel, VariableModel } from "@/types/contracts";

let mockSlug = "test-project";
jest.mock("next/navigation", () => ({
  useParams: () => ({ slug: mockSlug }),
}));

jest.mock("@/components/equations/canvas/SymbolicCanvas", () => ({
  SymbolicCanvas: ({ onValidate, onClear, onNodeDataChange, onAddNode }: {
    onValidate: () => void;
    onClear: () => void;
    onNodeDataChange: (nodeId: string, data: Record<string, unknown>) => void;
    onAddNode: (type: string) => void;
  }) => {
    const React = require("react");
    return React.createElement(
      React.Fragment,
      null,
      React.createElement("button", { type: "button", onClick: onValidate }, "Test validation"),
      React.createElement("button", { type: "button", onClick: onClear }, "Clear canvas"),
      React.createElement(
        "button",
        { type: "button", onClick: () => onNodeDataChange("node_1", { value: "not-a-number" }) },
        "Break computation"
      ),
      React.createElement(
        "button",
        { type: "button", onClick: () => onAddNode("equation_root") },
        "Add equation_root"
      )
    );
  },
}));

jest.mock("@/components/equations/canvas/ScientificPresetsBar", () => ({
  ScientificPresetsBar: () => null,
  CANONICAL_PRESETS: [],
}));

jest.mock("@/lib/api", () => ({
  validateEquationAst: jest.fn(),
  fetchProjectBySlug: jest.fn().mockResolvedValue({ slug: "test-project", versions: [] }),
  fetchVersionEquations: jest.fn(),
  fetchVersionVariables: jest.fn(),
  fetchVersionDraft: jest.fn(),
}));

const passResult: FindingResult = {
  job_id: "server-run-1",
  state: "PASS",
  diagnostic_code: "DIMENSIONS_MATCH",
  message: "Backend finding",
  dimensions_verified: true,
  diagnostics: [],
};

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function projectFixture(slug: string, title: string): ResearchProjectModel {
  return {
    id: slug, slug, title, can_edit: true, visibility: "private_draft", is_frozen: false, created_at: "2026-11-16T00:00:00Z",
    versions: [{
      id: `${slug}-version`, project_id: slug, version_number: 1, title: `${title} draft`,
      publication_status: "draft", is_frozen: false, created_at: "2026-11-16T00:00:00Z",
    }],
  };
}

function equationFixture(versionId: string, value: number): EquationModel[] {
  return [{
    id: `${versionId}-equation`, version_id: versionId, label: "Fixture expression", latex_raw: String(value),
    canonical_ast_json: { node_type: "constant", value }, created_at: "2026-11-16T00:00:00Z",
  }];
}

describe("editor validation result integrity", () => {
  beforeEach(() => {
    mockSlug = "test-project";
    jest.resetAllMocks();
    window.history.replaceState(null, "", "/projects/test-project/editor");
    (fetchProjectBySlug as jest.Mock).mockResolvedValue({
      slug: "test-project",
      title: "Test project",
      can_edit: true,
      versions: [{ id: "version-1", version_number: 1, title: "Draft", publication_status: "draft", revision: 0 }],
    });
    (fetchVersionEquations as jest.Mock).mockResolvedValue([{
      id: "equation-1",
      version_id: "version-1",
      label: "Constant test expression",
      latex_raw: "1",
      canonical_ast_json: { node_type: "constant", value: 1 },
      created_at: "2026-11-16T00:00:00Z",
    }]);
    (fetchVersionVariables as jest.Mock).mockResolvedValue([]);
    // Compatibility fixtures exercise the same response races through the new
    // single snapshot API; these mocks are UI tests, never persistence evidence.
    (fetchVersionDraft as jest.Mock).mockImplementation(async (versionId: string) => {
      const [equations, variables] = await Promise.all([fetchVersionEquations(versionId), fetchVersionVariables(versionId)]);
      const title = versionId === "version-1" ? "Draft" : versionId === "project-b-version" ? "Project B draft" : "Project A draft";
      return { version: { id: versionId, version_number: 1, title, publication_status: "draft", revision: 0 }, equations, variables, units: [] };
    });
  });

  it("clears an earlier PASS while revalidating and after a transport failure", async () => {
    const validate = validateEquationAst as jest.MockedFunction<typeof validateEquationAst>;
    validate.mockResolvedValueOnce(passResult);
    let rejectSecond: ((error: Error) => void) | undefined;
    validate.mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectSecond = reject;
        })
    );

    render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
    await screen.findByText(/Version 1: Draft/i);
    const validateButton = screen.getByRole("button", { name: "Test validation" });

    fireEvent.click(validateButton);
    await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));

    fireEvent.click(validateButton);
    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("COMPUTING...");
    expect(screen.getByTestId("finding-state-badge")).not.toHaveTextContent("PASS");

    rejectSecond?.(new Error("Network connection refused"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Network connection refused");
    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
    expect(screen.getByTestId("finding-state-badge")).not.toHaveTextContent("PASS");
  });

  it("clears prior validation and numeric previews when a canvas edit cannot be computed", async () => {
    (validateEquationAst as jest.MockedFunction<typeof validateEquationAst>).mockResolvedValueOnce(passResult);

    render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
    await screen.findByText(/Version 1: Draft/i);
    fireEvent.click(screen.getByRole("button", { name: "Test validation" }));
    await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));
    expect(screen.getByText("R ≈ 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Break computation" }));

    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
    expect(screen.queryByText("PASS")).not.toBeInTheDocument();
    expect(screen.queryByText("R ≈ 1")).not.toBeInTheDocument();
    expect(screen.queryByText("AST preview · not a validation result")).not.toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("not a finite number");
  });

  it("keeps a project with no versions on an empty canvas", async () => {
    (fetchProjectBySlug as jest.Mock).mockResolvedValue({
      slug: "test-project",
      title: "Test project",
      versions: [],
    });
    render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);

    await screen.findByText(/No version is recorded for this project/i);
    expect(screen.queryByText("Local equation draft")).not.toBeInTheDocument();
    expect(validateEquationAst).not.toHaveBeenCalled();
  });

  it("does not replace a malformed stored equation with the local example", async () => {
    (fetchVersionEquations as jest.Mock).mockResolvedValueOnce([{
      id: "equation-bad",
      version_id: "version-1",
      label: "Malformed equation",
      latex_raw: "x +",
      canonical_ast_json: { node_type: "binary_op", op: "+", left: { node_type: "unknown" } },
      created_at: "2026-11-16T00:00:00Z",
    }]);

    render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("unknown AST node type");
    expect(screen.queryByText("Local equation draft")).not.toBeInTheDocument();
    expect(screen.getByText("Empty")).toBeInTheDocument();
    expect(validateEquationAst).not.toHaveBeenCalled();
  });

  it.each(["success", "rejection"])("returns to idle after clearing during validation and ignores its late %s", async (outcome) => {
    const validate = validateEquationAst as jest.MockedFunction<typeof validateEquationAst>;
    const pending = deferred<FindingResult>();
    validate.mockReturnValueOnce(pending.promise);
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);

    try {
      render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
      await screen.findByText(/Version 1: Draft/i);
      fireEvent.click(screen.getByRole("button", { name: "Test validation" }));
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("COMPUTING...");

      fireEvent.click(screen.getByRole("button", { name: "Clear canvas" }));

      expect(confirm).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
      await act(async () => {
        if (outcome === "success") pending.resolve(passResult);
        else pending.reject(new Error("Obsolete clear transport error"));
        await pending.promise.catch(() => undefined);
      });
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
      expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText("R ≈ 1")).not.toBeInTheDocument();
      expect(screen.queryByText("AST preview · not a validation result")).not.toBeInTheDocument();
      expect(screen.getByText("Empty")).toBeInTheDocument();
      expect(validate).toHaveBeenCalledTimes(1);
    } finally {
      confirm.mockRestore();
    }
  });

  it("removes a previous verified response and numeric preview when the canvas is reset", async () => {
    (validateEquationAst as jest.MockedFunction<typeof validateEquationAst>).mockResolvedValueOnce(passResult);
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);

    render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
    await screen.findByText(/Version 1: Draft/i);
    fireEvent.click(screen.getByRole("button", { name: "Test validation" }));
    await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));
    expect(screen.getByText("API REPORTED VERIFIED")).toBeInTheDocument();
    expect(screen.getByText("R ≈ 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear canvas" }));

    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
    expect(screen.queryByText("PASS")).not.toBeInTheDocument();
    expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();
    expect(screen.queryByText("R ≈ 1")).not.toBeInTheDocument();
    confirm.mockRestore();
  });

  it("clears prior validation when adding a node creates an invalid graph structure", async () => {
    (validateEquationAst as jest.MockedFunction<typeof validateEquationAst>).mockResolvedValueOnce(passResult);

    render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
    await screen.findByText(/Version 1: Draft/i);
    fireEvent.click(screen.getByRole("button", { name: "Test validation" }));
    await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));

    // The single-expression canvas must never silently choose the old connected root.
    fireEvent.click(screen.getByRole("button", { name: /Add.*equation_root/i }));

    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
    expect(screen.queryByText("PASS")).not.toBeInTheDocument();
    expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();
    expect(screen.queryByText("R ≈ 1")).not.toBeInTheDocument();
    expect(screen.queryByText("AST preview · not a validation result")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Multiple equation roots");
    fireEvent.click(screen.getByRole("button", { name: "Test validation" }));
    expect(validateEquationAst).toHaveBeenCalledTimes(1);
  });

  it("preserves the verified result when a used declaration deletion is canceled", async () => {
    (fetchVersionEquations as jest.Mock).mockResolvedValueOnce([{
      id: "equation-variable", version_id: "version-1", label: "Declared variable expression",
      latex_raw: "x", canonical_ast_json: { node_type: "variable", value: "x" }, created_at: "2026-11-16T00:00:00Z",
    }]);
    (fetchVersionVariables as jest.Mock).mockResolvedValueOnce([{
      id: "variable-x", version_id: "version-1", symbol: "x", name: "Length",
      unit: "meter", domain: "real", latex_presentation: "x",
    }]);
    (validateEquationAst as jest.MockedFunction<typeof validateEquationAst>).mockResolvedValueOnce(passResult);
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(false);

    try {
      render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
      await screen.findByText(/Version 1: Draft/i);
      const validateButton = screen.getByRole("button", { name: "Test validation" });
      fireEvent.click(validateButton);
      await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));

      fireEvent.click(screen.getByRole("button", { name: "Delete variable x" }));

      expect(confirm).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS");
      expect(screen.getByText("API REPORTED VERIFIED")).toBeInTheDocument();
      expect(screen.getByText("Length")).toBeInTheDocument();
      expect(screen.getByTestId("variable-table")).toHaveTextContent("meter");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByText("AST preview · not a validation result")).toBeInTheDocument();
      expect(validateEquationAst).toHaveBeenCalledTimes(1);
    } finally {
      confirm.mockRestore();
    }
  });

  it.each(["success", "rejection"])("keeps a newer declaration validation pending when an obsolete %s arrives after redeclaration", async (outcome) => {
    const validate = validateEquationAst as jest.MockedFunction<typeof validateEquationAst>;
    const ast = { node_type: "variable", value: "x" } as const;
    (fetchVersionEquations as jest.Mock).mockResolvedValueOnce([{
      id: "equation-variable", version_id: "version-1", label: "Declared variable expression",
      latex_raw: "x", canonical_ast_json: ast, created_at: "2026-11-16T00:00:00Z",
    }]);
    (fetchVersionVariables as jest.Mock).mockResolvedValueOnce([{
      id: "variable-x", version_id: "version-1", symbol: "x", name: "Length",
      unit: "meter", domain: "real", latex_presentation: "x",
    }]);
    let resolveOld!: (value: FindingResult) => void;
    let rejectOld!: (error: Error) => void;
    const old = new Promise<FindingResult>((resolve, reject) => { resolveOld = resolve; rejectOld = reject; });
    let resolveCurrent!: (value: FindingResult) => void;
    const current = new Promise<FindingResult>((resolve) => { resolveCurrent = resolve; });
    validate.mockReturnValueOnce(old).mockReturnValueOnce(current);
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);

    try {
      render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
      await screen.findByText(/Version 1: Draft/i);
      const validateButton = screen.getByRole("button", { name: "Test validation" });
      fireEvent.click(validateButton);
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("COMPUTING...");
      fireEvent.click(screen.getByRole("button", { name: "Delete variable x" }));
      expect(screen.getByRole("alert")).toHaveTextContent("Symbol 'x' is undeclared");
      fireEvent.click(validateButton);
      expect(validate).toHaveBeenCalledTimes(1);

      fireEvent.change(screen.getByLabelText("Variable symbol"), { target: { value: "x" } });
      fireEvent.change(screen.getByLabelText("Variable name"), { target: { value: "Time" } });
      fireEvent.change(screen.getByLabelText("Physical SI unit"), { target: { value: "second" } });
      fireEvent.change(screen.getByLabelText("Mathematical domain"), { target: { value: "positive_real" } });
      fireEvent.click(screen.getByRole("button", { name: "Declare Symbol" }));
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByText("AST preview · not a validation result")).toBeInTheDocument();
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
      expect(validate).toHaveBeenCalledTimes(1);
      fireEvent.click(validateButton);
      expect(validate).toHaveBeenCalledTimes(2);
      expect(validate).toHaveBeenLastCalledWith({
        expression_ast: ast,
        variables: [{ symbol: "x", name: "Time", unit: "second", domain: "positive_real", latex_presentation: "x" }],
      });

      await act(async () => {
        if (outcome === "success") resolveOld({ ...passResult, job_id: "obsolete-run" });
        else rejectOld(new Error("Obsolete transport error"));
        await old.catch(() => undefined);
      });
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("COMPUTING...");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();

      await act(async () => {
        resolveCurrent({ ...passResult, job_id: "current-declaration-run", state: "FAIL", message: "Current declaration finding" });
        await current;
      });
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("FAIL");
      expect(screen.getByText("Current declaration finding")).toBeInTheDocument();
    } finally {
      confirm.mockRestore();
    }
  });

  it("updates previews from the declaration panel and ignores a late result after deleting a used symbol", async () => {
    const validate = validateEquationAst as jest.MockedFunction<typeof validateEquationAst>;
    const ast = { node_type: "variable", value: "x" } as const;
    (fetchVersionEquations as jest.Mock).mockResolvedValueOnce([{
      id: "equation-variable",
      version_id: "version-1",
      label: "Declared variable expression",
      latex_raw: "x",
      canonical_ast_json: ast,
      created_at: "2026-11-16T00:00:00Z",
    }]);
    (fetchVersionVariables as jest.Mock).mockResolvedValueOnce([{
      id: "variable-x", version_id: "version-1", symbol: "x", name: "Length",
      unit: "meter", domain: "real", latex_presentation: "x",
    }]);
    let resolvePending!: (value: FindingResult) => void;
    const pending = new Promise<FindingResult>((resolve) => { resolvePending = resolve; });
    validate.mockResolvedValueOnce(passResult).mockReturnValueOnce(pending);
    const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);

    try {
      render(<EquationEditorPage params={Promise.resolve({ slug: "test-project" })} />);
      await screen.findByText(/Version 1: Draft/i);
      expect(screen.getByText("AST preview · not a validation result")).toBeInTheDocument();
      const validateButton = screen.getByRole("button", { name: "Test validation" });
      fireEvent.click(validateButton);
      await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));
      fireEvent.click(validateButton);
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("COMPUTING...");

      fireEvent.click(screen.getByRole("button", { name: "Delete variable x" }));
      expect(confirm).toHaveBeenCalledTimes(1);
      expect(screen.getByRole("alert")).toHaveTextContent("Symbol 'x' is undeclared");
      expect(screen.getByText("Empty")).toBeInTheDocument();
      expect(screen.queryByText("AST preview · not a validation result")).not.toBeInTheDocument();
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
      await act(async () => { resolvePending(passResult); await pending; });
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
      expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();
      fireEvent.click(validateButton);
      expect(validate).toHaveBeenCalledTimes(2);

      fireEvent.change(screen.getByLabelText("Variable symbol"), { target: { value: "x" } });
      fireEvent.change(screen.getByLabelText("Variable name"), { target: { value: "Time" } });
      fireEvent.change(screen.getByLabelText("Physical SI unit"), { target: { value: "second" } });
      fireEvent.change(screen.getByLabelText("Mathematical domain"), { target: { value: "positive_real" } });
      fireEvent.click(screen.getByRole("button", { name: "Declare Symbol" }));
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.queryByText("Empty")).not.toBeInTheDocument();
      expect(screen.getByText("AST preview · not a validation result")).toBeInTheDocument();
      expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("NOT YET TESTED");
      expect(validate).toHaveBeenCalledTimes(2);

      validate.mockResolvedValueOnce({ ...passResult, job_id: "updated-declaration-run" });
      fireEvent.click(validateButton);
      expect(validate).toHaveBeenLastCalledWith({
        expression_ast: ast,
        variables: [{ symbol: "x", name: "Time", unit: "second", domain: "positive_real", latex_presentation: "x" }],
      });
      await waitFor(() => expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS"));
    } finally {
      confirm.mockRestore();
    }
  });

  it.each([
    ["project", "success"],
    ["project", "rejection"],
    ["equations", "success"],
    ["equations", "rejection"],
    ["variables", "success"],
    ["variables", "rejection"],
  ] as const)("keeps route B under StrictMode after stale route A %s %s", async (stage, outcome) => {
    mockSlug = "project-a";
    const projectA = projectFixture("project-a", "Project A");
    const projectB = projectFixture("project-b", "Project B");
    const oldProject = deferred<ResearchProjectModel>();
    const oldEquations = deferred<EquationModel[]>();
    const oldVariables = deferred<VariableModel[]>();
    const variablesA: VariableModel[] = [{
      id: "variable-a", version_id: "project-a-version", symbol: "obsolete", name: "Obsolete declaration",
      unit: "meter", domain: "real", created_at: "2026-11-16T00:00:00Z",
    }];

    (fetchProjectBySlug as jest.Mock).mockImplementation((slug: string) => slug === "project-b"
      ? Promise.resolve(projectB)
      : stage === "project" ? oldProject.promise : Promise.resolve(projectA));
    (fetchVersionEquations as jest.Mock).mockImplementation((versionId: string) => versionId === "project-b-version"
      ? Promise.resolve(equationFixture(versionId, 2)) : oldEquations.promise);
    (fetchVersionVariables as jest.Mock).mockImplementation((versionId: string) => versionId === "project-b-version"
      ? Promise.resolve([]) : oldVariables.promise);
    if (stage === "equations") oldVariables.resolve(variablesA);
    if (stage === "variables") oldEquations.resolve(equationFixture("project-a-version", 41));

    const view = render(<React.StrictMode><EquationEditorPage params={Promise.resolve({ slug: "project-a" })} /></React.StrictMode>);
    expect(fetchProjectBySlug).toHaveBeenCalledTimes(2);
    if (stage !== "project") {
      await waitFor(() => expect(fetchVersionEquations).toHaveBeenCalledWith("project-a-version"));
      expect(fetchVersionVariables).toHaveBeenCalledWith("project-a-version");
    }

    mockSlug = "project-b";
    view.rerender(<React.StrictMode><EquationEditorPage params={Promise.resolve({ slug: "project-b" })} /></React.StrictMode>);
    await screen.findByText("R ≈ 2");
    expect(validateEquationAst).not.toHaveBeenCalled();
    (validateEquationAst as jest.Mock).mockResolvedValueOnce({ ...passResult, message: "Project B finding" });
    fireEvent.click(screen.getByRole("button", { name: "Test validation" }));
    await screen.findByText("Project B finding");

    await act(async () => {
      if (stage === "project") {
        if (outcome === "success") oldProject.resolve(projectA);
        else oldProject.reject(new Error("Stale project lookup failed"));
        await oldProject.promise.catch(() => undefined);
      } else {
        if (stage === "equations") {
          if (outcome === "success") oldEquations.resolve(equationFixture("project-a-version", 41));
          else oldEquations.reject(new Error("Stale equations lookup failed"));
        } else {
          if (outcome === "success") oldVariables.resolve(variablesA);
          else oldVariables.reject(new Error("Stale variables lookup failed"));
        }
        await Promise.allSettled([oldEquations.promise, oldVariables.promise]);
      }
    });

    expect(screen.getByRole("heading", { name: "Project B" })).toBeInTheDocument();
    expect(screen.getByText(/Project project-b · Version 1: Project B draft/)).toBeInTheDocument();
    expect(screen.getByText("R ≈ 2")).toBeInTheDocument();
    expect(screen.getByText("Project B finding")).toBeInTheDocument();
    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PASS");
    expect(screen.getByText("AST preview · not a validation result")).toBeInTheDocument();
    expect(screen.queryByText("Obsolete declaration")).not.toBeInTheDocument();
    expect(screen.queryByText("R ≈ 41")).not.toBeInTheDocument();
    expect(screen.queryByText("Project A")).not.toBeInTheDocument();
    expect(screen.queryByText("Local equation draft")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(validateEquationAst).toHaveBeenCalledTimes(1);
    expect(validateEquationAst).toHaveBeenCalledWith({ expression_ast: { node_type: "constant", value: 2 }, variables: [] });
    if (stage === "project") expect(fetchVersionEquations).not.toHaveBeenCalledWith("project-a-version");
  });

  it.each(["success", "rejection"])("ignores a discarded StrictMode mount's late project %s", async (outcome) => {
    const discarded = deferred<ResearchProjectModel>();
    (fetchProjectBySlug as jest.Mock).mockReturnValueOnce(discarded.promise);

    render(<React.StrictMode><EquationEditorPage params={Promise.resolve({ slug: "test-project" })} /></React.StrictMode>);
    await screen.findByText("R ≈ 1");
    expect(fetchProjectBySlug).toHaveBeenCalledTimes(2);

    await act(async () => {
      if (outcome === "success") discarded.resolve(projectFixture("discarded", "Discarded mount"));
      else discarded.reject(new Error("Discarded mount error"));
      await discarded.promise.catch(() => undefined);
    });

    expect(screen.getByRole("heading", { name: "Test project" })).toBeInTheDocument();
    expect(screen.getByText("R ≈ 1")).toBeInTheDocument();
    expect(screen.queryByText("Discarded mount")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(fetchVersionEquations).toHaveBeenCalledTimes(1);
    expect(validateEquationAst).not.toHaveBeenCalled();
  });
});
