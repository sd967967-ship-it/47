import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/tasks")({
 head:()=>({meta:[{title:"Tasks — 47"},{name:"description",content:"Manage tasks in the 47 personal AI workspace."},{property:"og:title",content:"Tasks — 47"},{property:"og:description",content:"Manage tasks in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="tasks" />,
});
