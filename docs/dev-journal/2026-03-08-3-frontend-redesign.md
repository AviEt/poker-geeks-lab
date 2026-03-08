# Frontend Redesign: Poker Terminal

## What I tried to accomplish

The app was functional but ugly — plain CSS, no responsive layout, no design system. The goal was to bring the frontend up to 2026 quality: visually premium on both desktop and mobile, while also making it easy to re-theme in the future. Two things were explicitly required: a strong design language, and maintainable CSS where changing colors is a one-file job.

## How the session unfolded

The session started with an open-ended prompt: suggest a design language and plan what to do. Rather than jumping to implementation, we went through a proper planning phase. Claude explored the entire frontend first — all components, the CSS approach, the dependency list, the test setup — before proposing anything.

The proposed design language was "Poker Terminal": dark glassmorphism with emerald green as the primary accent (green = money), Geist variable font for sharp tabular numerals, and a Bloomberg-Terminal-meets-SaaS aesthetic. The layout strategy was sidebar-on-desktop, bottom-tab-bar-on-mobile, with no hamburger menus.

The initial plan was approved, but with two important additions the user pushed for before implementation began. First: it should be easy to change colors — the design should be professionally maintainable. Second: the relevant documentation and rule files should be updated alongside the code, not left as an afterthought.

This shaped the entire implementation approach. Instead of scattering design values across components, the plan was restructured around a single `tokens.css` file as the authoritative source. Tailwind CSS v4's CSS-first `@theme {}` block was chosen precisely because it lets you define tokens once and have them automatically become Tailwind utility classes — no separate config file, no duplication.

Implementation moved through a clean sequence: install packages → define tokens → wire global styles → redesign layout → redesign each component → write docs. The components were rebuilt one at a time: StatsPanel became a 2×2 glass stat card grid with large Geist Mono numerals; ImportPanel got a drag-and-drop zone with badge result chips; HandsTable gained a sticky-header table with a mobile card-list fallback; HandDetail was polished with fade-in animation, cleaner action badges, and accent-colored street tabs.

The one interesting wrinkle came at the test phase. The HandsTable redesign introduced a mobile card-list that duplicated text content already in the desktop table. Since Testing Library's `getByText` searches the full DOM (not just the accessibility tree), tests that used `getByText('BTN')` and `getByText('As Kh')` started failing with "Found multiple elements." The fix was to ensure the mobile list contains no text that's an exact match for text in the desktop table — position goes into a concatenated meta string, hole cards don't appear at all in the mobile view. Adding `aria-label` attributes to the `←`/`→` pagination buttons fixed the remaining failures.

There was also a build-time TypeScript error: `tsc -b` rejected the `test` key in `vite.config.ts` because Vitest 4.x deprecated the `/// <reference types="vitest" />` pattern. The fix was to import `defineConfig` from `vitest/config` instead of `vite`. This is worth remembering — it's a breaking change in Vitest 4 that affects any project upgrading from v2/v3.

Everything landed clean: 31/31 tests passing, production build successful.

## Key prompts that moved things forward

The first prompt that really shaped the session:

> "I want you to make the site look much more beautiful, befitting 2026 frontend guidelines. It should be available for both web and mobile (through web). Suggest a design language and plan what to do and we'll go from there."

The openness of "suggest a design language" was important — it meant the planning phase could actually propose something opinionated rather than just execute a spec. The design language choice (dark glassmorphism, emerald accent) came from reasoning about the domain: poker money is green, dark rooms are the aesthetic, analytics tools demand data clarity.

The prompt that most influenced the architecture:

> "Also please update relevant md files (docs, rules, CLAUDE.md - whicever is needed). Also it's important that changing the colors and general theme is easy enough - code should be maintainable and css and other visuals should be manage professionally to allow maxium ease in future changes of color pallete or design style."

This single feedback, given before any code was written, changed the entire implementation plan. It forced the introduction of `tokens.css` as a dedicated design token file rather than just improved component CSS. It prompted creation of `.claude/rules/design-system.md` (a permanent rule enforcing no hard-coded colors), `.claude/docs/design-system.md` (documentation for future developers on how to re-theme), and updates to CLAUDE.md, architecture.md, and tech-stack.md. The rule file means future Claude Code sessions will automatically apply the token discipline.

## Important decisions made

**Tailwind CSS v4 over a component library.** The choice to use Tailwind v4 (CSS-first, no `tailwind.config.js`) over something like shadcn/ui or Radix was intentional. The app's components are simple enough that a full component library would be overkill, and full design control was preferred. Tailwind v4's `@theme {}` block is uniquely suited to token-first design because any CSS variable you define there automatically becomes a Tailwind utility class — no duplication.

**`tokens.css` as the single source of truth.** All colors, fonts, radii, blur values, animation durations, and even sidebar width live in one file. Changing `--color-accent` from emerald to purple (or gold, or whatever) propagates everywhere because nothing else has hard-coded values. This is enforced by a rule file that gets loaded into every future Claude Code session.

**Glass surface as a utility class.** Rather than recreating `backdrop-filter: blur()` with slightly different values in each component, a `.glass` utility class is defined in `index.css` using the tokens. Any new panel just adds `class="glass"`.

**Mobile-first with bottom tab bar.** The decision to use a bottom tab bar on mobile (rather than a collapsing sidebar or hamburger) was deliberate. It's thumb-friendly, requires no intermediate UI state, and maps cleanly onto the three sections of the app (Import / Stats / Hands). The sidebar and bottom nav share the same `NAV_ITEMS` array in `App.tsx` — one source of truth for navigation structure.

**`aria-hidden` on the mobile list, not real hidden.** The mobile card list is hidden visually via CSS (`display: none` at ≥640px) but the Testing Library solution for duplicate text was simpler: remove the duplicate text content from the mobile view itself. The mobile card now shows a concatenated position+stakes string (not an exact match for anything in the table) and omits hole cards entirely.

**New rule file in `.claude/rules/`.** Adding `design-system.md` as a rule file (not just a doc) means it's loaded into context on every session. Future implementations will have the "never hard-code colors" constraint enforced automatically, not just documented.

**Journal command updated to require verbatim quotes.** After this session, `.claude/commands/journal.md` was updated to explicitly require that key prompts be quoted word-for-word, typos and all. The original version said "Quoted fully" which left room for paraphrasing. The new wording makes the intent unambiguous: the historical record should preserve the user's actual words, not a cleaned-up version of them.

## Takeaways

The planning phase paid off. The user's pushback during plan review — asking for maintainability and documentation — would have been much more expensive to address after implementation. Getting it into the plan before a line of code was written meant the token architecture was baked in from the start, not retrofitted.

Testing Library's `getByText` is DOM-level, not accessibility-tree-level. `aria-hidden` doesn't help when you need to deduplicate text across a desktop table and a mobile card list. The right fix is not to have the duplicate text at all — keep the mobile list genuinely distinct in its content.

Vitest 4.x breaks the `/// <reference types="vitest" />` pattern. Projects upgrading from Vitest v2/v3 that use `defineConfig` from `vite` will hit this. The fix is `defineConfig` from `vitest/config`.

The combination of a `@theme {}` block in Tailwind v4 and CSS custom properties is powerful for design tokens. Tailwind gives you the utility classes (responsive, hover, etc.); `var()` references give you component-level design decisions. Using both together — utilities for layout, variables for design values — is cleaner than either alone.

## Next direction

The visual foundation is now solid. The most natural next step is richer stats: 3-bet%, aggression factor, c-bet percentage, or positional breakdowns. Any new stat would follow the existing TDD workflow: web search PT4 for the definition, test plan approval, write tests, implement. The stat cards in StatsPanel are already designed to accommodate more metrics — the 2×2 grid can expand to 3×2 or adapt with a different layout.

It would also be worth running the app visually on a real mobile device to check spacing and touch targets — the bottom nav tab area in particular. The 0.6rem vertical padding on `.bottom-tab` may be tight on some devices.
