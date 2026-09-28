import { createFileRoute } from "@tanstack/react-router";
import { ModulePage } from "../components/ModulePage";
export const Route = createFileRoute("/projects")({
 head:()=>({meta:[{title:"Projects — 47"},{name:"description",content:"Manage projects in the 47 personal AI workspace."},{property:"og:title",content:"Projects — 47"},{property:"og:description",content:"Manage projects in the 47 personal AI workspace."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:()=> <ModulePage name="projects" />,
});
