const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const defaultApiBase = 'http://127.0.0.1:8000';

const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
const configuredWsBase = import.meta.env.VITE_WS_BASE_URL?.trim();

export const API_BASE_URL = trimTrailingSlash(configuredApiBase || defaultApiBase);
export const WS_BASE_URL = trimTrailingSlash(
  configuredWsBase || API_BASE_URL.replace(/^http/i, 'ws'),
);

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

export function wsUrl(path: string): string {
  return `${WS_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}
