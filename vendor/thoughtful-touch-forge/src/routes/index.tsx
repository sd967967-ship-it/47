import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "../components/HomePage";
export const Route = createFileRoute("/")({
 head:()=>({meta:[{title:"47 — Personal AI Workspace"},{name:"description",content:"A calm, transparent personal AI workspace for planning and daily focus."},{property:"og:title",content:"47 — Personal AI Workspace"},{property:"og:description",content:"A calm, transparent personal AI workspace for planning and daily focus."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:HomePage,
});
