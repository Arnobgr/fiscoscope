---
name: Fiscoscope
description: An honest civic instrument for reading French public-finance efficiency — editorial calm, data as the protagonist.
colors:
  ink: "#28261f"
  ink-soft: "#514c40"
  ink-faint: "#8a8576"
  cream: "#f4f1ea"
  cream-deep: "#ece7db"
  paper: "#fbfaf6"
  rule: "#e2dccd"
  rule-strong: "#d3cab4"
  bleu: "#0055a4"
  rouge: "#ef4135"
  rouge-ink: "#b3261e"
  taupe: "#8a8576"
  coral: "#cc785c"
  coral-ink: "#a8553a"
  coral-soft: "#f0e4dc"
  positive-ink: "#2c6e49"
typography:
  display:
    fontFamily: "Lora, Georgia, 'Times New Roman', serif"
    fontSize: "clamp(2rem, 4.5vw, 3.1rem)"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "clamp(1.35rem, 2.4vw, 1.9rem)"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.01em"
  figure:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "clamp(2.6rem, 6vw, 3.6rem)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.03em"
    fontVariation: "tabular-nums"
  body:
    fontFamily: "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
    fontFeature: "'ss01', 'cv05'"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.05em"
rounded:
  sm: "6px"
  lg: "12px"
  pill: "999px"
spacing:
  s1: "0.25rem"
  s2: "0.5rem"
  s3: "0.75rem"
  s4: "1rem"
  s5: "1.5rem"
  s6: "2rem"
  s7: "3rem"
  s8: "4.5rem"
components:
  kpi-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "1.5rem"
  kpi-card-hover:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "1.5rem"
  stat-callout:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "1.5rem 2rem"
  last-updated-pill:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-faint}"
    rounded: "{rounded.pill}"
    padding: "0.35em 0.85em"
---

# Design System: Fiscoscope

## 1. Overview

**Creative North Star: "The Public Ledger"**

Fiscoscope reads like an honest civic instrument, not an argument. The system is
built on editorial restraint: a warm cream canvas, a Lora serif for figures and
headings, an Inter sans for prose, and color that is spent almost entirely on
*meaning*. The data is the protagonist; the interface is the quiet, well-set page
it sits on. The feeling to evoke is calm confidence — the reader should sense
they're looking at a trustworthy record of the Republic's finances, with the
sourcing and methodology always one interaction away.

The single most distinctive decision is a strict separation of roles for color.
The French tricolore is reserved for **data semantics** — bleu (#0055a4) is the
France series, the protagonist of every chart; rouge (#ef4135) marks meaningful
negatives only. The brand's interaction accent is **coral** (#cc785c, the
Anthropic-editorial note), which carries links, hover, focus, and the slim
masthead rule — never the data. Color never decorates; if it appears, it means
something.

This system explicitly rejects four things, carried straight from the product's
anti-references: the dated, cluttered **government-portal** look; any **partisan
or activist** coloring or outrage framing; the **generic SaaS dashboard** (hero
metric template, identical icon-card grids, gradient accents); and **crypto/fintech
flash** (dark-neon, animated tickers, hype motion). Each would trade away the
credibility the product depends on.

**Key Characteristics:**
- Warm cream editorial canvas (#f4f1ea), never stark white, never the AI sand-beige cliché — here it is a committed, identity-bearing choice paired with a serif.
- Lora serif for every figure and heading; Inter for body. Contrast by axis (serif × sans), not by two near-identical sans.
- Tricolore = data only; coral = interaction only. The two never cross.
- Flat surfaces at rest, hairline borders, lift only on hover. Restraint over depth.
- Tabular numerals everywhere figures are read; a readable 64ch measure for prose.

## 2. Colors

A warm, low-chroma editorial neutral base, with a tightly rationed set of meaningful colors layered on top.

### Primary
- **Republic Bleu** (#0055a4): The France data series — the protagonist line in every chart and the accent stroke on the primary stat callout. This is the color the eye should follow. Reserved exclusively for France's own data.

### Secondary
- **Editorial Coral** (#cc785c): The interaction accent (the Anthropic note in the pairing). Links, hover borders, focus rings, the 3px masthead rule, section-title ticks, control accents. Use **Coral Ink** (#a8553a) for coral-colored text to hold AA contrast. **Coral Soft** (#f0e4dc) is a tint wash for rare emphasis surfaces.

### Tertiary
- **Signal Rouge** (#ef4135): Meaningful negatives as *marks only* (a deficit threshold, a break note's rule). For negative text use **Rouge Ink** (#b3261e). Never used as chrome or for emphasis-by-default.
- **Positive Ink** (#2c6e49): AA-safe green for favourable year-over-year text only. Never a fill.
- **OECD Taupe** (#8a8576): The peer-average reference line, always rendered dashed so it reads without relying on hue.

### Neutral
- **Ink** (#28261f): Primary text and figures on the cream canvas.
- **Ink Soft** (#514c40): Secondary text, explainers, intros.
- **Ink Faint** (#8a8576): Captions, "as of" labels, footer, muted metadata.
- **Cream** (#f4f1ea): The page canvas.
- **Cream Deep** (#ece7db): Recessed bands and the footer.
- **Paper** (#fbfaf6): Card and surface fill, one step brighter than canvas.
- **Rule** (#e2dccd) / **Rule Strong** (#d3cab4): Hairline borders and dividers; the stronger tone for axis lines and tooltips.

### Named Rules
**The Tricolore-Is-Data Rule.** Bleu and rouge belong to the data layer and nowhere else. Coral owns interaction. If you are reaching for blue or red to style a button, a header, or a card, you are wrong — use coral or ink. The flag is never decoration.

**The Color-Earns-Its-Place Rule.** On any given screen, meaningful color (bleu/rouge/green/coral) covers a small fraction of the surface. The default state of everything is ink-on-cream. Rarity is what makes a colored mark legible.

## 3. Typography

**Display Font:** Lora (with Georgia, "Times New Roman", serif)
**Body Font:** Inter (with system-ui, -apple-system, "Segoe UI", sans-serif)

**Character:** A classic literary serif paired with a neutral, highly legible
grotesque. The pairing reads editorial and considered — Lora carries authority and
warmth on figures and titles; Inter stays out of the way for reading. The contrast
is on the serif × sans axis, deliberately, so the two never compete.

### Hierarchy
- **Display** (Lora 600, clamp(2rem, 4.5vw, 3.1rem), 1.12): The brand wordmark and page H1s. Letter-spacing -0.025em.
- **Headline** (Lora 600, clamp(1.35rem, 2.4vw, 1.9rem), 1.12): Theme-section and detail-page section titles, each led by a small coral tick.
- **Figure** (Lora 600, clamp(2.6rem, 6vw, 3.6rem), 1, tabular-nums): The headline statistic in a stat callout — the single largest element on a KPI detail page. Letter-spacing -0.03em.
- **Body** (Inter 400, 17px, 1.6): All prose. Hold prose to the 64ch measure (`--measure`). Font features ss01 + cv05 are on globally.
- **Label** (Inter 600, 0.7rem, +0.05em, uppercase): Badges, pills, the OECD-comparison tag, "last updated" chip. Sparingly.

### Named Rules
**The Serif-For-Numbers Rule.** Every figure the reader is meant to weigh — KPI values, the stat callout, card values — is set in Lora with tabular numerals. Numbers carry the editorial authority; sans is for the words around them.

**The One-Measure Rule.** Prose never exceeds the 64ch measure. A wide column of body text is the government-portal tell; keep reading columns narrow even when the viewport is wide.

## 4. Elevation

The system is flat by default and conveys depth through tonal layering, not shadow.
Surfaces step up in tone (cream canvas → paper cards) and are separated by hairline
rules rather than drop shadows. Shadows exist, but they are a *response to state*,
not an ambient property: a card sits flush with a near-invisible card shadow at
rest, and lifts on hover.

### Shadow Vocabulary
- **Card (at rest)** (`box-shadow: 0 1px 2px rgba(40, 38, 31, 0.04)`): Barely-there seam under a resting surface. Almost subliminal.
- **Lift (on hover)** (`box-shadow: 0 12px 30px -12px rgba(40, 38, 31, 0.22)`): The hover/active state for an interactive card, paired with a -3px translateY and a coral border. This is the only place real depth appears.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest, defined by tone and a 1px rule. Shadow is earned by interaction (hover, focus), never applied for decoration. If a static card has a heavy shadow, it's wrong.

## 5. Components

### Buttons
This is a read-only dashboard; it has almost no buttons. Interaction is carried by **links** and a single chart toggle, so style those, not invented CTAs.
- **Links:** Coral Ink (#a8553a) text, 1px underline at 2px offset; hover shifts to Ink. Breadcrumb and footer links drop the underline until hover.
- **Toggle (chart "compare" checkbox):** Native checkbox with `accent-color: var(--coral)`, an inline label in Ink Soft. No custom button chrome.
- **Focus (all interactive elements):** 2px coral outline, 2px offset, 3px radius. Never removed.

### Chips / Badges
- **Style:** Uppercase Inter label (0.7rem, +0.05em) in Ink Faint.
- **Last-updated pill:** Paper fill, 1px rule border, fully rounded (999px), Ink Faint text.
- **OECD badge:** Inline label preceded by a 2px dashed taupe rule (a legend swatch), signalling the dashed peer-average line.

### Cards / Containers
- **Corner Style:** 12px radius (`--radius-lg`).
- **Background:** Paper (#fbfaf6) on the cream canvas.
- **Shadow Strategy:** Flat at rest (card shadow); on hover, translateY(-3px) + lift shadow + coral border (see Elevation).
- **Border:** 1px Rule (#e2dccd) at rest; Coral on hover.
- **Internal Padding:** 1.5rem (`--space-5`); min-height 200px so a grid of cards stays even.

### Stat Callout (signature)
The single hero figure on a KPI detail page. Paper surface, 12px radius, 1px rule, with a **4px Republic-Bleu left edge** — the one place a thick colored edge is sanctioned, because here it is a data signal (this is France's figure), not a decorative side-stripe. Lora figure type at clamp up to 3.6rem, tabular nums, with year and year-over-year change beside it.

### Charts (signature)
Recharts, themed to the system: Inter axis labels in Ink Faint, Rule-Strong axis lines, France series in bleu, OECD average as a **dashed taupe** line, tooltips on Paper with a Rule-Strong border and the lift shadow. A "compare to OECD" toggle sits above. Break/caveat notes sit below the chart, set small in Ink Soft with a 3px rouge left rule — reserved for genuine data caveats (structural breaks), the one editorial use of a colored rule.

### Navigation
Minimal. A masthead with the 🇫🇷 Fiscoscope wordmark (Lora) as the home link, an italic Lora tagline, and a last-updated pill. No top nav bar; the KPI grid is the navigation. Footer carries sources, a Méthodologie link, and personal links in Ink Faint.

## 6. Do's and Don'ts

### Do:
- **Do** keep bleu and rouge for the data layer only; style all interaction with **coral** (#cc785c / Coral Ink #a8553a for text).
- **Do** set every reader-facing figure in **Lora with tabular numerals**.
- **Do** keep surfaces flat at rest and let depth appear only on hover (`0 12px 30px -12px rgba(40,38,31,0.22)` + coral border).
- **Do** pair color encodings with a second cue — the OECD line is **dashed**, not just taupe — so charts survive color-vision deficiency.
- **Do** hold prose to the 64ch measure and use the cream canvas (#f4f1ea), never stark white.
- **Do** disclose breaks and caveats in a rouge-ruled note below the chart, not hidden.

### Don't:
- **Don't** look like a **government portal**: no dense, undifferentiated tables, no full-width prose, no low-trust clutter.
- **Don't** read as **partisan or activist**: no flag-waving chrome, no outrage callouts, no editorializing color. The tricolore is data, not a banner.
- **Don't** fall into the **generic SaaS dashboard**: no hero-metric template (gradient accent + tiny label), no endless identical icon-card grids, no gradient text.
- **Don't** add **crypto/fintech flash**: no dark-neon theme, no animated tickers, no hype motion.
- **Don't** use a `border-left`/`border-right` colored stripe as decoration. The only sanctioned thick edge is the 4px bleu stat-callout edge, and only because it is a *data* signal.
- **Don't** apply shadow to a resting surface, and **don't** put a heavy shadow anywhere — it reads as a 2014 app.
- **Don't** introduce a third type family or pair two similar sans; the system is Lora × Inter, full stop.
