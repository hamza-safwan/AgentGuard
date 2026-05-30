import { getTrace } from "@/lib/api";

function pretty(value: unknown) {
  if (value === undefined || value === null || value === "") return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export default async function TracePage({ params }: { params: { traceId: string } }) {
  const trace = await getTrace(params.traceId);
  if (!trace) return <div className="card">Trace not found.</div>;

  return (
    <>
      <div className="page-title">
        <div>
          <h1>Trace Viewer</h1>
          <p className="muted">{trace.trace_id} / {trace.scenario_id}</p>
        </div>
      </div>
      <section className="timeline">
        {trace.steps.map((step, index) => (
          <article className={`card step ${step.type}`} key={step.step_id}>
            <div className="label">Step {index + 1} / {step.type} / {step.latency_ms ?? "n/a"}ms</div>
            <h2>{step.name}</h2>
            {pretty(step.input) && <><h3>Input</h3><pre>{pretty(step.input)}</pre></>}
            {pretty(step.output) && <><h3>Output</h3><pre>{pretty(step.output)}</pre></>}
            {step.metadata && Object.keys(step.metadata).length > 0 && <><h3>Metadata</h3><pre>{pretty(step.metadata)}</pre></>}
          </article>
        ))}
        <article className="card step final_output">
          <div className="label">Final Output</div>
          <p>{trace.final_output || ""}</p>
        </article>
      </section>
    </>
  );
}
