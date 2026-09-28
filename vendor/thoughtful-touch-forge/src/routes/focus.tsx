import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/focus")({
 head:()=>({meta:[{title:"Focus — 47"},{name:"description",content:"Manage focus in the 47 personal AI workspace."},{property:"og:title",content:"Focus — 47"},{property:"og:description",content:"Manage focus in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="focus" />,
});
