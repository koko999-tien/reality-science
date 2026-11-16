import {
  ExprNode,
  VariableSpec,
  UnitSpec,
  FindingResult,
  ValidationRunModel,
  EquationModel,
  VariableModel,
  ClaimModel,
  ResearchProjectModel,
} from "@/types/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const ACCESS_TOKEN_KEY = "reality-science.access-token";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

function authenticatedHeaders(headers: HeadersInit = {}): Headers {
  const result = new Headers(headers);
  const token = getAccessToken();
  if (token) result.set("Authorization", `Bearer ${token}`);
  return result;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE_URL}/iam/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (typeof errorData?.detail === "string") detail = errorData.detail;
    } catch {
      // Keep the HTTP status when the body is not JSON.
    }
    throw new Error(`Login failed: ${detail}`);
  }
  const data: unknown = await res.json();
  const response = data as { access_token?: unknown; token_type?: unknown } | null;
  if (
    response === null ||
    typeof response !== "object" ||
    Array.isArray(response) ||
    typeof response.access_token !== "string" ||
    response.access_token.trim().length === 0 ||
    typeof response.token_type !== "string" ||
    response.token_type.toLowerCase() !== "bearer"
  ) {
    throw new Error("Login failed: API returned an invalid bearer token response.");
  }
  const loginResponse: LoginResponse = {
    access_token: response.access_token,
    token_type: response.token_type,
  };
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, loginResponse.access_token);
  }
  return loginResponse;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new Error(`API health check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function validateEquationAst(payload: {
  expression_ast: ExprNode;
  variables: VariableSpec[];
  units?: UnitSpec[];
  version_id?: string;
}): Promise<FindingResult> {
  const res = await fetch(`${API_BASE_URL}/validation/verify`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (typeof errorData?.detail === "string") detail = errorData.detail;
      else if (typeof errorData?.message === "string") detail = errorData.message;
    } catch {
      // Keep the HTTP status as the actionable error when the body is not JSON.
    }
    throw new Error(`Validation API request failed: ${detail}`);
  }

  return res.json();
}

export async function validateVersion(versionId: string): Promise<ValidationRunModel> {
  const res = await fetch(`${API_BASE_URL}/versions/${versionId}/validate`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Validation failed (${res.status}): ${errorText}`);
  }
  return await res.json();
}

export async function fetchVersionRuns(versionId: string): Promise<ValidationRunModel[]> {
  const res = await fetch(`${API_BASE_URL}/versions/${versionId}/validation-runs`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to fetch validation runs: ${res.status}`);
  }
  return await res.json();
}

export async function fetchVersionEquations(versionId: string): Promise<EquationModel[]> {
  const res = await fetch(`${API_BASE_URL}/versions/${versionId}/equations`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to fetch equations: ${res.status}`);
  }
  return await res.json();
}

export async function fetchVersionVariables(versionId: string): Promise<VariableModel[]> {
  const res = await fetch(`${API_BASE_URL}/versions/${versionId}/variables`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to fetch variables: ${res.status}`);
  }
  return await res.json();
}

export async function fetchVersionClaims(versionId: string): Promise<ClaimModel[]> {
  const res = await fetch(`${API_BASE_URL}/versions/${versionId}/claims`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to fetch claims: ${res.status}`);
  }
  return await res.json();
}

export async function fetchProjectBySlug(slug: string): Promise<ResearchProjectModel> {
  const res = await fetch(`${API_BASE_URL}/projects/${encodeURIComponent(slug)}`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const errorData = await res.json();
      if (typeof errorData?.detail === "string") detail = errorData.detail;
    } catch {
      // Keep the status as the actionable error when the body is not JSON.
    }
    throw new Error(`Failed to fetch project: ${detail}`);
  }
  return await res.json();
}

export function getExportVersionZipUrl(versionId: string): string {
  return `${API_BASE_URL}/versions/${versionId}/export-zip`;
}

export async function exportVersionZip(versionId: string): Promise<Blob> {
  const response = await fetch(getExportVersionZipUrl(versionId), {
    method: "POST",
    headers: authenticatedHeaders(),
  });
  if (!response.ok) throw new Error(`Export failed (${response.status}).`);
  return response.blob();
}
