import { listRuns } from "@/lib/api";

export default async function ComparePage() {
  const runs = await listRuns();
  const base = runs[1];
  const candidate = runs[0];

  return (
    <>
      <div className="page-title"><h1>Regression Comparison</h1></div>
      <section className="card">
        {!base || !candidate ? (
          <p className="muted">At least two saved runs are needed for comparison.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Metric</th><th>Base</th><th>Candidate</th><th>Delta</th></tr></thead>
            <tbody>
              {[
                ["Overall", base.overall_score, candidate.overall_score],
                ["Security", base.security_score, candidate.security_score],
                ["RAG", base.rag_score, candidate.rag_score],
                ["Tool", base.tool_score, candidate.tool_score]
              ].map(([name, b, c]) => {
                const delta = Number(c) - Number(b);
                return <tr key={String(name)}><td>{name}</td><td>{Math.round(Number(b))}</td><td>{Math.round(Number(c))}</td><td>{delta.toFixed(1)}</td></tr>;
              })}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
