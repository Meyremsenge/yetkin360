/**
 * AC-6/AC-S4: Error classes for API communication.
 */

export class ApiError extends Error {
  status: number;
  code: string;
  requestId: string | null;
  fields?: Record<string, string>;

  constructor({
    status,
    code,
    message,
    requestId,
    fields,
  }: {
    status: number;
    code: string;
    message: string;
    requestId: string | null;
    fields?: Record<string, string>;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.fields = fields;
  }
}

export class NetworkError extends Error {
  kind: "network" | "timeout";

  constructor(kind: "network" | "timeout") {
    const message =
      kind === "timeout"
        ? "İstek zaman aşımına uğradı"
        : "Ağ hatası oluştu";
    super(message);
    this.name = "NetworkError";
    this.kind = kind;
  }
}

export class SessionExpiredError extends Error {
  constructor() {
    super("Oturumunuz sona erdi");
    this.name = "SessionExpiredError";
  }
}

export class InvalidResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidResponseError";
  }
}

export function parseApiError(
  status: number,
  body: unknown
): ApiError {
  if (
    typeof body === "object" &&
    body !== null &&
    !Array.isArray(body)
  ) {
    const obj = body as Record<string, unknown>;
    const code = typeof obj.code === "string" ? obj.code : undefined;
    const message = typeof obj.message === "string" ? obj.message : undefined;
    const requestId =
      typeof obj.request_id === "string" ? obj.request_id : null;
    const fields =
      typeof obj.fields === "object" && obj.fields !== null
        ? (obj.fields as Record<string, string>)
        : undefined;

    if (code && message) {
      return new ApiError({
        status,
        code,
        message,
        requestId,
        fields,
      });
    }

    if (code) {
      return new ApiError({
        status,
        code,
        message: "Bilinmeyen hata oluştu",
        requestId,
      });
    }
  }

  return new ApiError({
    status,
    code: "UNKNOWN_ERROR",
    message: "Bilinmeyen hata oluştu",
    requestId: null,
  });
}
