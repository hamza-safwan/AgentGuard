import { getRun } from "@/lib/api";

export default async function SecurityPage({ params }: { params: { runId: string } }) {
  const run = await getRun(params.runId);
  const findings = run?.security_findings || [];

  return (
    <>
      <div className="page-title"><h1>Security Findings</h1></div>
      <section className="card">
        <div className="label">Security Score</div>
        <div className="value">{run ? Math.round(run.security_score) : 0}/100</div>
      </section>
      <section className="grid" style={{ marginTop: 24 }}>
        {findings.map((finding, index) => (
          <div className="card" key={`${finding.scenario_id}-${index}`}>
            <span className={`badge ${finding.severity === "critical" ? "fail" : "warn"}`}>{finding.severity}</span>
            <h3>{finding.scenario_id}</h3>
            <p>{finding.finding}</p>
          </div>
        ))}
        {!findings.length && <div className="card">No security findings recorded for this run.</div>}
      </section>
    </>
  );
}
