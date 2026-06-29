# Product

## Register

product

## Users

Fiscoscope serves a public, non-specialist-to-specialist audience reading French
public-finance data, primarily three groups:

- **Engaged citizens** — taxpayers and voters who want to understand whether
  public money is spent efficiently. They arrive with curiosity, not training,
  and need plain-language framing plus visible sourcing to trust what they see.
- **Journalists & analysts** — people who will cite specific figures, drill into
  the "Méthodologie & sources" disclosure, and compare years and peer countries.
  They need the numbers to be quotable and the methodology to be defensible.
- **Skeptics** — readers who distrust efficiency claims about government from any
  direction. The interface has to read as scrupulously neutral; any whiff of
  spin loses them.

Context of use: mostly desktop and mobile web, read in short sessions ("what's
the deficit trend?", "how does France compare to Germany?"), not all-day tools.
The primary task on any screen is *reading and trusting a ratio over time*, with
peer benchmarking and methodology one click away.

## Product Purpose

Fiscoscope is an open-source dashboard that measures the productivity and
efficiency of the French public administration using only publicly available
fiscal data (INSEE, OECD, GTED, URSSAF, France Travail). It is ratio-focused
(efficiency per euro, not raw accounting totals), longitudinal (1995–present),
and peer-benchmarked (France vs. DE, GB, IT, ES, NL, SE, OECD average). The whole
pipeline is automated: cron → static JSON → FastAPI → frontend.

It exists because the raw data is public but illegible — scattered across SDMX
APIs and accounting tables that no ordinary reader can assemble into a trend.
Success is when a non-expert can look at a KPI, grasp what it means and where it's
heading, and trust the number enough to repeat it — with the methodology always
within reach to back it up.

## Brand Personality

**Neutral, rigorous, trustworthy.** Quiet authority that lets the data speak and
takes no political side. The voice is editorial and precise, never promotional and
never outraged. Every claim is sourced; uncertainty and structural breaks are
disclosed rather than smoothed over. The emotional goal is *calm confidence* — the
reader should feel they're looking at an honest instrument, not an argument.

This is expressed visually through restraint: an editorial cream canvas with a
Lora/Inter pairing, and a deliberate rule that the French tricolore (bleu/rouge)
is reserved for **data meaning** — bleu for the France series, rouge only for
meaningful negatives — while coral carries interaction. Color earns its place;
it is never decoration.

## Anti-references

- **Government portal.** Not the dated, cluttered, low-trust official-administration
  look (service-public.fr era). Density without hierarchy reads as bureaucracy.
- **Partisan / activist.** No political coloring, no editorializing chrome, no
  outrage framing or "shocking" callouts. Tricolore is data, not flag-waving.
- **Generic SaaS dashboard.** No hero-metric template (big number / tiny label /
  gradient accent), no endless identical icon-card grids, no gradient text.
- **Crypto / fintech flash.** No dark-neon, no animated tickers, no hype motion.
  Flashiness here actively destroys the credibility the product depends on.

## Design Principles

1. **The data is the protagonist.** Chrome recedes; the series, the trend, and the
   comparison are what the eye lands on. Color and weight are spent on meaning.
2. **Earn trust by showing your work.** Every figure carries its source and method
   within one interaction. Disclose breaks, gaps, and assumptions instead of
   hiding them — skeptics are a primary audience, not an edge case.
3. **Impartial by construction.** Neutrality is a design constraint, not a tone we
   add later. No framing that pushes a verdict; let the reader draw conclusions.
4. **Legible to a non-expert, rigorous for an analyst.** Plain-language framing on
   the surface, full methodology a click deeper. Don't make the citizen read like
   an economist, and don't make the analyst distrust the simplification.
5. **Restraint as credibility.** When in doubt, remove. A quiet interface signals
   confidence; a loud one signals persuasion.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**, already reflected in the codebase: the ink ramp and accent
inks (`--coral-ink`, `--rouge-ink`, `--positive-ink`) are tuned for AA contrast on
the cream canvas, focus-visible outlines are present, and all motion has a
`prefers-reduced-motion` path. Because color carries data meaning, encodings must
not rely on hue alone — pair color with line style (the OECD average is dashed),
labels, and direction so the charts remain readable for color-vision deficiency.
Maintain tabular numerals for scannable figures and keep body line length within a
readable measure (`--measure: 64ch`).
