# WozapAuto UI/UX Design Playbook

Updated: 2025-11-04

This living document captures our UI/UX principles, current implementation status, and open opportunities. It replaces the previous `visual_style_audit.md` file and should be the single source of truth for design consistency and performance improvements.

---

## 1. Mission & Scope

- **Objective:** Deliver a cohesive, accessible, and performant operator experience for configuring WhatsApp automation.
- **Audience:** Internal product/design/engineering team; external stakeholders reviewing UI/UX decisions.
- **Artifacts tracked here:** Design principles, IA map, component inventory, accessibility/performance changes, analytics instrumentation, and change log.

---

## 2. Experience Pillars & Characteristics

| Pillar | Characteristics | Current Implementation Highlights | Next Opportunities |
| --- | --- | --- | --- |
| **Visual Design** | Cohesive palette, modular spacing, clear hierarchy | Shared tokens in `main.css`; onboarding/dashboard use consistent gradients and typography; stat/CTA cards restyled via extracted CSS modules | Formalize color/typography tokens in a design system reference; unify iconography across business & knowledge base sections |
| **Interaction Design** | Familiar navigation, clear CTAs, responsive layout | App shell standardized in `app-shell.css`; onboarding checklist drives primary actions; skip link + focusable main for keyboard users | Convert onboarding checklist into reusable component; audit sidebar vs top-nav redundancy post IA redesign |
| **Accessibility** | WCAG 2.1 AA contrast, semantic structure, focus management | Skip link, `<main>` landmark, reduced-motion handling, checklist semantics; upcoming Axe/Lighthouse review slated | Address mobile sidebar focus trap; verify icon-only controls have accessible labels |
| **Performance** | Optimized assets, deferred scripts, reduced motion when preferred | Bootstrap/AOS/custom JS loaded with `defer`; animations gated by `prefers-reduced-motion` | Consider code-splitting animations, lazy-loading heavy sections (e.g., knowledge base detail charts) |
| **Feedback & Guidance** | Onboarding, contextual messaging, analytics loop | Dashboard checklist with progress counters; knowledge base empty states consistent; analytics plan drafted | Implement success/celebratory states for completed onboarding; hook analytics events into logging pipeline |

---

## 3. Information Architecture Map

### Sitemap (auth vs guest)
- `/` → Dashboard (`core.home`); authenticated users see onboarding checklist, guests see marketing hero.
- `/signin`, `/signup`, `/forgot-password`, `/reset-password/<uid>/<token>` → Authentication flows.
- `/profile`, `/profile/edit`, `/profile/change-password` → Account management.
- `/connections/` (QR management) and `/connections/create/` → WhatsApp connection setup.
- `/business/` → redirects to `/business/profile/`; nested resources for products, services, categories, carts, bookings, business hours.
- `/knowledge/` → Knowledge base list; `/knowledge/upload/`, `/knowledge/search/`, `/knowledge/document/<id>/` for operations.
- `/aiengine/` → AI agent configuration view.
- `/audit/` → Notifications/logs (consider renaming or merging into ops hub).
- `/onboarding/` wizard (`welcome`, `profile`, `business`, `verify`, `complete`) for first-time setup.

### Primary User Journeys
1. **New User:** `signup → onboarding welcome → profile → business → verify → complete → dashboard checklist`.
2. **Operator:** `signin → dashboard → manage connection → update knowledge base → review notifications`.
3. **Business Admin:** `dashboard → business resources (products/services/categories) → monitor carts/bookings`.

---

## 4. Component & Style Inventory

- **App Shell** (`static/css/app-shell.css`): navigation, sidebar, skip link, onboarding panel, reduced-motion overrides, **surface card** system.
- **Dashboard Checklist** (`core/home.html`): inline template using progress context (`onboarding_progress`, counts). Candidate for component extraction.
- **Auth & Account** (`static/css/auth.css`, `static/css/account.css`): sign-in/up, forgot/reset password, change password modules.
- **Profile** (`static/css/profile.css`): profile summary/edit cards, quick actions.
- **Onboarding Wizard** (`static/css/onboarding.css`): shared styling for welcome/profile/business/verify/complete steps.
- **Business Forms** (`static/css/business-forms.css`): business profile creation and category icon selector.
- **Knowledge Base** (`static/css/knowledgebase.css`): upload, list, search, document detail.
- **Connections** (`static/css/connections.css`): QR display, connection detail, modals/buttons.

**Pending:** consolidate reusable UI (alerts, empty states, CTA buttons) into partials or component tags after dashboard refactor settles.

---

## 5. Accessibility & Performance Log

- ✅ Added skip link + focusable `<main>` for keyboard navigation (2025-11-04).
- ✅ Deferred Bootstrap/AOS/custom scripts for faster first paint.
- ✅ Honored `prefers-reduced-motion` in JS animations and global CSS transitions.
- 🔜 Run Axe/Lighthouse audits on staging; remediate contrast & aria issues as needed.
- 🔜 Ensure mobile sidebar toggling traps focus and restores scroll when closed.

Keep logging changes here with date + scope.

---

## 6. Analytics Instrumentation Plan

- `onboarding_step_completed` – triggered server-side when each checklist milestone is saved.
- `dashboard_cta_clicked` – client event capturing which onboarding CTA users follow.
- `connection_status_changed` – logs transitions between `pending/open/disconnected` (tie into AuditService).
- `knowledge_document_uploaded` / `knowledge_document_searched` – measure knowledge base adoption.
- `business_entity_created` – identify catalog growth (include entity type).

Implementation guidance: reuse `AuditService` where possible, add lightweight analytics helper for client-side events, feature flag for GDPR compliance.

---

## 7. Change Log

| Date | Area | Notes |
| --- | --- | --- |
| 2025-11-04 | Dashboard onboarding | Added checklist panel, contextual progress, removed stat clutter. |
| 2025-11-04 | App shell | Introduced skip link, deferred scripts, reduced-motion handling, centralized layout CSS. |
| 2025-11-04 | Surface system | Rolled out global “moon kiss” surface cards/buttons to dashboard, profile, business, connections, and knowledge base flows. |
| 2025-11-04 | Documentation | Consolidated `visual_style_audit.md` into this playbook with IA map, component inventory, and analytics plan. |
| 2025-11-05 | Profile | Harmonized WhatsApp connection section with moon-kiss surfaces and updated Manage CTA. |
| 2025-11-05 | Business onboarding | Restyled create business profile flow with guided stepper and moon-kiss surface system. |
| 2025-11-05 | Auth flows | Added password visibility toggles, compact sign-in layout, and shared styling across auth endpoints. |
| 2025-11-05 | Identity simplification | Removed in-app profile avatars/names and enforced no-space usernames across auth flows. |
| 2025-11-05 | Onboarding | Skipped legacy personal-profile step; business setup now pre-fills signup email and flows straight to verification. |
| 2025-11-05 | Signup UX | Wired server-side validation into the custom signup form so errors persist and render inline. |
| 2025-11-05 | Form validation | Synced sign-in, change/reset password flows with inline server errors and value persistence. |

Add future entries when UI/UX changes ship or plans evolve.

