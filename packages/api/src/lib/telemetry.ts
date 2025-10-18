import { diag, DiagConsoleLogger, DiagLogLevel, trace, SpanStatusCode } from '@opentelemetry/api';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-proto';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-proto';
import { Resource } from '@opentelemetry/resources';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

let sdk: NodeSDK | null = null;

export function initTelemetry(): void {
  if (sdk) {
    return;
  }

  diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.ERROR);

  const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
  const headers = process.env.OTEL_EXPORTER_OTLP_HEADERS;

  const traceExporter = endpoint
    ? new OTLPTraceExporter({ url: `${endpoint}/v1/traces`, headers: parseHeaders(headers) })
    : undefined;

  const metricExporter = endpoint
    ? new OTLPMetricExporter({ url: `${endpoint}/v1/metrics`, headers: parseHeaders(headers) })
    : undefined;

  sdk = new NodeSDK({
    resource: new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: 'edison-api',
      [SemanticResourceAttributes.SERVICE_VERSION]: process.env.npm_package_version ?? 'dev',
      [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV ?? 'development',
    }),
    traceExporter,
    metricReader: metricExporter
      ? new PeriodicExportingMetricReader({ exporter: metricExporter, exportIntervalMillis: 15000 })
      : undefined,
    instrumentations: [],
  });

  void sdk.start().catch((error) => {
    diag.error('Failed to start telemetry SDK', error);
  });
}

export async function shutdownTelemetry(): Promise<void> {
  if (!sdk) {
    return;
  }

  await sdk.shutdown().catch((error) => {
    diag.error('Failed to shutdown telemetry SDK', error);
  });
  sdk = null;
}

export function withActiveSpan<T>(name: string, fn: () => Promise<T> | T): Promise<T> {
  const tracer = trace.getTracer('edison');
  return tracer.startActiveSpan(name, async (span) => {
    try {
      const result = await fn();
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      if (error instanceof Error) {
        span.recordException(error);
        span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
      }
      throw error;
    } finally {
      span.end();
    }
  });
}

function parseHeaders(raw: string | undefined): Record<string, string> | undefined {
  if (!raw) {
    return undefined;
  }

  return raw.split(',').reduce<Record<string, string>>((acc, pair) => {
    const [key, value] = pair.split('=');
    if (key && value) {
      acc[key.trim()] = value.trim();
    }
    return acc;
  }, {});
}
