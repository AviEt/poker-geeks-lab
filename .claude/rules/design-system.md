# Design System Rules

## Token Usage (mandatory)

- **Never hard-code color values** in component CSS or TSX (no `#10b981`, no `rgba(...)`, no named CSS colors).
  Always use `var(--color-*)` from `tokens.css`.

- **Never hard-code pixel values for spacing** as inline styles. Use the 8pt spacing scale
  (`0.5rem`, `1rem`, `1.5rem`, `2rem`, `2.5rem`, `3rem`) or CSS custom properties.

- **Never hard-code font families** inline. Use `var(--font-family-sans)` or `var(--font-family-mono)`.

- **Never hard-code border-radius values** inline. Use `var(--radius-card)`, `var(--radius-pill)`,
  `var(--radius-badge)`.

- **Never hard-code transition durations** inline. Use `var(--duration-fast)`, `var(--duration-normal)`,
  `var(--duration-slow)`.

## Adding New Colors

If you need a color not in `tokens.css`:
1. Add it to `tokens.css` in the `@theme {}` block with a descriptive name
2. Use `var(--color-your-name)` in the component
3. Do NOT inline the color in the component CSS

## Glass Surface

For any new panel or card, use the `.glass` utility class or the glass recipe from `design-system.md`.
Never recreate the glass effect manually with different values — always use the tokens.

## Where Tokens Live

Single source of truth: `frontend/src/styles/tokens.css`

See `.claude/docs/design-system.md` for full documentation.
