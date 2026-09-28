import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/today")({
 head:()=>({meta:[{title:"Today — 47"},{name:"description",content:"Manage today in the 47 personal AI workspace."},{property:"og:title",content:"Today — 47"},{property:"og:description",content:"Manage today in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="today" />,
});
