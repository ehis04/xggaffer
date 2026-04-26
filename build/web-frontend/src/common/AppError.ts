export type AppErrorCode =
  | "NOT_FOUND"
  | "FORBIDDEN"
  | "UNAUTHENTICATED"
  | "SERVER_ERROR"
  | "NETWORK_ERROR"
  | "UNKNOWN";

function resolveCode(status: number): AppErrorCode {
  if (status === 401) return "UNAUTHENTICATED";
  if (status === 403) return "FORBIDDEN";
  if (status === 404) return "NOT_FOUND";
  if (status >= 500 && status <= 599) return "SERVER_ERROR";
  return "UNKNOWN";
}

function extractDetail(data: unknown): string | null {
  if (typeof data === "string") return data;
  if (typeof data === "object" && data !== null) {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    if (typeof obj.message === "string") return obj.message;
  }
  return null;
}

export class AppError extends Error {
  status: number;
  code: AppErrorCode;
  detail: string;

  constructor(status: number, code: AppErrorCode, detail: string) {
    super(detail);
    this.name = "AppError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }

  static fromResponse(status: number, data: unknown): AppError {
    const detail = extractDetail(data) ?? `HTTP ${status}`;
    const code = resolveCode(status);
    return new AppError(status, code, detail);
  }
}