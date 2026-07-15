# Handoff: Europe Incoming — Data-Driven Package Pages

## Overview
Replace the per-product static brochure HTML pages (currently rebuilt from ~8 PDFs each year) in the `europeincoming/TestFITSTD` repo with a **single reusable package-page template** driven by two JSON files per product:

- `products/<product-id>.json` — evergreen content (itinerary, inclusions, hotels, tips). Written once, rarely touched.
- `prices/<year>.json` — the ONLY file edited for the annual price update.

The page lets a buyer (travel-trade agent) switch between **travel styles** (Trains & Taxi Transfers / Self Drive / Private Exclusive Coach), **hotel category** (3★/4★) and **season** (Apr–Oct / Nov–Mar), and download the currently-selected variation as a PDF via the browser print dialog.

## About the Design Files
The files in `reference/` are **design references created in HTML** in a design tool — they show intended look and behavior; they are not production code to copy verbatim. `reference/Package Page.dc.html` uses a proprietary component runtime (`<x-dc>`, `{{ }}` holes, `sc-for`/`sc-if`, a `DCLogic` class). **Recreate it in the target repo's environment.** The TestFITSTD repo is a static site rebuilt by `scripts/rebuild_site.py` via GitHub Actions — the recommended approach is:

1. Write one plain static HTML/JS template (vanilla JS is fine; no framework needed).
2. Extend `rebuild_site.py` to generate one page per `products/*.json` (inject product JSON + prices JSON inline or fetch at runtime).
3. Migrate every existing brochure page: extract its content into a `products/*.json`, and its rates into `prices/2026.json` entries.

## Fidelity
**High-fidelity.** Recreate pixel-perfectly. All values below are final.

## Data Model

### products/<id>.json (see data/products/ireland-discovery.json for a complete example)
- `id`, `title` (headline style — ALL CAPS with terminal period, e.g. "Ireland Discovery."), `eyebrow`, `heroImage`, `pricesFile`
- `map`: `{ points: [{lat, lng, label, nights}], closeLoop: bool }` — points with `nights > 0` are overnight cities (numbered badge markers); `nights: 0` are excursion/en-route stops (small grey dots)
- `styles`: object keyed by style id (`trains` / `selfdrive` / `private`). Each has `name`, `blurb`, `nights` ("6 nights · 7 days"), `route` ("Dublin (2N) → Limerick (3N) → Dublin (1N)" — may differ per style), `aboutNights`, `transport` (map of day-number → included-transport sentence), `inclusions` (string array)
- `days`: `[{num, title, overnight, desc, taste?, experience?, shopping?, fallbackIncluded?}]` — taste/experience/shopping are optional per-day pills, only present where the destination is genuinely famed for it
- `hotels`: `[{city, nights, h3, h4}]`
- `about`: `[{title, body}]` sidebar facts (best season, weather, currency)
- `goodToKnow`: `[{title, body, styles?}]` — `styles` array restricts a tip to specific travel styles (e.g. driving tips only for selfdrive)
- `terms`: string array

### prices/<year>.json (see data/prices/2026.json)
- `validFrom`, `validTo`, `currency`
- `variants[styleId][hotelCat][season] = { single, twin, child }` — hotelCat "3"/"4", season "summer"/"winter". All rates net, per person, EUR
- `optionalTours`: `[{name, price}]`

**Note: all rates in the sample prices file are placeholders — real 2026-27 rates must be entered.**

## Page Layout (desktop, max-width 1200px centered, 48px side padding)

1. **Sticky top bar** (64px, white, 1px #E5E7EC bottom border, z-300): logo left (38px tall) + "← All packages" link; right: "Trade enquiries / fitsales@europeincoming.com" + gold **↓ DOWNLOAD PDF** button.
2. **Hero** (420px, navy #0B1733): full-bleed photo at 65% opacity, bottom gradient `linear-gradient(to top, rgba(3,7,20,0.75), rgba(3,7,20,0.05) 65%)`. Bottom-left: gold eyebrow, 56px Montserrat 900 uppercase white title, meta row (nights · route · "From €X pp" in gold) — **all three meta values change with the selected travel style**; "From" = cheapest twin rate within that style.
3. **Sticky variant bar** (below top bar, top:64px, z-290): "TRAVEL STYLE" label + pill buttons, one per style key. Active pill: navy fill/white text; inactive: white/#4B5563 text/1px #CBD0DA border. Right-aligned: the style's blurb.
4. **Body**: two columns — main (flex:1) + sidebar (300px, sticky top:132px).

### Main column sections (each headed by an 11px Montserrat 700 uppercase #6B7280 label with 1px bottom border)
- **Day by day — <style name>**: per day a 56px/1fr grid: big day number (34px Montserrat 900 navy) | title (16px Montserrat 700 uppercase), overnight line (11px gold #B8870A caps), description paragraph (14px Open Sans #4B5563 lh 1.75), then pills:
  - "INCLUDED" pill (green #1F8A5B on #EEF5F0) + transport text from `styles[style].transport[day]`, falling back to `day.fallbackIncluded` or "Day at leisure."
  - Optional "LOCAL TASTE" (#B8870A on #FEF7DC), "LOCAL EXPERIENCE" (#14245A on #EEF1F8), "SHOPPING" (#4B5563 on #F2F4F7). No day images.
- **Package includes — <style name>**: 2-col grid of ✓ items (green check) from the style's `inclusions`.
- **Sample hotels**: 3-col grid card (1px gap on #E5E7EC, 10px radius) — city, nights, 3 STAR / 4 STAR hotel names.
- **Package rates**: segmented toggles (3★/4★ and Apr–Oct/Nov–Mar; active = navy fill) + table with navy header row (white 10px caps), rows Single / Twin-Double / Child (2–11), right-aligned bold navy prices. Footnote italic 12px.
- **Optional tours & extras**: 2-col grid, name left, "€X pp" bold right. From prices file.
- **Good to know**: 2-col grid cards, gold caps titles — filtered by `styles` field so e.g. driving tips only appear on Self Drive.
- **T&C accordion**: collapsed by default; toggle ▼/▲; bullet list.

### Sidebar
- **About this tour** card (#FAFAF8, 1px border, 10px radius, 22px padding): gold caps title; **route map** (180px, Leaflet, click to enlarge — see below) with a navy "⤢ ENLARGE" badge bottom-right; then stacked fact rows (13px semibold title + 12px #6B7280 body): duration + route (style-dependent) and the `about` items.
- **Ready to quote?** card (navy): gold caps title, white/80 body, full-width gold "EMAIL THE FIT TEAM" mailto button.
- **Footer**: navy band, company reg + contact, 12px white/55.

## Route map (Leaflet 1.9.4, CartoDB `light_all` tiles)
- Small map: non-interactive (no zoom/drag/attribution), fit bounds to points +0.4° padding, dashed navy polyline (weight 2, dash "5,4") through points in order, closed loop if `closeLoop`.
- Overnight cities: circular divIcon badge — navy fill, 2px gold #F2B91D ring, white bold night-count (18px small / 22px large map); permanent tooltip "Dublin · 3N" above.
- Excursion stops: small grey #9AA1AE circleMarker, radius 4/5, tooltip label only.
- Tooltips: transparent background, 10px Montserrat 700 navy, white text-shadow outline halo.
- **Popup**: clicking the small map opens a modal (fixed overlay `rgba(11,23,51,0.65)`, centered white panel `min(960px,100%) × min(640px,100%)`, 10px radius, shadow) with header "ROUTE MAP — <TITLE>" + ✕ button, and a fully interactive Leaflet map (zoom control, scroll zoom, drag). Closes on ✕, Escape key, or backdrop click. Destroy the large map instance on close.

## Interactions & State
State: `style` (default first key), `cat` ("3"), `season` ("summer"), `tcOpen` (false), `mapOpen` (false).
- Style switch instantly updates: hero meta, variant blurb, day-by-day transport lines, inclusions, rates, good-to-know filtering, sidebar route/duration, section headings.
- **Download PDF** = expand T&C, then `window.print()` after ~150ms. Print CSS: `.no-print { display:none }` on top bar, variant bar, rate toggles, sidebar, map popup; body column goes full-width (`display:block`). Prints the currently selected variation only.
- Transitions: 220ms cubic-bezier(0.22,0.61,0.36,1) color fades only, no scale/bounce.

## Design Tokens (Europe Incoming design system)
- Navy `#0B1733` (structure, text headers, table header, footer) · Gold `#F2B91D` (CTAs, accents; hover `#E0A810`) · Gold-dark text `#B8870A` · Ink `#1A1D2E` · Body grey `#4B5563` · Muted `#6B7280` · Faint `#9AA1AE` · Line `#E5E7EC` · Faint line `#F2F4F7` · Off-white `#FAFAF8` · Green `#1F8A5B` on `#EEF5F0`
- Type: **Montserrat** 600/700/900 (headlines ALL CAPS with terminal period, buttons/eyebrows 0.08em tracking) + **Open Sans** 400/600/700 body. Google Fonts.
- Radii: 6px buttons/inputs, 10px cards, 999px pills. Shadows navy-tinted, soft.
- UK English. Gold reserved for CTAs — never section backgrounds.

## Assets
- `assets/logo-europe-incoming.png` (included)
- Hero photo: currently an Unsplash Dublin photo (placeholder) — replace with licensed EI photography per product.

## Files in this bundle
- `reference/Package Page.dc.html` — the design reference (design-tool format; read for exact inline styles/markup, do not ship)
- `data/products/ireland-discovery.json` — complete worked product example
- `data/prices/2026.json` — prices schema example (placeholder numbers)
- `assets/logo-europe-incoming.png`

## Migration checklist for Claude Code
1. Build the static template (one HTML + one JS, no framework) matching this spec.
2. Wire `scripts/rebuild_site.py` to emit a page per product JSON.
3. For each existing brochure in the repo: extract content → `products/<id>.json`; extract rates → `prices/2026.json`.
4. Keep existing URLs/paths working (e.g. `multi-country/uk-ireland/…`) or add redirects.
5. Verify print output per style and the annual workflow: editing only `prices/<year>.json` updates every page.
