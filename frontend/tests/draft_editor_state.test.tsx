import { act, renderHook, waitFor } from "@testing-library/react";
import { useEquationCanvas } from "@/hooks/useEquationCanvas";
import { canvasDraft, draftContentKey, useDraftEditor } from "@/hooks/useDraftEditor";
import { useDraftRecovery } from "@/hooks/useDraftRecovery";
import { createVersion, fetchProjectBySlug, fetchVersionDraft, saveVersionDraft } from "@/lib/api";
import type { DraftSnapshot } from "@/types/contracts";

jest.mock("@/lib/api", () => ({ createVersion: jest.fn(), fetchProjectBySlug: jest.fn(),
  fetchVersionDraft: jest.fn(), saveVersionDraft: jest.fn() }));

const version = { id: "v1", project_id: "p", title: "Draft", version_number: 1, revision: 0,
  publication_status: "draft", is_frozen: false, created_at: "2026-11-17" };
const empty: DraftSnapshot = { version, equations: [], variables: [], units: [] };
function response(value: number, revision: number): DraftSnapshot {
  return { ...empty, version: { ...version, revision }, equations: [{ id: "eq1", version_id: "v1", label: "Primary equation",
    latex_raw: String(value), canonical_ast_json: { node_type: "constant", value }, created_at: "2026-11-17" }] };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  return { promise: new Promise<T>((a, b) => { resolve = a; reject = b; }), get resolve() { return resolve; }, get reject() { return reject; } };
}
function useEditor(slug = "p") {
  const canvas = useEquationCanvas();
  const draft = useDraftEditor(slug, canvas.replaceCanvas, canvas.getSaveSnapshot, canvas.cancelPendingValidation);
  return { canvas, draft };
}

beforeEach(() => {
  jest.resetAllMocks(); window.history.replaceState(null, "", "/projects/p/editor");
  (fetchProjectBySlug as jest.Mock).mockResolvedValue({ id: "p", slug: "p", can_edit: true, versions: [version] });
  (fetchVersionDraft as jest.Mock).mockResolvedValue(empty);
});

it("preserves newer edits when a save returns, then saves against the acknowledged revision", async () => {
  const delayed = deferred<DraftSnapshot>();
  (saveVersionDraft as jest.Mock).mockReturnValueOnce(delayed.promise).mockResolvedValueOnce(response(2, 6));
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  act(() => result.current.canvas.replaceCanvas({ node_type: "constant", value: 1 }, []));
  let pending!: Promise<void>;
  act(() => { pending = result.current.draft.save(); });
  act(() => result.current.canvas.replaceCanvas({ node_type: "constant", value: 2 }, []));
  await act(async () => { delayed.resolve(response(1, 3)); await pending; });
  expect(result.current.canvas.currentAst).toEqual({ node_type: "constant", value: 2 });
  expect(result.current.draft.snapshot?.version.revision).toBe(3);
  expect(draftContentKey(canvasDraft(result.current.draft.snapshot, result.current.canvas.getSaveSnapshot()))).not.toBe(result.current.draft.savedKey);
  await act(async () => { await result.current.draft.save(); });
  expect(saveVersionDraft).toHaveBeenLastCalledWith("v1", 3, expect.objectContaining({ equations: [expect.objectContaining({ id: "eq1", canonical_ast_json: { node_type: "constant", value: 2 } })] }));
});

it.each(["conflict", "offline"])("keeps local input and revision on %s", async (kind) => {
  (saveVersionDraft as jest.Mock).mockRejectedValue(new Error(kind));
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  act(() => result.current.canvas.replaceCanvas({ node_type: "constant", value: 7 }, []));
  await act(async () => { await result.current.draft.save(); });
  expect(result.current.draft.saveError).toBe(kind);
  expect(result.current.canvas.currentAst?.value).toBe(7);
  expect(result.current.draft.snapshot?.version.revision).toBe(0);
});

it("serializes double save clicks and rejects malformed local canvas before HTTP", async () => {
  const pending = deferred<DraftSnapshot>();
  (saveVersionDraft as jest.Mock).mockReturnValue(pending.promise);
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  act(() => result.current.canvas.handleAddNode("binary_op"));
  await act(async () => { await result.current.draft.save(); });
  expect(saveVersionDraft).not.toHaveBeenCalled();
  act(() => result.current.canvas.replaceCanvas({ node_type: "constant", value: 1 }, []));
  let first!: Promise<void>;
  act(() => { first = result.current.draft.save(); void result.current.draft.save(); });
  expect(saveVersionDraft).toHaveBeenCalledTimes(1);
  await act(async () => { pending.resolve(response(1, 3)); await first; });
});

it("creates an empty version and reloads that exact ID rather than the latest version", async () => {
  const v2 = { ...version, id: "v2", version_number: 2 };
  (createVersion as jest.Mock).mockResolvedValue(v2);
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  (fetchProjectBySlug as jest.Mock).mockResolvedValue({ versions: [{ ...v2, id: "v3" }, v2, version] });
  (fetchVersionDraft as jest.Mock).mockResolvedValue({ ...empty, version: v2 });
  await act(async () => { await result.current.draft.create("Second"); });
  expect(fetchVersionDraft).toHaveBeenLastCalledWith("v2");
  expect(window.location.search).toBe("?version=v2");
});

it("retains secondary equations and custom units in a primary equation save", async () => {
  const richer = response(1, 0);
  richer.equations.push({ ...richer.equations[0], id: "eq2", canonical_ast_json: { node_type: "constant", value: 9 } });
  richer.units = [{ name: "custom_length", symbol: "clen", dimensionality: "[length]", scale_factor: 2 }];
  (fetchVersionDraft as jest.Mock).mockResolvedValue(richer);
  (saveVersionDraft as jest.Mock).mockResolvedValue(richer);
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  const node = result.current.canvas.nodes.find((n) => n.type === "constantNode")!;
  act(() => result.current.canvas.handleNodeDataChange(node.id, { value: 5 }));
  await act(async () => { await result.current.draft.save(); });
  expect(saveVersionDraft).toHaveBeenCalledWith("v1", 0, expect.objectContaining({
    units: richer.units, equations: [expect.objectContaining({ id: "eq1", canonical_ast_json: { node_type: "constant", value: 5 } }), expect.objectContaining({ id: "eq2", canonical_ast_json: { node_type: "constant", value: 9 } })],
  }));
});

it("preserves exact numeric strings and authored LaTeX in declaration-only saves", async () => {
  const original = response(1, 0);
  original.equations[0].canonical_ast_json = { node_type: "constant", value: "9007199254740993" };
  original.equations[0].latex_raw = "\\underbrace{9007199254740993}_{\\text{authored}}";
  (fetchVersionDraft as jest.Mock).mockResolvedValue(original);
  (saveVersionDraft as jest.Mock).mockResolvedValue(original);
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  expect(result.current.canvas.currentAst?.value).toBe("9007199254740993");
  act(() => result.current.canvas.handleVariablesChange([{ symbol: "x", name: "Declaration only", unit: "meter", domain: "real" }]));
  await act(async () => { await result.current.draft.save(); });
  expect(saveVersionDraft).toHaveBeenLastCalledWith("v1", 0, expect.objectContaining({
    equations: [expect.objectContaining({ canonical_ast_json: original.equations[0].canonical_ast_json, latex_raw: original.equations[0].latex_raw })],
  }));
});

it("does not overwrite a retained secondary equation after clearing and saving the primary", async () => {
  const richer = response(1, 0);
  const secondary = { ...richer.equations[0], id: "eq2", canonical_ast_json: { node_type: "constant", value: 9 } };
  richer.equations.push(secondary);
  (fetchVersionDraft as jest.Mock).mockResolvedValue(richer);
  (saveVersionDraft as jest.Mock).mockResolvedValueOnce({ ...richer, version: { ...version, revision: 3 }, equations: [secondary] })
    .mockResolvedValueOnce({ ...richer, version: { ...version, revision: 6 }, equations: [secondary, { ...secondary, id: "eq3", canonical_ast_json: { node_type: "constant", value: 5 } }] });
  const { result } = renderHook(() => useEditor());
  await waitFor(() => expect(result.current.draft.loading).toBe(false));
  act(() => result.current.canvas.replaceCanvas(null, []));
  await act(async () => { await result.current.draft.save(); });
  expect(result.current.draft.primaryEquationId).toBeNull();
  act(() => result.current.canvas.replaceCanvas({ node_type: "constant", value: 5 }, []));
  await act(async () => { await result.current.draft.save(); });
  const submitted = (saveVersionDraft as jest.Mock).mock.calls[1][2].equations;
  expect(submitted[0].id).toBeUndefined();
  expect(submitted[1]).toEqual(expect.objectContaining({ id: "eq2", canonical_ast_json: secondary.canonical_ast_json }));
  expect(result.current.draft.primaryEquationId).toBe("eq3");
});

it("recovers an earlier version after another version loads first, and honors explicit reload", async () => {
  sessionStorage.setItem("reality-science.access-token", "cross-version-recovery-fixture");
  const older = response(1, 0);
  const newer = { ...response(2, 0), version: { ...version, id: "v2", version_number: 2 } };
  (fetchProjectBySlug as jest.Mock).mockResolvedValue({ id: "p", can_edit: true, versions: [newer.version, version] });
  (fetchVersionDraft as jest.Mock).mockImplementation(async (id) => id === "v1" ? older : newer);
  function useRecoveringEditor() {
    const { canvas, draft } = useEditor();
    const dirty = !!draft.snapshot && draftContentKey(canvasDraft(draft.snapshot, canvas.getSaveSnapshot())) !== draft.savedKey;
    const message = useDraftRecovery("p", draft, dirty, true, canvas.getCanvasSnapshot, canvas.restoreCanvas);
    return { canvas, draft, message };
  }
  try {
    window.history.replaceState(null, "", "/projects/p/editor?version=v1");
    const first = renderHook(useRecoveringEditor);
    await waitFor(() => expect(first.result.current.draft.loading).toBe(false));
    act(() => first.result.current.canvas.replaceCanvas({ node_type: "constant", value: "17" }, []));
    first.unmount();
    window.history.replaceState(null, "", "/projects/p/editor");
    const next = renderHook(useRecoveringEditor);
    await waitFor(() => expect(next.result.current.draft.snapshot?.version.id).toBe("v2"));
    await act(async () => { await next.result.current.draft.load("v1"); });
    expect(next.result.current.canvas.currentAst?.value).toBe("17");
    expect(next.result.current.message).toMatch(/Recovered unsaved edits/);
    await act(async () => { await next.result.current.draft.load("v1"); });
    expect(next.result.current.canvas.currentAst?.value).toBe(1);
    next.unmount();
    const reloaded = renderHook(useRecoveringEditor);
    await waitFor(() => expect(reloaded.result.current.draft.loading).toBe(false));
    expect(reloaded.result.current.canvas.currentAst?.value).toBe(1);
    expect(reloaded.result.current.message).toBe("");
    reloaded.unmount();
  } finally { sessionStorage.removeItem("reality-science.access-token"); }
});
