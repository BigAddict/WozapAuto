# Navigation Inventory — WozapAuto

This document captures the current navigation surfaces rendered via `core/base.html` after removing placeholder entries. Each item is classified as *Primary* (core modules), *Secondary* (supporting actions), or *Utility* (account/feedback controls).

## Global / Mobile Navigation (`#navbarNav`)

| Label | Destination | Classification | Notes |
| --- | --- | --- | --- |
| Dashboard | `home` | Primary | Entry point for overall status. |
| Manage Connection / Create Connection | `connections:qr_display` / `connections:create` | Primary | Conditional based on whether the user has an active connection. |
| AI Agent | `aiengine:agent_detail` | Primary | Leads to agent configuration view. |
| Business | `business:business_detail` | Primary | Business profile management. |
| Knowledge Base | `knowledgebase:knowledge_base_list` | Primary | Document management hub. |
| Profile | `profile` | Utility | Personal account settings summary. |
| Sign In / Sign Up (unauthenticated) | `signin` / `signup` | Utility | Authentication links shown for guests. |

**Observations**
- Global nav mirrors sidebar content for authenticated users, creating redundancy on desktop.
- There is no grouping to distinguish setup tasks from ongoing management actions.

## Header Icons (top-right)

| Label | Destination | Classification | Notes |
| --- | --- | --- | --- |
| Notifications | `audit:notifications` | Utility | Dropdown shows latest entries; links within list are placeholders. |
| Business shortcut | `business:business_detail` | Secondary | Quick access to business management; duplicates primary nav. |
| Knowledge Base shortcut | `knowledgebase:knowledge_base_list` | Secondary | Quick access; duplicates primary nav. |

**Observations**
- Quick links replicate items already in the global nav/sidebar; consider swapping for contextual actions (e.g., help, support).

## Profile Dropdown

| Label | Destination | Classification | Notes |
| --- | --- | --- | --- |
| Profile | `profile` | Utility | Account overview. |
| Logout | `signout` | Utility | Terminates session. |

**Observations**
- Dropdown now contains only implemented actions; future settings/help entries should point to real destinations before reintroduction.

## Sidebar Navigation (Authenticated Users)

| Label | Destination | Classification | Notes |
| --- | --- | --- | --- |
| Dashboard | `home` | Primary | Same as global nav. |
| Manage Connection / Create Connection | `connections:qr_display` / `connections:create` | Primary | Mirrors mobile logic. |
| AI Agent | `aiengine:agent_detail` | Primary | |
| Business | `business:business_detail` | Primary | |
| Knowledge Base | `knowledgebase:knowledge_base_list` | Primary | |
| Profile | `profile` | Utility | |

**Observations**
- Sidebar duplicates global navigation entirely; future IA work should decide whether to collapse to one shell or repurpose sidebar for contextual/secondary actions.

## Breadcrumb Behavior Audit

| Flow | Current Breadcrumb Output | Issue |
| --- | --- | --- |
| Connections – Manage QR (`/connections/`) | Home › Connections | Label is accurate but there is no intermediate “overview” destination; users land directly on a state-specific screen. |
| Connections – Create (`/connections/create/`) | Home › Connections › Create | The “Connections” crumb links back to `/connections/create/`, so there is no way to reach an overview/health page. |
| Business Profile (`/business/profile/`) | Home › Business › Profile | Works as expected; “Business” redirects to `/business/`. |
| Knowledge Base List (`/knowledge/`) | Home › Knowledge | Fallback label omits “Base” and breadcrumb link renders as `href="None"`, exposing a broken anchor. |
| Knowledge Base Upload (`/knowledge/upload/`) | Home › Knowledge › Upload | Same missing/invalid link issue for the intermediate crumb; “Upload” inherits a generic label with no contextual copy. |

**Observations**
- Breadcrumb copy does not align with navigation labels for the Knowledge Base routes.
- Fallback logic introduces `href="None"` anchors whenever a URL mapping is missing.
- Connections flows lack a higher-level summary step, making breadcrumbs less helpful for orientation.

## Next Steps
- Align on which surface (top vs. sidebar) should host primary navigation to reduce redundancy.
- Define contextual navigation needs (per-module shortcuts) to inform eventual sidebar redesign.
- Extend inventory to include breadcrumbs and in-content CTAs during the breadcrumb audit step.

