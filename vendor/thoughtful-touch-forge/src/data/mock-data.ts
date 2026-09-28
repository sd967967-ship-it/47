export type AssistantState = "idle" | "listening" | "thinking" | "speaking" | "working" | "success" | "error" | "offline" | "permission";
export type ItemState = "ready" | "loading" | "empty" | "error" | "permission";

export interface NavItem { label: string; path: string; icon: string }
export interface Task { id: number; title: string; meta: string; done: boolean; priority: "High" | "Medium" | "Low" }
export interface ModuleItem { title: string; meta: string; status?: string }
export type ScreenName = "today" | "tasks" | "calendar" | "notes" | "projects" | "focus" | "memory" | "activity";

export const navItems: NavItem[] = [
  { label: "Home", path: "/", icon: "home" },
  { label: "Today", path: "/today", icon: "sun" },
  { label: "Tasks", path: "/tasks", icon: "check" },
  { label: "Calendar", path: "/calendar", icon: "calendar" },
  { label: "Notes", path: "/notes", icon: "note" },
  { label: "Projects", path: "/projects", icon: "folder" },
  { label: "Focus", path: "/focus", icon: "timer" },
  { label: "Memory", path: "/memory", icon: "brain" },
  { label: "Activity", path: "/activity", icon: "activity" },
  { label: "Settings", path: "/settings", icon: "settings" },
];

export const tasks: Task[] = [
  { id: 1, title: "Finish chemistry revision plan", meta: "Today · 45 min", done: false, priority: "High" },
  { id: 2, title: "Review project notes", meta: "Today · 20 min", done: false, priority: "Medium" },
  { id: 3, title: "Morning mobility routine", meta: "Completed at 8:10", done: true, priority: "Low" },
];

export const quickActions = ["Plan my day", "Add task", "Start focus", "Create note", "Set reminder", "Find a file"];

export const screenData: Record<ScreenName, { eyebrow: string; title: string; description: string; items: ModuleItem[] }> = {
  today: { eyebrow: "Monday · Demo timeline", title: "Today", description: "A clear view of what deserves your attention next.", items: [
    { title: "Chemistry revision", meta: "4:00 PM · 45 minutes", status: "Priority" }, { title: "Team sync", meta: "5:30 PM · Video call", status: "Upcoming" }, { title: "Evening run", meta: "7:15 PM · 5 km", status: "Routine" }] },
  tasks: { eyebrow: "3 open · Demo data", title: "Tasks", description: "Priorities, grouped without the noise.", items: tasks.map(t => ({ title: t.title, meta: t.meta, status: t.done ? "Done" : t.priority })) },
  calendar: { eyebrow: "September 2026 · Demo calendar", title: "Calendar", description: "Time blocks and commitments in one calm timeline.", items: [
    { title: "Deep work", meta: "10:00–11:30", status: "Focus" }, { title: "Lunch with Mira", meta: "1:00–2:00", status: "Personal" }, { title: "Team sync", meta: "5:30–6:00", status: "Work" }] },
  notes: { eyebrow: "12 notes · Demo library", title: "Notes", description: "Thoughts captured, connected, and ready to revisit.", items: [
    { title: "Ideas for the research essay", meta: "Edited 18 minutes ago", status: "Pinned" }, { title: "Books to explore", meta: "Edited yesterday", status: "List" }, { title: "Weekly reflection", meta: "Edited Sunday", status: "Journal" }] },
  projects: { eyebrow: "3 active · Demo workspace", title: "Projects", description: "Longer efforts, visible momentum, fewer loose ends.", items: [
    { title: "Chemistry exam prep", meta: "8 of 12 steps complete", status: "67%" }, { title: "Personal site refresh", meta: "Research phase", status: "Active" }, { title: "Running plan", meta: "Week 3 of 8", status: "On track" }] },
  focus: { eyebrow: "Focus mode · Demo timer", title: "Protect your attention", description: "Set an intention, choose a duration, and make space to finish.", items: [
    { title: "25 minute sprint", meta: "Short, structured interval", status: "Start" }, { title: "50 minute deep work", meta: "One task, fewer interruptions", status: "Start" }, { title: "Open session", meta: "No fixed ending", status: "Start" }] },
  memory: { eyebrow: "Private by design · Demo memory", title: "What 47 remembers", description: "47 remembers only what you approve. Review or remove saved preferences anytime.", items: [
    { title: "Prefer concise morning plans", meta: "Approved 12 Sep", status: "Preference" }, { title: "Studying organic chemistry", meta: "Approved 21 Sep", status: "Project" }, { title: "Focus sessions usually 50 minutes", meta: "Approved 25 Sep", status: "Routine" }] },
  activity: { eyebrow: "Transparent activity · Demo log", title: "Activity", description: "Every proposed action, pause, and result remains visible.", items: [
    { title: "Prepared a study-plan draft", meta: "10:06 · No external action taken", status: "Draft" }, { title: "Paused reminder setup", meta: "09:58 · Waiting for approval", status: "Approval" }, { title: "Summarized uploaded notes", meta: "Yesterday · Local demo", status: "Complete" }] },
};
