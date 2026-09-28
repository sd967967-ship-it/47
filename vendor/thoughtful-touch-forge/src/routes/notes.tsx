import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/notes")({
 head:()=>({meta:[{title:"Notes — 47"},{name:"description",content:"Manage notes in the 47 personal AI workspace."},{property:"og:title",content:"Notes — 47"},{property:"og:description",content:"Manage notes in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="notes" />,
});
