import Link from "next/link";
import { listRuns } from "@/lib/api";

function pct(value: number) {
  return `${Math.round(value)}/100`;
}

export default async function HomePage() {
  const runs = await listRuns();
  const latest = runs[0];

  return (
    <>
      <div className="page-title">
        <div>
          <h1>Project Health</h1>
          <p className="muted">Postgres-backed evaluation history for agent reliability and security.</p>
        </div>
      </div>

      <section className="grid cards">
        <div className="card"><div className="label">Overall Score</div><div className="value">{latest ? pct(latest.overall_score) : "No runs"}</div></div>
        <div className="card"><div className="label">Pass Rate</div><div className="value">{latest ? `${latest.passed_scenarios}/${latest.total_scenarios}` : "0/0"}</div></div>
        <div className="card"><div className="label">Security Score</div><div className="value">{latest ? pct(latest.security_score) : "0/100"}</div></div>
        <div className="card"><div className="label">Tool Correctness</div><div className="value">{latest ? pct(latest.tool_score) : "0/100"}</div></div>
        <div className="card"><div className="label">Avg Cost</div><div className="value">${latest ? latest.avg_cost_usd.toFixed(4) : "0.0000"}</div></div>
        <div className="card"><div className="label">p95 Latency</div><div className="value">{latest?.p95_latency_ms ? `${(latest.p95_latency_ms / 1000).toFixed(1)}s` : "n/a"}</div></div>
      </section>

      <section className="card" style={{ marginTop: 24 }}>
        <h2>Recent Runs</h2>
        <table className="table">
          <thead><tr><th>Run</th><th>Agent</th><th>Suite</th><th>Score</th><th>Status</th><th>Started</th></tr></thead>
          <tbody>
            {runs.slice(0, 8).map((run) => (
              <tr key={run.run_id}>
                <td><Link href={`/runs/${run.run_id}`}>{run.run_id}</Link></td>
                <td>{run.agent_name} <span className="muted">{run.agent_version}</span></td>
                <td>{run.suite}</td>
                <td>{Math.round(run.overall_score)}</td>
                <td><span className={`badge ${run.failed_scenarios ? "fail" : "pass"}`}>{run.failed_scenarios ? "Fail" : "Pass"}</span></td>
                <td>{run.started_at ? new Date(run.started_at).toLocaleString() : "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
