import Link from "next/link";
import { getRun } from "@/lib/api";

export default async function RunDetailPage({ params }: { params: { runId: string } }) {
  const run = await getRun(params.runId);
  if (!run) return <div className="card">Run not found.</div>;

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{run.run_id}</h1>
          <p className="muted">{run.agent_name} / {run.agent_version} / {run.suite}</p>
        </div>
        <Link className="badge warn" href={`/runs/${run.run_id}/security`}>Security findings</Link>
      </div>

      <section className="grid cards">
        <div className="card"><div className="label">Overall</div><div className="value">{Math.round(run.overall_score)}</div></div>
        <div className="card"><div className="label">Security</div><div className="value">{Math.round(run.security_score)}</div></div>
        <div className="card"><div className="label">RAG</div><div className="value">{Math.round(run.rag_score)}</div></div>
        <div className="card"><div className="label">Tool</div><div className="value">{Math.round(run.tool_score)}</div></div>
      </section>

      <section className="card" style={{ marginTop: 24 }}>
        <h2>Scenario Results</h2>
        <table className="table">
          <thead><tr><th>Scenario</th><th>Status</th><th>Score</th><th>Failure</th><th>Trace</th></tr></thead>
          <tbody>
            {(run.results || []).map((result) => (
              <tr key={result.id}>
                <td><Link href={`/runs/${run.run_id}/scenarios/${result.scenario_id}`}>{result.scenario_id}</Link></td>
                <td><span className={`badge ${result.passed ? "pass" : "fail"}`}>{result.passed ? "Pass" : "Fail"}</span></td>
                <td>{Math.round(result.overall_score * 100)}</td>
                <td>{result.failure_summary || ""}</td>
                <td>{result.trace_id ? <Link href={`/traces/${result.trace_id}`}>Open trace</Link> : "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
