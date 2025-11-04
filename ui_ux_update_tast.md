# UI/UX Immediate Remediation Tasks

These items can be tackled right away to reduce user confusion and prepare for the broader UX overhaul described in `proposal.md`.

## Navigation & Information Architecture
- [x] Inventory every link exposed by `core/base.html` (top nav + sidebar) and classify as primary, secondary, or redundant.
- [x] Remove placeholder links (e.g., `Add Agent`, `Settings` stubs) or hide them behind feature flags until functionality exists.
- [x] Document current breadcrumb outputs for key flows (Connections, Business, Knowledge Base) to highlight mismatches between labels and user intent.

## Visual Consistency & Layout Hygiene
- [ ] List all templates that re-import Bootstrap or define inline `<style>` blocks, starting with `knowledgebase/knowledge_base_list.html` and `connections/base.html`.
- [ ] Consolidate duplicated card and stat styles by replacing per-page CSS with reusable components from `components/`.
- [ ] Identify animation-heavy assets loaded globally and note where they are actually required.

## Guidance & Onboarding Support
- [ ] Audit `core/home.html` widgets and label each card with its target user state (new vs. returning) to prepare for progressive disclosure.
- [ ] Create a draft onboarding checklist describing the minimum steps (Account ➜ Connection ➜ Business ➜ Knowledge Base) for engineering review.

## Accessibility & Performance Baseline
- [ ] Run an Axe or Lighthouse accessibility scan on the dashboard and knowledge base list screens; capture all high/critical findings.
- [ ] Verify color contrast for primary and secondary CTAs against WCAG 2.1 AA and log any failures.
- [ ] Inspect mobile navigation behavior to ensure focus trapping and body scroll locking comply with accessibility best practices.

## Documentation & Collaboration Prep
- [ ] Start an IA map (sitemap + user flows) in the shared design workspace to ground upcoming stakeholder conversations.
- [ ] Draft a component inventory spreadsheet covering buttons, cards, forms, alerts, and empty states with references to template paths.
- [ ] Outline analytics events we can instrument immediately (e.g., connection_created, knowledge_upload_started) to capture baseline data before redesigned flows ship.

