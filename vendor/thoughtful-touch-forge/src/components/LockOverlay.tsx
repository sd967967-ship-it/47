import { useEffect, useState } from "react";
import { lockStatus, setupPin, unlock } from "../lib/live";
import { Button } from "./Button";

// PIN gate for the whole app. Setup mode when no lock exists (the user
// picks the PIN here — it is never hardcoded, logged, or stored plain).
// Rate-limit messages come straight from the backend.
export function LockOverlay({ onUnlocked }: { onUnlocked: () => void }) {
  const [mode, setMode] = useState<"checking" | "setup" | "unlock">("checking");
  const [pin, setPin] = useState("");
  const [note, setNote] = useState("Checking lock state…");
  useEffect(() => {
    let live = true;
    lockStatus()
      .then((s) => {
        if (!live) return;
        if (!s.configured) {
          setMode("setup");
          setNote("First run: choose a 4–12 digit PIN to lock 47.");
        } else if (s.unlocked) {
          onUnlocked();
        } else {
          setMode("unlock");
          setNote("47 is locked. Enter your PIN.");
        }
      })
      .catch(() => {
        if (live) setNote("Backend unreachable — start 47, then reload this page.");
      });
    return () => { live = false; };
  }, []);
  const submit = async () => {
    if (!pin) {
      setNote("Enter your PIN first.");
      return;
    }
    setNote("Checking…");
    try {
      if (mode === "setup") {
        const r = await setupPin(pin);
        if (r.ok) {
          onUnlocked();
        } else {
          setNote(r.message || "That PIN won't work — use 4–12 digits.");
        }
        return;
      }
      const r = await unlock(pin);
      if (r.ok) {
        onUnlocked();
      } else {
        setNote(r.message || "Try again.");
      }
    } catch {
      setNote("Backend unreachable — is 47 running?");
    }
    setPin("");
  };
  if (mode === "checking") return null;
  return (
    <div className="dialog-layer" role="dialog" aria-modal="true" aria-label="Unlock 47">
      <div className="command-dialog">
        <div className="command-input"><span>47</span><strong>{mode === "setup" ? "Set a lock PIN" : "47 is locked"}</strong></div>
        <div className="command-content">
          <p className="command-label">{note}</p>
          <div style={{ display: "flex", gap: 8, padding: "4px 8px 10px" }}>
            <input
              type="password"
              inputMode="numeric"
              autoComplete="off"
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 12))}
              onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
              placeholder="PIN"
              aria-label="PIN"
              autoFocus
              style={{ flex: 1, background: "transparent", border: "1px solid var(--border)", borderRadius: 6, color: "var(--foreground)", padding: "10px 12px", outline: "none" }}
            />
            <Button variant="primary" onClick={submit}>{mode === "setup" ? "Set PIN" : "Unlock"}</Button>
          </div>
          <p className="command-label">Stored as a salted hash on this machine only. 5 wrong tries locks for 5 minutes.</p>
        </div>
      </div>
    </div>
  );
}
