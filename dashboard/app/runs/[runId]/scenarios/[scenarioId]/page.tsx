import Link from "next/link";
import { getRun } from "@/lib/api";

export default async function ScenarioDetailPage({ params }: { params: { runId: string; scenarioId: string } }) {
  const run = await getRun(params.runId);
  const result = run?.results?.find((item) => item.scenario_id === params.scenarioId);
  if (!result) return <div className="card">Scenario result not found.</div>;

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{result.scenario_id}</h1>
          <p className="muted">{result.status} / score {Math.round(result.overall_score * 100)}</p>
        </div>
        {result.trace_id && <Link className="badge warn" href={`/traces/${result.trace_id}`}>View Trace</Link>}
      </div>
      <section className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}>
        <div className="card">
          <h2>Final Output</h2>
          <p>{result.final_output}</p>
        </div>
        <div className="card">
          <h2>Raw Result</h2>
          <pre>{JSON.stringify(result.raw, null, 2)}</pre>
        </div>
      </section>
      <section className="grid cards" style={{ marginTop: 24 }}>
        {result.evaluations.map((evaluation) => (
          <div className="card" key={evaluation.metric_name}>
            <span className={`badge ${evaluation.passed ? "pass" : "fail"}`}>{evaluation.passed ? "Pass" : "Fail"}</span>
            <h3>{evaluation.metric_name}</h3>
            <div className="value">{Math.round(evaluation.score * 100)}</div>
            <p className="muted">{evaluation.reason}</p>
          </div>
        ))}
      </section>
    </>
  );
}
