import { useEffect, useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, Brain, CalendarDays, CheckSquare, Command, Focus, FolderKanban, Home, Menu, MessageCircle, Search, Settings, StickyNote, SunMedium, X } from "lucide-react";
import { navItems } from "../data/mock-data";
import { Button } from "./Button";

const icons = { home: Home, sun: SunMedium, check: CheckSquare, calendar: CalendarDays, note: StickyNote, folder: FolderKanban, timer: Focus, brain: Brain, activity: Activity, settings: Settings };
export function AppShell({ children }: { children: ReactNode }) {
 const [open,setOpen]=useState(false); const [palette,setPalette]=useState(false);
 const path=useRouterState({select:s=>s.location.pathname});
 useEffect(()=>{ const onKey=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();setPalette(true)} if(e.key==="Escape"){setPalette(false);setOpen(false)}}; addEventListener("keydown",onKey);return()=>removeEventListener("keydown",onKey)},[]);
 return <div className="app-shell">
  <a href="#main-content" className="skip-link">Skip to content</a>
  <aside className={`sidebar ${open?"sidebar-open":""}`}><div className="brand"><span className="brand-mark">47</span><div><strong>Forty Seven</strong><small>Personal intelligence</small></div><Button variant="icon" className="mobile-close" onClick={()=>setOpen(false)} aria-label="Close menu"><X size={18}/></Button></div>
   <nav aria-label="Primary">{navItems.map(item=>{const Icon=icons[item.icon as keyof typeof icons];return <Link key={item.path} to={item.path} onClick={()=>setOpen(false)} className="nav-link" activeProps={{className:"nav-link nav-active"}} activeOptions={{exact:item.path==="/"}}><Icon size={18}/><span>{item.label}</span></Link>})}</nav>
   <div className="sidebar-bottom"><div className="privacy-line"><span className="status-dot"/> Demo mode</div><button className="profile-button"><span className="avatar">R</span><span><strong>Ryan</strong><small>Local preview</small></span></button></div>
  </aside>
  <div className="app-main"><header className="topbar"><Button variant="icon" className="menu-button" onClick={()=>setOpen(true)} aria-label="Open menu"><Menu size={19}/></Button><div className="top-context"><span className="status-dot"/><span>47 is ready</span></div><div className="top-actions"><Button variant="secondary" onClick={()=>setPalette(true)}><Search size={16}/><span>Ask or find</span><kbd>⌘ K</kbd></Button><Button variant="icon" aria-label="Open assistant"><MessageCircle size={18}/></Button></div></header><main id="main-content">{children}</main></div>
  {open&&<button className="scrim" aria-label="Close menu" onClick={()=>setOpen(false)}/>} 
  {palette&&<div className="dialog-layer" role="presentation" onMouseDown={()=>setPalette(false)}><div className="command-dialog" role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={e=>e.stopPropagation()}><div className="command-input"><Command size={18}/><input autoFocus placeholder="Ask 47 or search your workspace…" aria-label="Command"/><kbd>esc</kbd></div><div className="command-content"><p className="command-label">Suggested</p>{["Plan my day","Create a task","Start a 25-minute focus session","Review assistant memory"].map((x,i)=><button key={x} onClick={()=>setPalette(false)}><span>{x}</span><small>{i===3?"Review only":"Demo action"}</small></button>)}</div></div></div>}
 </div>
}
