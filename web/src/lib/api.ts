import type {
  DebugSuccess,
  ModeBSelection,
  ResolveError,
  ResolveSuccess,
  TownConfig,
  VersionResponse,
} from "../types";

const REQUEST_TIMEOUT_MS = 8_000;

export class ApiClientError extends Error {
  readonly status?: number;
  readonly suggestions: string[];
  readonly requiresNumber: boolean;

  constructor(message: string, options?: { status?: number; suggestions?: string[]; requiresNumber?: boolean }) {
    super(message);
    this.name = "ApiClientError";
    this.status = options?.status;
    this.suggestions = options?.suggestions ?? [];
    this.requiresNumber = options?.requiresNumber ?? false;
  }
}

function apiBase(town: TownConfig): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL?.trim();
  const fromTown = town.api.baseUrl?.trim();
  if (fromEnv) {
    return fromEnv;
  }
  if (fromTown) {
    return fromTown;
  }
  return "";
}

function apiUrl(town: TownConfig, path: string, params?: URLSearchParams): string {
  const base = apiBase(town);
  const url = new URL(path, base || window.location.origin);
  if (params) {
    url.search = params.toString();
  }
  return base ? url.toString() : `${url.pathname}${url.search}`;
}

async function parseJson(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return undefined;
  }
  return response.json();
}

export function normalizeSuggestions(input: unknown): string[] {
  if (!Array.isArray(input)) {
    return [];
  }
  const output: string[] = [];
  for (const item of input) {
    if (typeof item === "string") {
      output.push(item);
      continue;
    }
    if (item && typeof item === "object" && "street" in item) {
      const street = (item as { street?: unknown }).street;
      if (typeof street === "string") {
        output.push(street);
      }
    }
  }
  return output;
}

async function requestJson<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      signal: controller.signal,
    });

    const payload = await parseJson(response);

    if (!response.ok) {
      const err = payload as ResolveError | undefined;
      throw new ApiClientError(err?.error ?? `HTTP ${response.status}`, {
        status: response.status,
        suggestions: normalizeSuggestions(err?.suggestions),
        requiresNumber: Boolean(err?.requires_number),
      });
    }

    return payload as T;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiClientError("Request timed out. Please try again.");
    }
    throw new ApiClientError("The backend is temporarily unavailable. Please retry.");
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchVersion(town: TownConfig): Promise<VersionResponse> {
  return requestJson<VersionResponse>(apiUrl(town, town.api.versionPath));
}

export async function resolveRoute(
  town: TownConfig,
  input: { address?: string; street?: string; number?: string },
): Promise<ResolveSuccess> {
  const params = new URLSearchParams();

  if (input.address?.trim()) {
    params.set("address", input.address.trim());
  } else {
    if (input.street?.trim()) {
      params.set("street", input.street.trim());
    }
    if (input.number?.trim()) {
      params.set("number", input.number.trim());
    }
  }

  return requestJson<ResolveSuccess>(apiUrl(town, town.api.resolvePath, params));
}

export async function fetchDebugPreview(
  town: TownConfig,
  selection: ModeBSelection,
): Promise<DebugSuccess> {
  const params = new URLSearchParams();
  params.set("weekday", selection.weekday);
  params.set("color", selection.color);
  params.set("types", selection.types.join(","));
  if (selection.days && selection.days > 0) {
    params.set("days", String(selection.days));
  }

  return requestJson<DebugSuccess>(apiUrl(town, town.api.debugPath, params));
}
