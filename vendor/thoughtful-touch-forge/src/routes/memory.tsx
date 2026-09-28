import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/memory")({
 head:()=>({meta:[{title:"Memory — 47"},{name:"description",content:"Manage memory in the 47 personal AI workspace."},{property:"og:title",content:"Memory — 47"},{property:"og:description",content:"Manage memory in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="memory" />,
});
