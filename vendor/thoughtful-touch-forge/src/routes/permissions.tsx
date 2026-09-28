import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { fetchHealth, type HealthData } from "../lib/live";

function PermissionsView() {
  const [perms, setPerms] = useState<{ id: string; title: string; level: string | number; scope: string; status: string; last: string; reason: string }[] | null>(null);
  useEffect(() => {
    fetch("/api/permissions" + window.location.search)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setPerms(d?.permissions ?? []))
      .catch(() => setPerms([]));
  }, []);
  return (
    <div className="page-stage animate-page-in">
      <header className="page-heading"><div><p className="eyebrow">Live · this machine</p><h1>Permissions</h1><p className="page-description">47 only acts within the permissions you grant. Sensitive actions require your confirmation.</p></div></header>
      <div className="module-list" style={{ marginTop: 20 }}>
        {(perms ?? []).map((p) => (
          <article className="module-row" key={p.id}>
            <div className="module-marker">●</div>
            <div className="module-copy"><h2>{p.title} <small style={{ color: "var(--muted-foreground)" }}>· level {p.level}</small></h2><p>Scope: {p.scope}</p><p>Status: {p.status} · Last: {p.last}</p><p>{p.reason}</p></div>
          </article>
        ))}
        {perms !== null && perms.length === 0 && <p className="kv">Backend unreachable — start 47 first.</p>}
      </div>
    </div>
  );
}

export const Route = createFileRoute("/permissions")({
  head: () => ({ meta: [{ title: "Permissions — 47" }] }),
  component: PermissionsView,
});
