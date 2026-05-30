import Link from "next/link";
import { listRuns } from "@/lib/api";

export default async function RunsPage() {
  const runs = await listRuns();

  return (
    <>
      <div className="page-title"><h1>Runs</h1></div>
      <section className="card">
        <table className="table">
          <thead><tr><th>Run</th><th>Version</th><th>Suite</th><th>Overall</th><th>Security</th><th>Recommendation</th></tr></thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id}>
                <td><Link href={`/runs/${run.run_id}`}>{run.run_id}</Link></td>
                <td>{run.agent_version}</td>
                <td>{run.suite}</td>
                <td>{Math.round(run.overall_score)}</td>
                <td>{Math.round(run.security_score)}</td>
                <td><span className={`badge ${run.deployment_recommendation.includes("deploy") ? "pass" : "fail"}`}>{run.deployment_recommendation}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
