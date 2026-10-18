---
name: Dignity Credit Engine
colors:
  surface: '#f9f9f8'
  surface-dim: '#dadad9'
  surface-bright: '#f9f9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f3'
  surface-container: '#eeeeed'
  surface-container-high: '#e8e8e7'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#3f4947'
  inverse-surface: '#2f3130'
  inverse-on-surface: '#f1f1f0'
  outline: '#6f7977'
  outline-variant: '#bec9c6'
  surface-tint: '#1a6962'
  primary: '#004943'
  on-primary: '#ffffff'
  primary-container: '#0e625b'
  on-primary-container: '#93dbd2'
  inverse-primary: '#8cd4ca'
  secondary: '#855300'
  on-secondary: '#ffffff'
  secondary-container: '#fea619'
  on-secondary-container: '#684000'
  tertiary: '#00446a'
  on-tertiary: '#ffffff'
  tertiary-container: '#005c8e'
  on-tertiary-container: '#a4d3ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a7f0e6'
  primary-fixed-dim: '#8cd4ca'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#cde5ff'
  tertiary-fixed-dim: '#94ccff'
  on-tertiary-fixed: '#001d32'
  on-tertiary-fixed-variant: '#004b74'
  background: '#f9f9f8'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  display:
    fontFamily: Noto Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Noto Sans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Noto Sans
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
  headline-md:
    fontFamily: Noto Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
  headline-sm:
    fontFamily: Noto Sans
    fontSize: 19px
    fontWeight: '600'
    lineHeight: 26px
  body-lg:
    fontFamily: Noto Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-sm:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-lg:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Noto Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1rem
  margin-mobile: 1rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system is tailored for underserved credit applicants: street vendors, gig economy workers, and new-to-credit micro-entrepreneurs. The core ethos is dignity-first, transparent, and approachable. Financial terminology is stripped of institutional jargon in favor of plain-spoken, reassuring guidance.

The visual style combines **Modern Corporate Reliability** with **Warm Tactility**:
- **Dignity-First Clarity:** Visuals never patronize or obscure. Metrics are framed around progress and opportunity rather than deficiency or debt.
- **Physical-Digital Bridge:** Clean surfaces, deliberate borders, and defined boundaries mimic tangible passbooks, physical receipts, and physical cash ledgers.
- **High-Accessibility Ergonomics:** Built specifically for field conditions—glare in open-air markets, entry-level smartphone displays, single-thumb handling, and varying literacy levels.
- **One Primary Decision Per View:** Screens are scannable with a strict rule of a single dominant action to reduce cognitive load and prevent input anxiety.

## Colors

The palette grounds the interface in institutional stability (Deep Teal) balanced with optimistic warmth (Amber) and physical parchment comfort (Warm Ivory).

### Functional Roles
- **Primary (`#0E625B`, `#0B4F4A`, `#147A71`):** Represents institutional trust, safety, and official status. Used for headers, primary CTAs, active bottom navigation states, and base score indicators.
- **Secondary / Accent (`#F59E0B`, `#D97706`, `#FEF3C7`):** Represents momentum, unlocks, advisory alerts, and high-value milestones.
- **Tertiary (`#0369A1`):** Reserved for contextual insights, educational tips, and informative guidance notes.
- **Background (`#FBFBFA`, `#F5F5F0`):** Replaces harsh stark whites with an organic, paper-like warmth that reduces eye strain under direct sunlight.
- **Surfaces (`#FFFFFF`):** Cards and actionable sheets sit on crisp white with a structural border (`#E5E7EB`) to define tap zones clearly.

### Status System (Icon + Text Mandatory)
Color is never used as the sole conveyor of status. Every state requires an accompanying icon and an explicit descriptive label:
- **Positive / Verified (`#15803D`):** Always accompanied by a checkmark badge and text (e.g., "Verified / सत्यापित").
- **Review / Pending (`#B45309`):** Paired with a clock or shield icon and descriptive text (e.g., "Under Review / समीक्षा में").
- **Informational (`#0369A1`):** Paired with an info-circle icon for educational financial guidance.
- **Attention / Action Required (`#B91C1C`):** Paired with an alert triangle for missing uploads or stalled verifications.

## Typography

Noto Sans is selected for its robust multilingual rendering parity across Devanagari (Hindi, Marathi) and Latin scripts. Complex ligatures, vowel signs (matras), and conjunct consonants render reliably without vertical clipping or awkward spacing shifts.

### Rules & Readability Guardrails
- **Minimum Base Body:** 16px is the absolute baseline for interactive or narrative reading text. 14px is strictly reserved for non-critical metadata or tags.
- **Line Heights:** Generous line heights (minimum 1.5x on body copy) accommodate multi-line vernacular scripts without vertical clashing.
- **Numeric Clarity:** Numbers and financial figures use tabular styling with bold weights for rapid ledger-style scanning.
- **Language Harmonization:** When toggling between English, Hindi, and Marathi, typography scale parameters remain constant to prevent screen jumping.

## Layout & Spacing

The layout is built for a 390px mobile viewport baseline, scaling gracefully to larger mobile screens and tablets while enforcing strict thumb-zone ergonomics.

### Mobile Grid & Layout
- **Viewport Constraints:** Centered mobile container with a maximum width of 480px on desktop environments to maintain focus on the touch-first layout.
- **Column System:** 4-column fluid layout with a 16px outer margin and 12px gutters.
- **Bottom Canvas Reservation:** All scrolling screens maintain a bottom padding buffer of `88px` to ensure floating navigation never conceals primary actions or card details.
- **Tap Zone Rhythm:** Vertical spacing between clickable interactive items is strictly pegged to `space-md` (16px) or higher to prevent mis-taps.

## Elevation & Depth

This design system avoids blurry layered shadows, which render poorly on low-cost IPS displays and wash out in bright sunlight. Instead, it employs **Tonal Layering with Structural Outlines**.

### Elevation Hierarchy
- **Level 0 (Canvas Base):** Background color `#FBFBFA`. Flat, non-interactive.
- **Level 1 (Card & Content Surface):** Solid `#FFFFFF` fill bounded by a continuous 1px outline in `#E5E7EB`. Depth is suggested through subtle border contrast rather than drop shadows.
- **Level 2 (Active Sheets & Sticky Bars):** Solid `#FFFFFF` fill bounded by a top border in `#E2E8F0` with a subtle contact line: `0 -2px 8px rgba(11, 79, 74, 0.05)`. Used for bottom navigation and persistent footer actions.
- **Level 3 (Modal / Verification Drawers):** Backdrop dimming at 60% opacity (`rgba(11, 27, 25, 0.60)`) with an elevated surface anchored directly to the bottom screen edge.

## Shapes

A balanced shape radius provides a modern, friendly character while retaining structural integrity.

### Shape Tokens in Practice
- **Inputs & Cards (0.5rem / 8px):** Provides structured, confidence-inspiring containers that feel stable and organized.
- **Interactive Buttons & Progress Meters (0.75rem to 1rem / 12px to 16px):** Softer corners signal touch interaction without shifting into toy-like full pills.
- **Pills (Full Radius):** Reserved exclusively for status indicators, micro-badges, and language toggles to distinguish functional tags from actionable cards.

## Components

### Buttons
- **Primary CTA:** Full-width container, minimum height 52px (well exceeding the 48px baseline). Background `#0E625B`, text `#FFFFFF`, font weight 600. Includes an explicit trailing icon (e.g., right arrow) to reinforce forward progress.
- **Secondary Action:** Minimum height 52px. Transparent background with a 1.5px border in `#0E625B` and text in `#0E625B`.
- **Destructive / Reset:** Text-only button with a visible underline and minimum 48px tap target zone.

### Inputs & Form Fields
- **Container:** Height 56px, background `#FFFFFF`, border 1.5px `#D1D5DB`, border radius 8px.
- **Typography:** Floating or persistent top label (14px, `#374151`), user text (18px, `#111827`).
- **Input Aids:** Large numeric keypads triggered automatically for phone numbers, OTPs, and daily income amounts. Clear inline visual affordances (e.g., currency symbol ₹ prefix permanently fixed).

### Cards & Ledger Blocks
- **Credit Score Card:** Prominent surface card featuring a high-contrast radial or step arc meter. Uses Deep Teal (`#0E625B`) for positive bands and Warm Amber (`#F59E0B`) for growth zones. Includes an plain-language summary: e.g., "Score: Strong (मजबूत) — Eligible for ₹25,000 Loan".
- **Insight Cards:** Left-bordered card (4px solid accent) breaking financial tips into digestible, bite-sized tasks.

### Bottom Navigation Bar
- **Height & Layout:** Fixed 64px height with an underlying home-indicator safe area. Four primary tabs: **Home (होम)**, **Documents (दस्तावेज़)**, **Score (स्कोर)**, and **Advisor (सलाहकार)**.
- **States:** Active tab displays a solid Deep Teal icon and text badge. Inactive tabs use muted charcoal (`#6B7280`) with clear icon outlines.

### Language Switcher
- **Design:** Compact segmented pill anchored in the top header.
- **Options:** Clearly displays `EN` | `हिं` | `म`. Switching languages is persistent across sessions and immediately updates labels without screen reloads.

### Checkboxes & Radio Controls
- **Hit Area:** Minimum 48px × 48px touch bounding box with a 24px visual box.
- **Visual Feedback:** 2px stroke in `#0E625B` when active, with an explicit high-contrast checkmark or filled center dot.