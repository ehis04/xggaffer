import { AppError } from "../../common/AppError";

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const DEFAULT_REQUEST_TIMEOUT_MS = 15000;

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
}

const isFormDataBody = (body: unknown): body is FormData =>
  typeof FormData !== 'undefined' && body instanceof FormData;

function getCsrfToken(): string | null {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return decodeURIComponent(value);
    }
  }
  return null;
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/users/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(getCsrfToken() && { 'X-CSRFToken': getCsrfToken()! }),
        },
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {},
    isRetry = false
  ): Promise<T> {
    const { params, ...fetchOptions } = options;

    let url = `${this.baseUrl}${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      url += `?${searchParams.toString()}`;
    }

    const headers: Record<string, string> = {
      ...(fetchOptions.headers as Record<string, string>),
    };

    if (!isFormDataBody(fetchOptions.body) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const method = (fetchOptions.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }
    }

    const config: RequestInit = {
      ...fetchOptions,
      credentials: 'include',
      headers,
    };

    const timeoutController = new AbortController();
    const externalSignal = fetchOptions.signal;
    const timeoutId = window.setTimeout(() => {
      timeoutController.abort();
    }, DEFAULT_REQUEST_TIMEOUT_MS);

    const signal = externalSignal
      ? AbortSignal.any([externalSignal, timeoutController.signal])
      : timeoutController.signal;

    const response = await fetch(url, {
      ...config,
      signal,
    }).finally(() => {
      window.clearTimeout(timeoutId);
    });

    if (response.status === 401 && !isRetry) {
      if (!endpoint.includes('/auth/refresh')) {
        const refreshed = await attemptTokenRefresh();
        if (refreshed) {
          return this.request<T>(endpoint, options, true);
        }
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw AppError.fromResponse(response.status, error);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  async get<T>(
    endpoint: string,
    params?: Record<string, string | number | boolean>
  ): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const body = isFormDataBody(data)
      ? data
      : data
        ? JSON.stringify(data)
        : undefined;

    return this.request<T>(endpoint, {
      method: 'POST',
      body,
    });
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    const body = isFormDataBody(data) ? data : JSON.stringify(data);

    return this.request<T>(endpoint, {
      method: 'PUT',
      body,
    });
  }

  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    const body = isFormDataBody(data) ? data : JSON.stringify(data);

    return this.request<T>(endpoint, {
      method: 'PATCH',
      body,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
export default apiClient;
