<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

- Keep all frontend demo content in `src/data/mock-data.ts` behind typed models so a real service can replace it without changing screens.
- Use a shared application shell with route-driven content pages so navigation and responsive behavior remain consistent.
- Lazy-load the Three.js assistant core and preserve a CSS fallback to protect first render, accessibility, and reduced-motion users.
