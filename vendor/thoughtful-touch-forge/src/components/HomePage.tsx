import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { ArrowUp, Check, ChevronRight, CirclePause, FilePlus2, Mic, MicOff, Paperclip, Sparkles, TimerReset, Volume2, VolumeX, X } from "lucide-react";
import type { AssistantState } from "../data/mock-data";
import { quickActions } from "../data/mock-data";
import { apiToken, fetchTasks, sendChat, type LiveTask } from "../lib/live";
import { Button } from "./Button";
const AssistantCore = lazy(() => import("./AssistantCore"));

interface ChatMsg { who: "you" | "agent"; text: string }
type RailId = "today" | "active" | "quick" | "system" | "world" | "learn";
const RAIL_ORDER_KEY = "47-rail-order-v1";
const RAIL_COLLAPSE_KEY = "47-rail-collapsed-v1";
const DEFAULT_ORDER: RailId[] = ["today", "active", "quick", "system", "world", "learn"];

function loadJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

// ---------- microphone with a REAL level meter (Web Audio analyser) ----------
function useMic(onTranscript: (text: string) => void, setState: (s: AssistantState) => void) {
  const [live, setLive] = useState(false);
  const [level, setLevel] = useState(0);
  const [note, setNote] = useState("");
  const refs = useRef<{ stream?: MediaStream; ctx?: AudioContext; raf?: number; rec?: unknown; heardAt?: number; timer?: ReturnType<typeof setInterval> }>({});
  const stop = () => {
    const r = refs.current;
    if (r.raf) cancelAnimationFrame(r.raf);
    if (r.timer) clearInterval(r.timer);
    try { (r.rec as { stop?: () => void } | undefined)?.stop?.(); } catch { /* noop */ }
    try { r.stream?.getTracks().forEach((t) => t.stop()); } catch { /* noop */ }
    try { r.ctx?.close(); } catch { /* noop */ }
    refs.current = {};
    setLive(false);
    setLevel(0);
    setState("idle");
  };
  const start = async () => {
    const SR = (window as unknown as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown }).SpeechRecognition
      || (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
    if (!SR) {
      setNote("Voice typing needs Chrome or Edge.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      refs.current = { ...refs.current, stream, ctx };
      const loop = () => {
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        const avg = sum / data.length / 255;
        setLevel(Math.round(avg * 100));
        const last = refs.current.heardAt || 0;
        if (avg < 0.02 && Date.now() - last > 4000 && last !== 0) {
          setNote("No speech detected — still listening…");
        }
        refs.current.raf = requestAnimationFrame(loop);
      };
      loop();
      const Rec = SR as new () => { lang: string; interimResults: boolean; onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null; onend: (() => void) | null; onerror: (() => void) | null; start: () => void; stop: () => void };
      const rec = new Rec();
      rec.lang = "en-US";
      rec.interimResults = true;
      refs.current.rec = rec;
      refs.current.heardAt = 0;
      rec.onresult = (e) => {
        let txt = "";
        for (const r of Array.from(e.results)) txt += r[0]?.transcript ?? "";
        if (txt.trim()) {
          refs.current.heardAt = Date.now();
          setNote("");
          onTranscript(txt);
        }
      };
      rec.onend = () => stop();
      rec.onerror = () => { setNote("Mic error — check permission."); stop(); };
      rec.start();
      setLive(true);
      setNote("Listening… review the text, then Send.");
      setState("listening");
    } catch {
      setNote("Mic blocked — allow microphone access, then retry.");
    }
  };
  const toggle = () => (live ? stop() : start());
  useEffect(() => () => stop(), []);
  return { live, level, note, toggle, stop };
}

// ---------- browser speech for replies (off by default, fully controlled) ----------
function useVoice() {
  const [enabled, setEnabled] = useState(false);
  const [rate, setRate] = useState(1);
  const [voiceURI, setVoiceURI] = useState("");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.onvoiceschanged = load;
  }, []);
  const stop = () => {
    try { window.speechSynthesis.cancel(); } catch { /* noop */ }
  };
  useEffect(() => () => stop(), []);
  const speak = (text: string, onState: (s: AssistantState) => void) => {
    if (!enabled || !("speechSynthesis" in window)) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 400));
    u.rate = rate;
    const v = voices.find((x) => x.voiceURI === voiceURI);
    if (v) u.voice = v;
    u.onstart = () => onState("speaking");
    u.onend = () => onState("idle");
    synth.speak(u);
  };
  return { enabled, setEnabled, rate, setRate, voiceURI, setVoiceURI, voices, speak, stop };
}

export function HomePage() {
  const [state, setState] = useState<AssistantState>("idle");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [liveTasks, setLiveTasks] = useState<LiveTask[] | null>(null);
  const [order, setOrder] = useState<RailId[]>(() => loadJSON(RAIL_ORDER_KEY, DEFAULT_ORDER));
  const [collapsed, setCollapsed] = useState<string[]>(() => loadJSON(RAIL_COLLAPSE_KEY, []));
  const [dragId, setDragId] = useState<RailId | null>(null);
  const voice = useVoice();
  const mic = useMic((t) => setInput(t), setState);

  useEffect(() => {
    fetchTasks().then(setLiveTasks).catch(() => setLiveTasks([]));
  }, []);
  useEffect(() => {
    try { localStorage.setItem(RAIL_ORDER_KEY, JSON.stringify(order)); } catch { /* noop */ }
  }, [order]);
  useEffect(() => {
    try { localStorage.setItem(RAIL_COLLAPSE_KEY, JSON.stringify(collapsed)); } catch { /* noop */ }
  }, [collapsed]);

  // Live socket: briefings refresh tasks; approval states surface honestly.
  useEffect(() => {
    let cancelled = false;
    import("socket.io-client").then(({ io }) => {
      if (cancelled) return;
      const token = apiToken();
      if (!token) return;
      const socket = io({ query: { token } });
      socket.on("data_47", (msg: { kind?: string }) => {
        if (cancelled) return;
        if (msg.kind === "briefing" || msg.kind === "text") {
          fetchTasks().then(setLiveTasks).catch(() => {});
        }
      });
      (window as unknown as { __sock47?: unknown }).__sock47 = socket;
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const send = async (text?: string) => {
    const value = (text ?? input).trim();
    if (!value) return;
    setMessages((m) => [...m, { who: "you", text: value }]);
    setInput("");
    setState("thinking");
    try {
      const reply = await sendChat(value);
      setMessages((m) => [...m, { who: "agent", text: reply }]);
      voice.speak(reply, setState);
      if (!("speechSynthesis" in window) || !voice.enabled) setState("idle");
      fetchTasks().then(setLiveTasks).catch(() => {});
    } catch {
      setMessages((m) => [...m, { who: "agent", text: "47 is unreachable right now. Is the backend running?" }]);
      setState("error");
    }
  };

  const railTasks = liveTasks === null
    ? [{ id: -1, title: "Loading tasks…", meta: "", done: false }]
    : liveTasks.length === 0
      ? [{ id: -2, title: "No open tasks", meta: "Say “remind me …” to add one", done: false }]
      : liveTasks.slice(0, 5).map((t) => ({ id: t.id, title: t.title, meta: t.due_at ? new Date(t.due_at * 1000).toLocaleString() : "No due date", done: false }));

  const moveRail = (id: RailId, dir: -1 | 1) => {
    setOrder((prev) => {
      const i = prev.indexOf(id);
      const j = i + dir;
      if (i < 0 || j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  };
  const toggleCollapse = (id: RailId) =>
    setCollapsed((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const railSection = (
    id: RailId,
    eyebrow: string,
    title: string,
    head: React.ReactNode,
    body: React.ReactNode,
  ) => (
    <section className="context-section" aria-label={title}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
          {head}
          <button className="task-done-btn" aria-label={`Move ${title} up`}
            onClick={() => moveRail(id, -1)} onKeyDown={(e) => { if (e.key === "ArrowUp") { e.preventDefault(); moveRail(id, -1); } }}>▲</button>
          <button className="task-done-btn" aria-label={`Move ${title} down`}
            onClick={() => moveRail(id, 1)} onKeyDown={(e) => { if (e.key === "ArrowDown") { e.preventDefault(); moveRail(id, 1); } }}>▼</button>
          <button className="task-done-btn" aria-label={collapsed.includes(id) ? `Expand ${title}` : `Collapse ${title}`}
            onClick={() => toggleCollapse(id)}>{collapsed.includes(id) ? "+" : "–"}</button>
        </span>
      </div>
      {!collapsed.includes(id) && body}
    </section>
  );

  const sections: Record<RailId, React.ReactNode> = {
    today: railSection("today", "Today", "What matters now",
      <span>{liveTasks === null ? "…" : `${liveTasks.length} open`}</span>,
      <>
        <div className="priority-list">{railTasks.map((t) => <div className={`priority-item ${t.done ? "is-done" : ""}`} key={t.id}><span className="task-check">{t.done && <Check size={13} />}</span><div><strong>{t.title}</strong><small>{t.meta}</small></div></div>)}</div>
        <div className="mini-metrics"><div><span>Mic level</span><strong>{mic.live ? `${mic.level}%` : "off"}</strong></div><div><span>Brain</span><strong>Live</strong></div></div>
      </>),
    active: railSection("active", "Active task", "Chatting with 47",
      <span className="status-pill warning">Live</span>,
      <>
        <p>Messages run through your 47 backend.</p>
        <div className="progress-track"><span className="progress-half" /></div>
        <div className="task-detail"><span>Replies appear in the conversation.</span><small>Live</small></div>
      </>),
    quick: railSection("quick", "Quick actions", "Move something forward", null,
      <div className="quick-grid">{quickActions.map((a, i) => <button key={a} onClick={() => setInput(a)}><span>{i === 0 ? <Sparkles size={17} /> : i === 2 ? <TimerReset size={17} /> : <FilePlus2 size={17} />}</span>{a}</button>)}</div>),
    system: railSection("system", "System", "This laptop", null,
      <p className="kv">Live vitals stream on the 47 dashboard view. Open <a href={"/classic" + window.location.search} style={{ color: "var(--primary)" }}>classic HUD</a> for gauges.</p>),
    world: railSection("world", "World", "Live headlines", null,
      <p className="kv">Headlines arrive with 47's proactive briefings while you chat.</p>),
    learn: railSection("learn", "Learning", "Memory", null,
      <p className="kv">Facts and stats live in the Memory view.</p>),
  };

  const meterBars = Array.from({ length: 12 }, (_, i) => (
    <span key={i} style={{ display: "inline-block", width: 5, height: 6 + Math.round((mic.level / 100) * 22), background: mic.level > 4 ? "var(--primary)" : "var(--border)", borderRadius: 2, marginRight: 2 }} />
  ));

  return <div className="home-stage animate-page-in">
    <section className="assistant-zone" aria-labelledby="assistant-title">
      <div className="assistant-heading">
        <div><p className="eyebrow">{new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })} · Live workspace</p><h1 id="assistant-title">Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}, Operator.</h1><p>What would you like to make progress on?</p></div>
        <span className="state-badge"><span className="status-dot" />{state === "idle" ? "Ready" : state}</span>
      </div>
      <div className="core-stage">
        <Suspense fallback={<div className="assistant-core"><div className="core-fallback"><span /></div></div>}><AssistantCore state={state} /></Suspense>
        <div className="core-caption"><span>47</span><strong>{state === "idle" ? "Standing by" : state.charAt(0).toUpperCase() + state.slice(1)}</strong><small>{mic.live ? `Mic ${mic.level}%` : "Live interface"}</small></div>
      </div>
      <div className="conversation" aria-live="polite">
        {messages.length === 0 && <div className="message assistant-message"><div className="message-meta"><span>47</span><span>Just now · Live</span></div><p>Connected to your 47 backend. Ask anything, or try “briefing”.</p></div>}
        {messages.map((m, i) => <div className="message assistant-message" key={i}><div className="message-meta"><span>{m.who === "you" ? "You" : "47"}</span></div><p>{m.text}</p></div>)}
      </div>
      <div className="composer">
        <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} rows={2} placeholder="Ask 47 anything…" aria-label="Message 47" />
        <div className="composer-actions">
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Button variant="icon" aria-label="Attach a file"><Paperclip size={18} /></Button>
            <Button variant="icon" aria-label={mic.live ? "Stop listening" : "Start voice input"} onClick={() => mic.toggle()}>
              {mic.live ? <MicOff size={18} /> : <Mic size={18} />}
            </Button>
            <span aria-hidden="true">{meterBars}</span>
            <span className="sr-only" role="status">Microphone {mic.live ? `on, level ${mic.level} percent` : "off"}</span>
            {mic.note && <small style={{ color: "var(--muted-foreground)" }}>{mic.note}</small>}
          </div>
          <Button variant="primary" aria-label="Send message" onClick={() => send()}><ArrowUp size={18} /></Button>
        </div>
        <div className="composer-actions" style={{ marginTop: 6 }}>
          <label className="kv"><input type="checkbox" checked={voice.enabled} onChange={(e) => { voice.setEnabled(e.target.checked); if (!e.target.checked) voice.stop(); }} /> Speak replies aloud</label>
          {voice.enabled && (
            <span style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <select aria-label="Voice" value={voice.voiceURI} onChange={(e) => voice.setVoiceURI(e.target.value)} style={{ background: "var(--card)", color: "var(--foreground)", border: "1px solid var(--border)", borderRadius: 6, height: 30, fontSize: 12 }}>
                <option value="">Default voice</option>
                {voice.voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name}</option>)}
              </select>
              <label className="kv">Speed <input type="range" min={0.5} max={1.5} step={0.1} value={voice.rate} onChange={(e) => voice.setRate(Number(e.target.value))} aria-label="Speech speed" style={{ width: 80 }} /></label>
              <Button variant="icon" aria-label="Stop speech" onClick={voice.stop}><X size={16} /></Button>
            </span>
          )}
        </div>
      </div>
    </section>
    <aside className="context-rail" aria-label="Today and active work">
      {order.map((id) => <div key={id}>{sections[id]}</div>)}
      <button className="task-done-btn" style={{ marginTop: 8 }} onClick={() => { setOrder(DEFAULT_ORDER); setCollapsed([]); }}>Reset layout</button>
    </aside>
  </div>;
}
