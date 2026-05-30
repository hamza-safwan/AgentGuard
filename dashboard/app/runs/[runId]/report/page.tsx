import { getRun } from "@/lib/api";

export default async function ReportPage({ params }: { params: { runId: string } }) {
  const run = await getRun(params.runId);
  if (!run) return <div className="card">Report not found.</div>;

  return (
    <>
      <div className="page-title"><h1>Reliability Report</h1></div>
      <section className="card">
        <h2>{run.agent_name} {run.agent_version}</h2>
        <p className="muted">Run {run.run_id} / {run.suite}</p>
        <div className="grid cards">
          <div><div className="label">Overall</div><div className="value">{Math.round(run.overall_score)}</div></div>
          <div><div className="label">Deployment</div><div className="value" style={{ fontSize: 18 }}>{run.deployment_recommendation}</div></div>
        </div>
      </section>
    </>
  );
}
