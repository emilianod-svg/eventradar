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

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const base = resolveBaseUrl();
  const response = await fetch(`${base}${path}`, { signal });
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
