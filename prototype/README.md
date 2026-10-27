# The Codebook — UI prototype

A local React + TypeScript + Vite prototype with scripted conversations. Source
Serif 4, yellowish paper surfaces, dark ink and muted green accents establish the
visual direction. Surfaces use solid colors, with no gradients.

From this directory:

```bash
npm ci
npm run dev
```

Open the Local URL printed by Vite, normally `http://127.0.0.1:5173/`. If that port
is occupied, Vite selects the next free port. To check and build the static app:

```bash
npm run build
npm run preview
```

The predev and prebuild scripts copy the original PDF and three crops from the
parent repository into ignored `public/reference/`. Build output and dependencies
are ignored too. The prototype therefore needs this repository's existing data
files when preparing assets. Fonts and KaTeX are bundled locally through npm.

## Explore

- Start with the preloaded tension-member conversation and fraction formula.
- Select a citation to inspect its typeset excerpt and open the original PDF page.
- Switch conversations to see Tables 5 and 19 or the original Figure 5 crop.
- Open the connection example and choose bolted, welded, or custom context.
- Start a new conversation or type a question. Recognized topics select scripted
  replies; unsupported topics identify the prototype's limits.
- Copy an equation's LaTeX, or use inline math in a question: `$A_g$`,
  `$\gamma_{m0}$`, `$f_y$`, `$\mathrm{mm}^{2}$`. Both `$...$` and `\(...\)` work;
  display math accepts `$$...$$` and `\[...\]`.

React escapes user text; KaTeX runs with untrusted commands disabled, finite macro
expansion, and a readable fallback for invalid expressions. Math includes MathML
alongside visual HTML. Mobile layouts use dialogs for conversation navigation and
sources; dialogs support Escape, and reduced-motion preferences are respected.

## Scope and verification

No retrieval or generation API is connected. No API key is needed or sent to the
browser, and the parent `.env` is outside the frontend root. Conversation changes
are kept in memory and reset on reload. Source values come from the prepared
table records. The clause 6.2 formula was visually checked against PDF page 46;
broader OCR and independent-review limitations remain visible in the source panel.

Verified in Chromium on desktop and mobile: formula rendering, LaTeX copying,
source selection, PDF delivery, complete table rows, clarification choices,
custom input, diagram display, follow-ups, new conversations, user-text escaping,
and mobile dialogs. The checked flows produce no JavaScript errors or external
network requests. `npm run build` includes TypeScript checking.

Dependencies and licenses: [React](https://react.dev/),
[Vite](https://vite.dev/), [KaTeX](https://katex.org/) (MIT), and
[Source Serif 4](https://github.com/adobe-fonts/source-serif) (SIL Open Font License).
The exact dependency versions are recorded in `package-lock.json`.
