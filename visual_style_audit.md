# Visual Style & Asset Audit

## Templates with Inline `<style>` Blocks
None (all previously identified inline styles have been migrated to shared static stylesheets).

_Resolved in this pass:_ inline CSS was removed from the knowledge base views (`knowledge_base_list`, `knowledge_base_upload`, `knowledge_base_search`, `knowledge_base_document_detail`), the dashboard (`core/home.html`), the connections flows (`connections/base.html`, `connections/qr_display.html`), user profile surfaces (`core/profile.html`, `core/profile_edit.html`), account security pages (`core/change_password.html`, `core/password_reset_confirm.html`), business setup screens (`core/create_business_profile.html`, `business/category_form.html`), and the global shell (`core/base.html`) with equivalent rules moved into static CSS files.

## Templates Re-importing Bootstrap CSS
- `core/templates/core/base.html` (global include)

_Resolved in this pass:_ Knowledge base templates now rely on the shared stylesheet and no longer re-import Bootstrap locally.

## Animation & Script Inventory (`static/js/main.js`)
- `initScrollAnimations` — attaches intersection observers to `.scroll-animate` elements (currently none scoped, but runs globally).
- `initFloatingCards` — animates `.floating-card` elements (used only on landing hero but initialized site-wide).
- `initParticleEffect` — injects canvas for `.hero-section` (landing page only, global init).
- `initTypingEffect` — adds typing animation for `[data-typing]` elements (rare usage).
- `initCounterAnimations` — animates `.stat-number` counts when visible.
- `initParallaxEffect` — applies transform on elements with `data-parallax` on scroll.
- `initSmoothScrolling` — hijacks anchor links starting with `#`.
- `initLoadingStates` — now targets buttons marked with `data-loading-button` to avoid hijacking every `.btn` click.
- `initMobileNavigation` — manages navbar toggling (required globally).
- `initNotificationDropdown`, `initFormEnhancements`, and chart helpers also register globally.

Optional animation helpers are now called only when matching elements exist, reducing no-op work on pages that do not use those interactions. Additional follow-up could split animation code into page-specific bundles.