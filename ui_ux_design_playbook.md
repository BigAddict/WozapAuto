# WozapAuto UI/UX Design Playbook

Updated: 2025-11-09

This living document consolidates our UI/UX vision, design system, implementation backlog, and tracking for reusable components across the product. Treat it as the single source of truth for visual, interaction, accessibility, and performance guardrails.

---

## 1. Mission & Scope

- **Objective:** Deliver a cohesive, accessible, and performant operator experience for configuring WhatsApp automation with minimal visual clutter.
- **Audience:** Product, design, engineering, and stakeholders who review or contribute to UI/UX decisions.
- **Artifacts tracked here:** Design principles, component system, IA map, accessibility/performance log, analytics instrumentation, and change history.

---

## 2. Experience Pillars & Current Signals

| Pillar | Focus Areas | Current Signals | Next Opportunities |
| --- | --- | --- | --- |
| **Visual Design** | Token-driven palette, typographic rhythm, balanced density | Tokens in `main.css`; “moon kiss” surfaces used on dashboard/profile/business | Externalize tokens for Bootstrap theming; prune gradients; normalize icon set & spacing scale |
| **Interaction Design** | Predictable navigation, clear CTA hierarchy, responsive patterns | App shell + onboarding checklist; skip link & focus states present; connection detail page fully responsive (mobile/tablet/desktop) | Collapse sidebar duplication; promote primary actions via reusable CTA bar; streamline wizard steps |
| **Accessibility** | WCAG 2.1 AA contrast, semantic flow, focus management | Skip link, landmarks, reduced motion handling live; toast notifications with ARIA labels and keyboard support | Fix mobile sidebar focus trap; audit icon-only controls for aria-labels; add keyboard traps to modals |
| **Performance** | Lean asset loading, motion budgets, Core Web Vitals | JS deferred, animations respect `prefers-reduced-motion` | Evaluate critical CSS + lazy loading for heavy knowledge views; trim unused CSS bundles |
| **Feedback & Guidance** | Onboarding cues, progressive disclosure, analytics loop | Checklist progress counters; consistent empty states; modern toast notification system with auto-dismiss | Add celebration state on onboarding completion; wire CTA analytics + tooltip hints |

---

## 3. Information Architecture Snapshot

- `/` → Dashboard (`core.home`): onboarding checklist first; marketing hero for guests.
- Auth: `/signin`, `/signup`, `/forgot-password`, `/reset-password/<uid>/<token>`.
- Account: `/profile`, `/profile/edit`, `/profile/change-password`.
- Connections: `/connections/`, `/connections/create/` (WhatsApp setup).
- Business hub: `/business/profile/` + nested products/services/categories/carts/bookings/hours.
- Knowledge base: `/knowledge/` list, upload, search, detail views.
- AI engine: `/aiengine/` configuration.
- Audit & notifications: `/audit/` (rename candidate → “Ops Hub”).
- First-time setup wizard: `/onboarding/<step>/` steps `welcome → profile → business → verify → complete`.

Primary journeys to optimize for density & clarity:
1. **New user:** `signup → onboarding → dashboard CTA`. Focus on progressive disclosure + celebratory completion state.
2. **Operator:** `signin → dashboard → manage connection → curate knowledge → audit notifications`. Ensure quick access to high-frequency tasks.
3. **Business admin:** `dashboard → business catalog/actions`. Provide data summaries before deep tables.

---

## 4. Design System Foundations

**Dependencies**
- Framework: Bootstrap 5.3.8 (CDN now; target local bundling + SCSS overrides).
- Iconography: Bootstrap Icons 1.10.0.
- Motion: AOS (review necessity post-cleanup).

**Token Strategy**
- ✅ `/static/css/tokens.css` now exports color, typography, spacing, radius, elevation, and motion tokens.
- Map tokens to Bootstrap variables via SCSS (e.g., `$primary`, `$body-font-family`, `$border-radius`).
- Author lighten/darken helpers for CTA gradients; standardize neutral grays for backgrounds and borders.

**Global Styles**
- Promote `main.css` to focus on utility helpers absent in Bootstrap; migrate bespoke layout rules into contextual component styles.
- ✅ Layout shell (`navbar`, `sidebar`, footer, header icons) consolidated in `/static/css/layout.css`; base template now loads `tokens → main → layout → app-shell`.
- Adopt CSS custom properties only for runtime adjustments (dark mode, motion preferences).

**Governance**
- Require every new component to document tokens used + responsive behaviors in this playbook.
- Use Figma tokens (future) to sync with SCSS token build.

**Component Documentation Standards**
- ✅ **Alert/Toast**: Uses `--space-*`, `--border-radius-*`, `--shadow-*`, `--success-color`, `--error-color`, `--info-color`, `--warning-color` tokens. Responsive: top-right (desktop), top-center (mobile). Breakpoints: 768px. Location: `static/js/main.js` (`showToast()`), `static/css/alerts.css`.
- ✅ **Connection Detail Page**: Uses `--space-*`, `--font-size-*`, `--border-radius-*` tokens. Responsive breakpoints: 576px (tablet), 768px (desktop). Grid layouts: 1→2→4 columns. Touch targets: min 80px height. Location: `connections/templates/connections/connection_detail.html`, `static/css/connections.css`.

---

## 5. Component Library Tracker

| Component | Location | Bootstrap Baseline | Status | Actions |
| --- | --- | --- | --- | --- |
| Buttons | `components/button.py` + `button.html` | `btn`, `btn-outline`, utilities | ✅ Live | Add loading/disabled aria states; align gradients with token scale |
| Cards / Surfaces | `components/card.py`, `static/css/app-shell.css` | `card`, `shadow` | ⚠️ Needs refactor | Unify padding/footers; expose variants (default/muted/interactive) |
| Form Field | `components/form_field.py` | `form-floating`, `form-control` | ⚠️ Needs refactor | Replace custom grids with Bootstrap `row-cols`; add validation messaging slots |
| Input Group | `components/input_group.py` | `input-group` | ✅ Live | Audit icon sizing; ensure label association |
| Stat Card | `components/stat_card.py` | `card`, `badge` | ⚠️ Needs refactor | Reduce chrome, support compact mode |
| Connection Card | `components/connection_card.py` | `card`, `list-group` | 🚧 Experimental | Document states (connected/pending/error); add focus styles |
| Layout Shell | `core/templates/core/base.html` | `navbar`, `offcanvas`, `container` | ✅ Live | Shared nav tag + mobile offcanvas + desktop sidebar |
| Alert / Toast | `static/css/alerts.css`, `static/js/main.js` | `alert`, `toast` | ✅ Live | Uses design tokens; supports success/error/info/warning variants; auto-dismiss + manual dismiss; ARIA labels; responsive positioning |
| Tabs / Pills | scattered templates | `nav`, `tab-content` | ❌ Missing component | Create component with ARIA roles, keyboard support |
| Data Table | `business` templates | `table`, `responsive` | ⚠️ Needs refactor | Standardize table density; add empty + loading states |
| Wizard Stepper | onboarding CSS | `nav` + custom classes | ❌ Missing component | Build stepper component with progress + description slots |

Legend: ✅ Live / ⚠️ Needs refactor / 🚧 In progress / ❌ Not started.

---

## 6. Layout Simplification & Decongestion Plan

**Navigation Shell**
- ✅ Collapsed duplicate menu definitions (header vs sidebar) into shared template tag.
- ✅ Replaced fixed sidebar duplication with Bootstrap `offcanvas` for <lg viewports; kept desktop sidebar responsive.
- Review notifications dropdown → convert to badge + modal/slideout to reduce header clutter.

**Dashboard (`core/home.html`)**
- Elevate onboarding checklist into reusable component with progress header + actionable CTA row.
- Introduce 12-column responsive grid (`row row-cols-1 row-cols-lg-2`) for cards; remove overlapping gradients.
- Provide compact stats summary (3-up) leveraging `card` + `list-group` for details.

**Profile Edit (`core/profile_edit.html`)**
- Swap custom `surface-card` wrappers for Bootstrapped `accordion` or `card` sections with sticky action bar.
- Transform progress indicator into `nav-pills` with numeric badges; highlight active step via utilities.
- Replace `form-grid` with `row g-4` + `col-md-6` semantics; rely on componentized form fields.

**Business & Catalog Pages**
- Use `row row-cols-1 row-cols-md-2` for cards to avoid extra white space.
- Provide summary header with key metrics; move advanced filters into collapsible panel.

**Knowledge Base**
- Introduce vertical tabs or segmented controls for `Upload / Search / Documents` to limit simultaneous panels.
- Lazy load heavy document previews; leverage skeleton loaders for file listings.

**General Density Controls**
- Enforce max width on long-form content (`max-width: 960px`) with auto margins.
- Introduce `stack-sm/stack-md` utility classes (vertical spacing) to replace manual `mb-*` cascades.
- Audit icons + supporting copy: limit to one icon per card; convert secondary help text into tooltips or collapsible help blocks.

---

## 7. Accessibility & Performance Backlog

| Backlog Item | Scope | Owner | Status |
| --- | --- | --- | --- |
| Mobile sidebar focus trap | `core/base.html` scripts | Front-end | 🔜 Schedule fix with offcanvas migration |
| Icon-only controls labeling | Header actions, tables | Front-end | 🔜 Add `aria-label` + `title` attributes |
| Form validation feedback | Auth + profile forms | Back-end + Front-end | 🔄 Inline errors live; add summary + role=alert |
| Motion audit | Global animations | Design | ✅ `prefers-reduced-motion` honored; revisit after AOS removal |
| Lighthouse / Axe run | Staging build | QA | 🔜 Queue after layout refactor |
| Critical CSS extraction | Above-the-fold hero | Front-end | 🚧 Investigate using `django-compressor` |
| Bundle review | `static/css/*.css`, `static/js/*.js` | Front-end | 🔄 Inventory ongoing; target tree-shaking of unused JS |

---

## 8. Analytics & Feedback Instrumentation

- `onboarding_step_completed` – server event when a step persists; add CTA context metadata.
- `dashboard_cta_clicked` – client event naming CTA + location; ensure consent gating.
- `connection_status_changed` – tie into `AuditService`; forward to analytics stream.
- `knowledge_document_uploaded/searched` – capture payload size + filters for adoption tracking.
- `business_entity_created` – include entity type + count for growth metrics.

Implementation guardrails: reuse centralized analytics helper, annotate events with user role, provide opt-out toggle for GDPR compliance.

---

## 9. Workstreams & Tracking

- [x] Extract tokens to `/static/css/tokens.css` and align with Bootstrap variables.
- [x] Move layout styles into `/static/css/layout.css`; update base template includes.
- [ ] Swap CDN Bootstrap for locally bundled version with SCSS overrides (post-tokenization).

### B. Componentization
- [ ] Convert dashboard checklist into `django_components` component with success state.
- [x] Ship alert/toast component with accessibility attributes. ✅ Implemented in `static/js/main.js` with `showToast()` function; CSS in `static/css/alerts.css`; uses design tokens, ARIA labels, responsive positioning.
- [ ] Standardize form fields + validation messaging.
- [ ] Build wizard stepper component reused by onboarding + multi-step forms.

### C. Page Decongestion
- [ ] Redesign navigation shell using offcanvas pattern + single config.
- [ ] Reduce profile edit page to accordion layout with sticky save bar.
- [ ] Simplify business catalog grid + filters.
- [ ] Introduce knowledge base segmented controls + skeleton states.

### D. Measurement & QA
- [ ] Run Lighthouse + Axe audits; log findings in backlog table.
- [ ] Define analytics dashboards for onboarding funnel + CTA usage.
- [ ] Plan usability testing for navigation changes (5 participants).

---

## 10. Change Log

| Date | Area | Notes |
| --- | --- | --- |
| 2025-11-05 | Playbook | Refactored document to focus on Bootstrap-aligned design system, component tracker, and decongestion roadmap. |
| 2025-11-05 | Design tokens | Extracted CSS variables into `static/css/tokens.css` and wired into base layout includes. |
| 2025-11-05 | Layout shell | Moved navigation/sidebar/footer styles to `static/css/layout.css` and pruned duplicates from `app-shell.css`. |
| 2025-11-05 | Navigation shell | Introduced `render_nav_menu` tag to reuse nav items across header and sidebar. |
| 2025-11-05 | Mobile navigation | Migrated mobile menu to Bootstrap offcanvas and hid sidebar below lg breakpoints. |
| 2025-11-05 | Notifications UX | Added global notification modal with mark-as-read interaction. |
| 2025-11-05 | Navigation planning | Identified duplication issues; earmarked offcanvas migration. |
| 2025-11-05 | Density audit | Profile edit, dashboard, and knowledge base flagged for simplification. |
| 2025-11-05 | Accessibility backlog | Captured focus trap + icon labeling issues for prioritization. |
| 2025-11-09 | Alert/Toast Component | Implemented modern toast notification system in `static/js/main.js` (`showToast()` function) and `static/css/alerts.css`. Features: design token-based styling, success/error/info/warning variants, auto-dismiss (5s default), manual dismiss, ARIA labels, responsive positioning (top-right desktop, top-center mobile), slide-in/out animations. Moved from `connections.css` to dedicated `alerts.css` for global use. |
| 2025-11-09 | Connection Detail Page | Refactored connection detail page for full responsiveness. Mobile-first approach: header stacks vertically on mobile, avatar scales (56px mobile, 72px desktop), overview grid (1→2→4 columns), stats grid (1→2→4 columns), touch-friendly targets (min 80px height). Uses Bootstrap responsive utilities and design tokens throughout. |
| 2025-11-09 | Responsive Patterns | Enhanced connection page with mobile-first responsive design. Breakpoints: <576px (mobile), 576-768px (tablet), >768px (desktop). All grids and layouts adapt fluidly. Buttons wrap properly on mobile with icon-only fallbacks. |

Append entries as UI/UX initiatives progress. Ensure each change links to commits, tickets, or design artifacts.
