# 47 Personal AI Workspace

## Goal
Build the supplied frontend-only concept as an original, polished everyday AI assistant. The experience will clearly label all sample information as demo data and will not imply real device, account, file, or AI access.

## Design direction
- A calm graphite workspace with crisp cyan interaction cues, restrained amber status accents, precise typography, thin structural borders, and minimal glow.
- The assistant core is the visual anchor, while the conversation, current task, and today context remain immediately usable.
- Motion communicates assistant state and interaction feedback; it never becomes ambient clutter.

## Screen and component structure
- Responsive application shell: compact desktop rail, mobile drawer, contextual top bar, global assistant access, and command palette.
- Home workspace: stateful assistant core, conversation surface, action approvals, today summary, active-task timeline, and curated quick actions.
- Productivity views: Today, Tasks, Calendar, Notes, Projects, Focus, Memory, Activity, and Settings, using shared searchable/filterable module patterns and honest mock states.
- Reusable primitives: status labels, buttons, icon controls, panels, messages, progress, empty/error/loading states, dialogs, drawers, tooltips, and toast feedback.

## Technical approach
- Keep TanStack Start routing and React Query conventions; use typed local mock services with deliberate latency and state variants.
- Use a lazy-loaded Three.js scene for the assistant core with capped geometry, visibility pausing, reduced-motion handling, and a semantic static fallback.
- Centralize color, type, spacing, shadow, and timing tokens in the Tailwind v4 design system. Use lightweight CSS transitions for routine UI motion.
- Preserve route-level metadata and add unique metadata for every content screen.

## Accessibility and responsiveness
- Semantic landmarks, logical headings, keyboard-complete navigation and command palette, visible focus, accessible dialogs, status announcements, and labelled icon controls.
- Desktop multi-column workspace becomes a clear single-column mobile flow; the assistant core shrinks, navigation becomes a drawer, and the composer remains reachable.
- Respect operating-system reduced motion and expose Full, Reduced, Minimal, and Off controls in Settings.

## Performance and verification
- Lazy-load 3D, pause it when hidden, cap rendering cost, avoid expensive layered blur, and keep layout stable while content changes.
- Verify build diagnostics, keyboard flows, main interactions, reduced-motion/static fallback, and responsive layouts at desktop and mobile sizes.
- Finish with a visual polish pass across every screen covering spacing, alignment, typography, hierarchy, consistency, states, contrast, focus, hover, clipping, and animation timing.
