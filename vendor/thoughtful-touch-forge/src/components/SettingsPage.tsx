import { useState } from "react";
import { Bell, Mic, Database, Gauge, ShieldCheck } from "lucide-react";
import { Button } from "./Button";

const rows = [
  { icon: Mic, title: "Microphone", copy: "Required only when voice mode is active.", status: "Not allowed" },
  { icon: Database, title: "Long-term memory", copy: "Store only preferences you explicitly approve.", status: "Off" },
  { icon: Bell, title: "Notifications", copy: "Reminder and focus-session updates.", status: "Demo only" },
];
export function SettingsPage() {
  const [motion, setMotion] = useState("System");
  return <div className="page-stage animate-page-in"><header className="page-heading"><div><p className="eyebrow">Control & privacy</p><h1>Settings</h1><p className="page-description">Choose how 47 behaves, moves, and handles your information.</p></div><ShieldCheck className="heading-icon"/></header>
    <section className="settings-section"><div className="section-title"><Gauge size={18}/><div><h2>Motion level</h2><p>System preference is respected by default.</p></div></div><div className="segmented" role="radiogroup" aria-label="Motion level">{["System","Full","Reduced","Off"].map(x => <Button key={x} variant={motion === x ? "primary" : "ghost"} role="radio" aria-checked={motion === x} onClick={() => setMotion(x)}>{x}</Button>)}</div></section>
    <section className="settings-list">{rows.map(({icon: Icon,title,copy,status}) => <div className="settings-row" key={title}><Icon size={18}/><div><h2>{title}</h2><p>{copy}</p></div><span className="status-pill">{status}</span></div>)}</section>
    <div className="demo-note"><ShieldCheck size={15}/><span>These controls are a frontend preview and do not grant device access.</span></div>
  </div>;
}
