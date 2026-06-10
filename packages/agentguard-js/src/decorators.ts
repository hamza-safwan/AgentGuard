/**
 * Function-style "decorators" that record a TraceStep per call into the
 * active trace. Sync and async callables both supported.
 */

import { recordStep } from "./context.js";
import type { TraceStep } from "./schema.js";

type StepKind = TraceStep["type"];
type AnyFn<TArgs extends unknown[], TReturn> = (...args: TArgs) => TReturn | Promise<TReturn>;
type MaybeFn<TArgs extends unknown[], TReturn> = AnyFn<TArgs, TReturn> | DecoratorOptions;

export type DecoratorOptions = {
  name?: string;
  captureInput?: boolean;
  captureOutput?: boolean;
  metadata?: Record<string, unknown>;
};

const DEFAULT_MAX_BYTES = 4096;

const scrubKeys: Set<string> = new Set([
  "password",
  "secret",
  "api_key",
  "apikey",
  "token",
  "authorization",
  "openai_api_key",
  "anthropic_api_key",
]);

export function scrub(...keys: string[]): void {
  for (const k of keys) scrubKeys.add(k.toLowerCase());
}

function maxBytes(): number {
  const env = typeof process !== "undefined" ? process.env?.AGENTGUARD_MAX_CAPTURE_BYTES : undefined;
  if (!env) return DEFAULT_MAX_BYTES;
  const n = Number.parseInt(env, 10);
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_MAX_BYTES;
}

function redactWalk(value: unknown, path: string, redactions: string[]): unknown {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      const childPath = path ? `${path}.${k}` : k;
      if (scrubKeys.has(k.toLowerCase())) {
        out[k] = "***";
        redactions.push(childPath);
      } else {
        out[k] = redactWalk(v, childPath, redactions);
      }
    }
    return out;
  }
  if (Array.isArray(value)) {
    return value.map((v, i) => redactWalk(v, `${path}[${i}]`, redactions));
  }
  return value;
}

function jsonable(value: unknown): unknown {
  let serialized: string;
  try {
    serialized = JSON.stringify(value, (_k, v) => (typeof v === "bigint" ? v.toString() : v));
  } catch {
    return String(value);
  }
  if (serialized === undefined) return null;
  const cap = maxBytes();
  if (serialized.length > cap) {
    return serialized.slice(0, cap) + `...<truncated ${serialized.length - cap} bytes>`;
  }
  try {
    return JSON.parse(serialized);
  } catch {
    return serialized;
  }
}

function captureArgs(args: unknown[], paramNames: string[] | null): {
  captured: unknown;
  redactions: string[];
} {
  const redactions: string[] = [];
  let captured: unknown;
  if (paramNames && paramNames.length === args.length) {
    captured = Object.fromEntries(paramNames.map((n, i) => [n, args[i]]));
  } else {
    captured = { args };
  }
  const redacted = redactWalk(captured, "", redactions);
  return { captured: jsonable(redacted), redactions };
}

function inferParamNames(fn: Function): string[] | null {
  // Best-effort: parse the function source; not always available in minified
  // environments, in which case we fall back to the args-array shape.
  const src = fn.toString();
  const match =
    /function[^(]*\(([^)]*)\)/.exec(src) ??
    /^\s*(?:async\s*)?\(([^)]*)\)\s*=>/.exec(src) ??
    /^\s*(?:async\s*)?([^()\s,]+)\s*=>/.exec(src);
  if (!match || !match[1]) return null;
  return match[1]
    .split(",")
    .map((s) => s.trim().split(/[ :=]/)[0]!)
    .filter(Boolean);
}

function build<TArgs extends unknown[], TReturn>(
  kind: StepKind,
  fn: AnyFn<TArgs, TReturn>,
  options: DecoratorOptions = {},
): AnyFn<TArgs, TReturn> {
  const label = options.name ?? fn.name ?? "anonymous";
  const captureInput = options.captureInput ?? true;
  const captureOutput = options.captureOutput ?? true;
  const metadata = options.metadata ?? {};
  const paramNames = inferParamNames(fn as unknown as Function);

  return ((...args: TArgs): TReturn | Promise<TReturn> => {
    const start = Date.now();
    const captured = captureInput ? captureArgs(args as unknown[], paramNames) : { captured: null, redactions: [] };

    const finishOk = (output: unknown): void => {
      let outputValue: unknown = null;
      const outputRedactions: string[] = [];
      if (captureOutput) {
        const redacted = redactWalk(output, "", outputRedactions);
        outputValue = jsonable(redacted);
      }
      recordStep({
        type: kind,
        name: label,
        input: (captureInput ? captured.captured : undefined) as TraceStep["input"],
        output: outputValue as TraceStep["output"],
        metadata,
        latency_ms: Date.now() - start,
        source: "sdk",
        redactions: [...captured.redactions, ...outputRedactions],
      });
    };

    const finishErr = (err: unknown): void => {
      recordStep({
        type: "error",
        name: label,
        input: (captureInput ? captured.captured : undefined) as TraceStep["input"],
        output: {
          error_type: (err as Error)?.name ?? "Error",
          message: (err as Error)?.message ?? String(err),
        } as TraceStep["output"],
        metadata,
        latency_ms: Date.now() - start,
        source: "sdk",
        redactions: captured.redactions,
      });
    };

    let result: TReturn | Promise<TReturn>;
    try {
      result = fn(...args);
    } catch (err) {
      finishErr(err);
      throw err;
    }

    if (result && typeof (result as Promise<TReturn>).then === "function") {
      return (result as Promise<TReturn>).then(
        (value) => {
          finishOk(value);
          return value;
        },
        (err: unknown) => {
          finishErr(err);
          throw err;
        },
      );
    }

    finishOk(result);
    return result;
  }) as AnyFn<TArgs, TReturn>;
}

export function tool<TArgs extends unknown[], TReturn>(
  fnOrName: AnyFn<TArgs, TReturn> | string,
  options?: MaybeFn<TArgs, TReturn>,
): AnyFn<TArgs, TReturn> | ((fn: AnyFn<TArgs, TReturn>) => AnyFn<TArgs, TReturn>) {
  if (typeof fnOrName === "function") {
    return build("tool_call", fnOrName, options as DecoratorOptions | undefined);
  }
  if (typeof options === "function") {
    return build("tool_call", options, { name: fnOrName });
  }
  return (fn: AnyFn<TArgs, TReturn>) => build("tool_call", fn, { ...options, name: fnOrName });
}

export function llmCall<TArgs extends unknown[], TReturn>(
  fnOrName: AnyFn<TArgs, TReturn> | string,
  options?: MaybeFn<TArgs, TReturn>,
): AnyFn<TArgs, TReturn> | ((fn: AnyFn<TArgs, TReturn>) => AnyFn<TArgs, TReturn>) {
  if (typeof fnOrName === "function") {
    return build("llm_call", fnOrName, options as DecoratorOptions | undefined);
  }
  if (typeof options === "function") {
    return build("llm_call", options, { name: fnOrName });
  }
  return (fn: AnyFn<TArgs, TReturn>) => build("llm_call", fn, { ...options, name: fnOrName });
}

export function retrieval<TArgs extends unknown[], TReturn>(
  fnOrName: AnyFn<TArgs, TReturn> | string,
  options?: MaybeFn<TArgs, TReturn>,
): AnyFn<TArgs, TReturn> | ((fn: AnyFn<TArgs, TReturn>) => AnyFn<TArgs, TReturn>) {
  if (typeof fnOrName === "function") {
    return build("retrieval", fnOrName, options as DecoratorOptions | undefined);
  }
  if (typeof options === "function") {
    return build("retrieval", options, { name: fnOrName });
  }
  return (fn: AnyFn<TArgs, TReturn>) => build("retrieval", fn, { ...options, name: fnOrName });
}

export function guardrail<TArgs extends unknown[], TReturn>(
  fnOrName: AnyFn<TArgs, TReturn> | string,
  options?: MaybeFn<TArgs, TReturn>,
): AnyFn<TArgs, TReturn> | ((fn: AnyFn<TArgs, TReturn>) => AnyFn<TArgs, TReturn>) {
  if (typeof fnOrName === "function") {
    return build("guardrail", fnOrName, options as DecoratorOptions | undefined);
  }
  if (typeof options === "function") {
    return build("guardrail", options, { name: fnOrName });
  }
  return (fn: AnyFn<TArgs, TReturn>) => build("guardrail", fn, { ...options, name: fnOrName });
}

export function traceable<TArgs extends unknown[], TReturn>(
  fnOrName: AnyFn<TArgs, TReturn> | string,
  options?: MaybeFn<TArgs, TReturn>,
): AnyFn<TArgs, TReturn> | ((fn: AnyFn<TArgs, TReturn>) => AnyFn<TArgs, TReturn>) {
  return tool<TArgs, TReturn>(fnOrName, options);
}
