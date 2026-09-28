import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/activity")({
 head:()=>({meta:[{title:"Activity — 47"},{name:"description",content:"Manage activity in the 47 personal AI workspace."},{property:"og:title",content:"Activity — 47"},{property:"og:description",content:"Manage activity in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="activity" />,
});
