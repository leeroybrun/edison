export type AppErrorOptions = {
  code: string;
  status: number;
  details?: Record<string, unknown>;
  cause?: unknown;
};

export class AppError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(message: string, options: AppErrorOptions) {
    super(message);
    this.name = options.code;
    this.code = options.code;
    this.status = options.status;
    this.details = options.details;
    if (options.cause) {
      this.cause = options.cause as Error;
    }
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, { code: 'VALIDATION_ERROR', status: 400, details });
  }
}

export class NotFoundError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, { code: 'NOT_FOUND', status: 404, details });
  }
}

export class ConflictError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, { code: 'CONFLICT', status: 409, details });
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, { code: 'UNAUTHORIZED', status: 401, details });
  }
}

export class RateLimitError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, { code: 'RATE_LIMITED', status: 429, details });
  }
}

export class ExternalServiceError extends AppError {
  constructor(message: string, details?: Record<string, unknown>, cause?: unknown) {
    super(message, { code: 'EXTERNAL_SERVICE', status: 503, details, cause });
  }
}

export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}
