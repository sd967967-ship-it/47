import { useEffect, useState } from "react";
import { Search, SlidersHorizontal, Plus, ArrowUpRight, Info, Inbox, AlertTriangle, LockKeyhole } from "lucide-react";
import { screenData, type ItemState, type ScreenName, type ModuleItem } from "../data/mock-data";
import { fetchTasks, fetchFacts, fetchAudit } from "../lib/live";
import { Button } from "./Button";

export function ModulePage({ name }: { name: ScreenName }) {
  const data = screenData[name];
  const [viewState, setViewState] = useState<ItemState>("ready");
  const [liveItems, setLiveItems] = useState<ModuleItem[] | null>(null);
  const live = name === "tasks" || name === "memory" || name === "activity";
  useEffect(() => {
    if (!live) return;
    (async () => {
      if (name === "tasks") {
        const tasks = await fetchTasks();
        setLiveItems(tasks.length ? tasks.map(t => ({ title: t.title, meta: t.due_at ? new Date(t.due_at * 1000).toLocaleString() : "No due date" })) : []);
      } else if (name === "memory") {
        const facts = await fetchFacts();
        const keys = Object.keys(facts);
        setLiveItems(keys.length ? keys.map(k => ({ title: k, meta: String(facts[k]).slice(0, 120) })) : []);
      } else {
        const entries = await fetchAudit();
        setLiveItems(entries.length ? entries.slice(-20).reverse().map(e => ({ title: e.event, meta: e.ts ? new Date(e.ts * 1000).toLocaleString() : "" })) : []);
      }
    })().catch(() => setLiveItems([]));
  }, [name]);
  const items = liveItems ?? data.items;
  const emptyHint = live && liveItems !== null && liveItems.length === 0;
  return <div className="page-stage animate-page-in">
    <header className="page-heading"><div><p className="eyebrow">{data.eyebrow}</p><h1>{data.title}</h1><p className="page-description">{data.description}</p></div><Button variant="primary"><Plus size={16} /> New</Button></header>
    <div className="module-toolbar"><label className="search-field"><Search size={16}/><span className="sr-only">Search {data.title}</span><input placeholder={`Search ${data.title.toLowerCase()}`} /></label><label className="state-select"><span className="sr-only">Preview content state</span><select value={viewState} onChange={(event) => setViewState(event.target.value as ItemState)}><option value="ready">Populated</option><option value="loading">Loading</option><option value="empty">Empty</option><option value="error">Error</option><option value="permission">Permission</option></select></label><Button variant="secondary" aria-label="Filter and sort"><SlidersHorizontal size={16}/><span>Filter</span></Button></div>
    {viewState === "ready" && <section className="module-list" aria-label={`${data.title} live items`}>
      {emptyHint
        ? <p className="kv">Nothing here yet — live data from your 47.</p>
        : items.map((item, i) => <article className="module-row" key={item.title}>
        <div className="module-marker">{String(i + 1).padStart(2, "0")}</div><div className="module-copy"><h2>{item.title}</h2><p>{item.meta}</p></div>{item.status && <span className="status-pill">{item.status}</span>}<Button variant="icon" aria-label={`Open ${item.title}`}><ArrowUpRight size={17}/></Button>
      </article>)}
    </section>}
    {viewState === "loading" && <section className="module-state" aria-live="polite"><div className="loading-mark"/><h2>Loading {data.title.toLowerCase()}</h2><p>Preparing this demo view.</p></section>}
    {viewState === "empty" && <section className="module-state"><Inbox/><h2>Nothing here yet</h2><p>Create your first item when you are ready.</p><Button variant="secondary"><Plus size={15}/> Create item</Button></section>}
    {viewState === "error" && <section className="module-state"><AlertTriangle/><h2>This view is unavailable</h2><p>No information was changed. Try loading the demo again.</p><Button variant="secondary">Try again</Button></section>}
    {viewState === "permission" && <section className="module-state"><LockKeyhole/><h2>Permission required</h2><p>Connect an approved source before using this view.</p><Button variant="secondary">Review access</Button></section>}
    <div className="demo-note"><Info size={15}/><span>{live ? "Live information from your 47 backend." : "Sample information for interface preview. Nothing has been connected or changed."}</span></div>
  </div>;
}
