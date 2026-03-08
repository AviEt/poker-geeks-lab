# Design System Rules

- Never hard-code colors, font families, border-radius, spacing, or transition durations in component CSS or TSX.
- All visual tokens live in `frontend/src/styles/tokens.css` — always use `var(--color-*)`, `var(--font-family-*)`, `var(--radius-*)`, `var(--duration-*)`.
- For new colors: add to `tokens.css` in the `@theme {}` block first, then use via `var()`.
- For new panels/cards: use `.glass` utility class or the glass recipe in the design system docs.

See [design-system.md](../docs/design-system.md) for full token reference.
