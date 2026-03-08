# Design System

## Overview

Poker Geeks Lab uses a **token-based design system** built on Tailwind CSS v4's CSS-first configuration.
All visual decisions — colors, fonts, spacing, radius, blur, animation timing — are defined in a single file.

## Single Source of Truth

**`frontend/src/styles/tokens.css`** — edit this file to change the entire look.

To re-theme (e.g., switch from emerald green to purple):
1. Change `--color-accent` (and `--color-accent-dim`, `--color-accent-text`)
2. Optionally change `--color-bg` and `--color-bg-bloom`
3. That's it — all components update automatically

## Token Categories

### Colors
| Token | Purpose |
|-------|---------|
| `--color-bg` | App background |
| `--color-bg-bloom` | Radial gradient bloom on background |
| `--color-surface` | Glass panel background |
| `--color-surface-hover` | Glass panel on hover |
| `--color-surface-active` | Glass panel pressed/active |
| `--color-border` | Default panel border |
| `--color-border-strong` | Emphasized border |
| `--color-accent` | Primary accent color (re-theme here) |
| `--color-accent-dim` | Accent at 15% opacity (badge backgrounds) |
| `--color-accent-text` | Lighter accent for text on dark |
| `--color-profit` | Positive money / wins |
| `--color-profit-dim` | Profit at 12% opacity |
| `--color-loss` | Negative money / losses |
| `--color-loss-dim` | Loss at 12% opacity |
| `--color-text` | Primary text |
| `--color-text-muted` | Secondary text |
| `--color-text-subtle` | Tertiary / disabled text |
| `--color-pot` | Amber for pot display |
| `--color-hero` | Hero player highlight |
| `--color-action-*-bg/text` | Action badge backgrounds and text |

### Typography
| Token | Value |
|-------|-------|
| `--font-family-sans` | Geist, system-ui fallback |
| `--font-family-mono` | Geist Mono, ui-monospace fallback |

Use `var(--font-family-mono)` for all numbers, card notation, and tabular data.

### Surfaces
| Token | Value |
|-------|-------|
| `--radius-card` | 12px — glass panels |
| `--radius-pill` | 9999px — buttons, badges |
| `--radius-badge` | 6px — action badges |
| `--blur-glass` | 16px — full glass effect |
| `--blur-sticky` | 12px — sticky headers |
| `--sidebar-width` | 240px |

### Animation
| Token | Value |
|-------|-------|
| `--duration-fast` | 120ms — hover states |
| `--duration-normal` | 200ms — transitions |
| `--duration-slow` | 350ms — page enters |

## Glass Surface Recipe

```css
.my-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  backdrop-filter: blur(var(--blur-glass));
  -webkit-backdrop-filter: blur(var(--blur-glass));
}
```

Or use the utility class `class="glass"` defined in `index.css`.

## How Tailwind v4 Uses Tokens

Tokens defined in `@theme {}` automatically generate Tailwind utility classes:
- `--color-accent` → `bg-accent`, `text-accent`, `border-accent`
- `--font-family-mono` → `font-mono`
- `--radius-card` → `rounded-card`

You can mix Tailwind utilities and `var()` CSS references freely in component styles.

## Font Files

Geist variable fonts are served from `/public/fonts/`:
- `Geist-Variable.woff2` — sans-serif, weights 100–900
- `GeistMono-Variable.woff2` — monospace, weights 100–900

These are copied from the `geist` npm package during setup (see setup notes in `tech-stack.md`).

## Component CSS Convention

Each component has its own `.css` file alongside its `.tsx`:
- Use `var(--color-*)` for all colors — never hard-code hex values
- Use `var(--font-family-mono)` for numbers and card notation
- Use `var(--duration-*)` for all transitions
- Use `var(--radius-*)` for border-radius
