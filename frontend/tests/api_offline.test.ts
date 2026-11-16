import { validateEquationAst } from "@/lib/api";

describe("validation API provenance", () => {
  afterEach(() => jest.restoreAllMocks());

  it("rejects network failures instead of manufacturing a PASS result", async () => {
    jest.spyOn(global, "fetch").mockRejectedValue(new Error("offline"));

    await expect(validateEquationAst({
      expression_ast: { node_type: "constant", value: 2 },
      variables: [],
    })).rejects.toThrow("offline");
  });

  it("surfaces HTTP failure details instead of presenting them as scientific findings", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 503,
      statusText: "Service Unavailable",
      json: async () => ({ detail: "worker unavailable" }),
    } as Response);

    await expect(validateEquationAst({
      expression_ast: { node_type: "constant", value: 2 },
      variables: [],
    })).rejects.toThrow("worker unavailable");
  });
});
