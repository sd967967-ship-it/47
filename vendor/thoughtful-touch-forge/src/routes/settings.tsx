import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "../components/SettingsPage";
export const Route = createFileRoute("/settings")({
 head:()=>({meta:[{title:"Settings — 47"},{name:"description",content:"Control motion, privacy, and permissions for 47."},{property:"og:title",content:"Settings — 47"},{property:"og:description",content:"Control motion, privacy, and permissions for 47."},{property:"og:type",content:"website"},{name:"twitter:card",content:"summary_large_image"}]}), component:SettingsPage,
});
