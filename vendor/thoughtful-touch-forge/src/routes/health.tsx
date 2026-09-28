import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { fetchHealth, type HealthData } from "../lib/live";

function HealthView() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetchHealth().then((h) => (h ? setHealth(h) : setFailed(true))).catch(() => setFailed(true));
  }, []);
  if (failed) {
    return (
      <div className="page-stage animate-page-in">
        <header className="page-heading"><div><p className="eyebrow">Health</p><h1>Unavailable</h1><p className="page-description">Backend unreachable — start 47 first.</p></div></header>
      </div>
    );
  }
  if (!health) {
    return (
      <div className="page-stage animate-page-in">
        <header className="page-heading"><div><p className="eyebrow">Health</p><h1>Checking…</h1></div></header>
      </div>
    );
  }
  const rows: [string, string][] = [
    ["Brain", health.agent.brain],
    ["Uptime", `${Math.floor(health.agent.uptime_s / 60)} min`],
    ["Emergency stop", health.agent.estop.stopped ? "STOPPED" : "released"],
    ["Pending approvals", String(health.agent.pending_approvals)],
    ["Focus sessions live", String(health.agent.focus_live)],
    ["CPU / RAM / Disk", `${health.resources.cpu ?? "?"}% / ${health.resources.ram ?? "?"}% / ${health.resources.disk ?? "?"}%`],
    ["Battery", health.resources.battery === null || health.resources.battery === undefined ? "n/a" : `${health.resources.battery}%`],
    ["Lock", health.security.lock],
  ];
  return (
    <div className="page-stage animate-page-in">
      <header className="page-heading"><div><p className="eyebrow">Live · this machine</p><h1>Agent health</h1><p className="page-description">Status, resources, and anything needing attention.</p></div></header>
      <div className="module-list" style={{ marginTop: 20 }}>
        {rows.map(([k, v]) => (
          <article className="module-row" key={k}>
            <div className="module-marker">●</div>
            <div className="module-copy"><h2>{k}</h2><p>{v}</p></div>
          </article>
        ))}
      </div>
      <div className="page-heading" style={{ marginTop: 28 }}><div><p className="eyebrow">Issues</p><h1 style={{ fontSize: 20 }}>Needs attention</h1></div></div>
      {health.issues.length === 0 && <p className="kv">All clear.</p>}
      {health.issues.map((i, n) => (
        <article className="module-row" key={n}>
          <div className="module-marker">!</div>
          <div className="module-copy"><h2>{i.text}</h2><p>Fix: {i.fix}</p></div>
          <span className="status-pill">{i.level}</span>
        </article>
      ))}
    </div>
  );
}

export const Route = createFileRoute("/health")({
  head: () => ({ meta: [{ title: "Health — 47" }] }),
  component: HealthView,
});
