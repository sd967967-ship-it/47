// Live bridge to the 47 backend (same origin, token from page URL).
// Falls back to empty data when 47 is unreachable — never mock-fakes.
export function apiToken(): string {
  try {
    return new URLSearchParams(window.location.search).get("token") || "";
  } catch {
    return "";
  }
}

async function apiGet<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${path}?token=${encodeURIComponent(apiToken())}`);
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export interface LiveTask { id: number; title: string; due_at: number | null }

export async function fetchTasks(): Promise<LiveTask[]> {
  const d = await apiGet<{ tasks: LiveTask[] }>("/api/tasks");
  return d?.tasks ?? [];
}

export async function completeTask(id: number): Promise<boolean> {
  try {
    const r = await fetch(`/api/tasks/complete?token=${encodeURIComponent(apiToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    return r.ok;
  } catch {
    return false;
  }
}

export async function fetchFacts(): Promise<Record<string, string>> {
  const d = await apiGet<{ facts: Record<string, string> }>("/api/memory");
  return d?.facts ?? {};
}

export async function deleteFact(key: string): Promise<boolean> {
  try {
    const r = await fetch(`/api/memory/${encodeURIComponent(key)}?token=${encodeURIComponent(apiToken())}`, {
      method: "DELETE",
    });
    return r.ok;
  } catch {
    return false;
  }
}

export interface AuditEntry { ts?: number; event: string }

export async function fetchAudit(): Promise<AuditEntry[]> {
  const d = await apiGet<{ entries: AuditEntry[] }>("/api/audit");
  return d?.entries ?? [];
}

export async function sendChat(text: string): Promise<string> {
  const r = await fetch(`/api/chat?token=${encodeURIComponent(apiToken())}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!r.ok) throw new Error(`chat ${r.status}`);
  const d = (await r.json()) as { reply?: string };
  return d.reply ?? "(no reply)";
}

export interface LockStatus { configured: boolean; unlocked: boolean }

export async function lockStatus(): Promise<LockStatus> {
  const d = await apiGet<LockStatus>("/api/lock/status");
  return d ?? { configured: false, unlocked: true };
}

export async function setupPin(pin: string): Promise<{ ok: boolean; message?: string }> {
  try {
    const r = await fetch(`/api/lock/setup?token=${encodeURIComponent(apiToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    return (await r.json()) as { ok: boolean; message?: string };
  } catch {
    return { ok: false, message: "Backend unreachable." };
  }
}

export async function unlock(pin: string): Promise<{ ok: boolean; message?: string }> {
  try {
    const r = await fetch(`/api/unlock?token=${encodeURIComponent(apiToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    return (await r.json()) as { ok: boolean; message?: string };
  } catch {
    return { ok: false, message: "Backend unreachable." };
  }
}

export async function estop(action: "stop" | "resume"): Promise<boolean> {
  try {
    const r = await fetch(`/api/estop?token=${encodeURIComponent(apiToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    return r.ok;
  } catch {
    return false;
  }
}

export interface FocusState { id: number; label: string; minutes: number; ends_at: number; done: boolean }

export async function focusStatus(): Promise<FocusState[]> {
  const d = await apiGet<{ live: FocusState[] }>("/api/focus");
  return d?.live ?? [];
}

export async function focusStart(minutes: number): Promise<boolean> {
  try {
    const r = await fetch(`/api/focus?token=${encodeURIComponent(apiToken())}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ minutes }),
    });
    return r.ok;
  } catch {
    return false;
  }
}

export async function focusStop(): Promise<boolean> {
  try {
    const r = await fetch(`/api/focus?token=${encodeURIComponent(apiToken())}`, {
      method: "DELETE",
    });
    return r.ok;
  } catch {
    return false;
  }
}

export interface HealthData {
  agent: { brain: string; uptime_s: number; estop: { stopped: boolean }; pending_approvals: number; focus_live: number; lock: string };
  resources: { cpu: number | null; ram: number | null; disk: number | null; battery: number | null; tasks_open: number | null };
  security: { lock: string };
  issues: { level: string; text: string; fix: string }[];
}

export async function fetchHealth(): Promise<HealthData | null> {
  return apiGet<HealthData>("/api/health");
}

export interface PermissionEntry { id: string; title: string; level: string | number; scope: string; status: string; last: string; reason: string }

export async function fetchPermissions(): Promise<PermissionEntry[]> {
  const d = await apiGet<{ permissions: PermissionEntry[] }>("/api/permissions");
  return d?.permissions ?? [];
}
