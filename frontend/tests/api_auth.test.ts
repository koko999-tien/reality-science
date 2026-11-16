import { exportVersionZip, fetchProjectBySlug, login, validateVersion } from "@/lib/api";

describe("frontend authentication contract", () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(() => jest.restoreAllMocks());

  it.each(["bearer", "BeArEr"])("stores a valid token with token_type %s", async (tokenType) => {
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "jwt-value", token_type: tokenType }),
    } as Response);

    await login("researcher@example.test", "password");
    expect(sessionStorage.getItem("reality-science.access-token")).toBe("jwt-value");
  });

  it.each<[string, unknown]>([
    ["null body", null],
    ["non-object body", "jwt-value"],
    ["array body", ["jwt-value", "bearer"]],
    ["missing access_token", { token_type: "bearer" }],
    ["numeric access_token", { access_token: 123, token_type: "bearer" }],
    ["object access_token", { access_token: {}, token_type: "bearer" }],
    ["empty access_token", { access_token: "", token_type: "bearer" }],
    ["whitespace-only access_token", { access_token: " \t ", token_type: "bearer" }],
    ["missing token_type", { access_token: "jwt-value" }],
    ["numeric token_type", { access_token: "jwt-value", token_type: 123 }],
    ["null token_type", { access_token: "jwt-value", token_type: null }],
    ["non-bearer token_type", { access_token: "jwt-value", token_type: "basic" }],
  ])("rejects a successful login response with %s before storing a token", async (_, payload) => {
    const setItem = jest.spyOn(Storage.prototype, "setItem");
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => payload,
    } as Response);

    await expect(login("researcher@example.test", "password")).rejects.toThrow(
      "Login failed: API returned an invalid bearer token response."
    );
    expect(setItem).not.toHaveBeenCalled();
    expect(sessionStorage.getItem("reality-science.access-token")).toBeNull();
  });

  it("adds Bearer auth to project, version, and export calls", async () => {
    sessionStorage.setItem("reality-science.access-token", "jwt-value");
    const fetchMock = jest.spyOn(global, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("export-zip")) return { ok: true, blob: async () => new Blob(["zip"]) } as Response;
      return { ok: true, json: async () => ({}) } as Response;
    });
    fetchMock.mockClear();

    await fetchProjectBySlug("project");
    await validateVersion("version");
    await exportVersionZip("version");

    for (const call of fetchMock.mock.calls) {
      const headers = call[1]?.headers as HeadersInit | undefined;
      const authorization = headers && typeof (headers as Headers).get === "function"
        ? (headers as Headers).get("Authorization")
        : Array.isArray(headers)
          ? headers.find(([name]) => name.toLowerCase() === "authorization")?.[1]
          : (headers as Record<string, string> | undefined)?.Authorization
            ?? (headers as Record<string, string> | undefined)?.authorization;
      expect(authorization).toBe("Bearer jwt-value");
    }
  });
});
