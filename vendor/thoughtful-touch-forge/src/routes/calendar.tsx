import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/calendar")({
 head:()=>({meta:[{title:"Calendar — 47"},{name:"description",content:"Manage calendar in the 47 personal AI workspace."},{property:"og:title",content:"Calendar — 47"},{property:"og:description",content:"Manage calendar in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="calendar" />,
});
