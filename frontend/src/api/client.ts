// Cliente HTTP mínimo. La URL base viene de VITE_API_URL (ver .env.example
// en la raíz del repositorio). Se falla explícitamente si no está definida
// en vez de asumir un valor productivo.

const API_BASE_URL = import.meta.env.VITE_API_URL as string | undefined;

function resolveBaseUrl(): string {
  if (import.meta.env.DEV) {
    return "";
  }

  return getApiBaseUrl();
}

export class ApiConfigurationError extends Error {}

export function getApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new ApiConfigurationError(
      "VITE_API_URL no está definida. Copiá .env.example a .env y configurá la URL del backend."
    );
  }
  return API_BASE_URL;
}

interface ApiRequestOptions {
  signal?: AbortSignal;
  headers?: HeadersInit;
  body?: BodyInit | null;
  method?: string;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const base = resolveBaseUrl();
  const response = await fetch(`${base}${path}`, options);
  if (!response.ok) {
    let message = `Error ${response.status} al consultar ${path}`;
    try {
      const body = await response.json();
      if (body?.message) message = body.message;
    } catch {
      // el cuerpo no era JSON: se mantiene el mensaje genérico
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export async function apiGet<T>(path: string, signal?: AbortSignal, headers?: HeadersInit): Promise<T> {
  return apiRequest<T>(path, { signal, headers, method: "GET" });
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  options: Omit<ApiRequestOptions, "body" | "method"> = {}
): Promise<T> {
  return apiRequest<T>(path, {
    ...options,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    body: body === undefined ? null : JSON.stringify(body),
  });
}
