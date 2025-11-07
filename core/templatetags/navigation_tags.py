from django import template
from django.urls import reverse


register = template.Library()


def _namespace_matches(match, target):
    if not match or not target:
        return False

    namespace = getattr(match, "namespace", None)
    if not namespace:
        return False

    if namespace == target:
        return True

    if isinstance(namespace, str):
        segments = [segment for segment in namespace.replace(":", " ").split() if segment]
        return target in segments

    if isinstance(namespace, (list, tuple, set)):
        return target in namespace

    return False


def _build_nav_items(request, user=None, context=None):
    if context is not None:
        cached = context.get("_nav_items_cache")
        if cached is not None:
            return cached

    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", "")

    nav_items = [
        {
            "url": reverse("home"),
            "icon": "bi bi-speedometer2",
            "label": "Dashboard",
            "active": url_name == "home",
        },
    ]

    if user and getattr(user, "is_authenticated", False):
        has_connection = False
        connection_manager = getattr(user, "connection_set", None)
        if connection_manager is not None:
            try:
                has_connection = connection_manager.exists()
            except Exception:
                has_connection = False

        if has_connection:
            nav_items.append(
                {
                    "url": reverse("connections:qr_display"),
                    "icon": "bi bi-whatsapp",
                    "label": "Manage Connection",
                    "active": _namespace_matches(match, "connections") and url_name == "qr_display",
                    "badge": "Connected",
                    "badge_class": "bg-success",
                }
            )
        else:
            nav_items.append(
                {
                    "url": reverse("connections:create"),
                    "icon": "bi bi-plus-circle",
                    "label": "Create Connection",
                    "active": _namespace_matches(match, "connections") and url_name == "create",
                }
            )

        nav_items.extend(
            [
                {
                    "url": reverse("aiengine:agent_detail"),
                    "icon": "bi bi-robot",
                    "label": "AI Agent",
                    "active": _namespace_matches(match, "aiengine") and url_name == "agent_detail",
                },
                {
                    "url": reverse("business:business_detail"),
                    "icon": "bi bi-shop",
                    "label": "Business",
                    "active": _namespace_matches(match, "business"),
                },
                {
                    "url": reverse("knowledgebase:knowledge_base_list"),
                    "icon": "bi bi-book",
                    "label": "Knowledge Base",
                    "active": _namespace_matches(match, "knowledgebase"),
                },
                {
                    "url": reverse("profile"),
                    "icon": "bi bi-person-circle",
                    "label": "Profile",
                    "active": url_name == "profile",
                },
            ]
        )
    else:
        nav_items.extend(
            [
                {
                    "url": reverse("signin"),
                    "icon": "bi bi-box-arrow-in-right",
                    "label": "Sign In",
                    "active": url_name == "signin",
                },
                {
                    "url": reverse("signup"),
                    "icon": "bi bi-person-plus",
                    "label": "Sign Up",
                    "active": url_name == "signup",
                },
            ]
        )

    if context is not None:
        context["_nav_items_cache"] = nav_items

    return nav_items


@register.inclusion_tag("core/partials/nav_menu.html", takes_context=True)
def render_nav_menu(context, mode="mobile"):
    request = context.get("request")
    user = context.get("user")

    nav_items = _build_nav_items(request, user, context)

    if mode == "sidebar" and not (user and getattr(user, "is_authenticated", False)):
        nav_items = []

    return {
        "nav_items": nav_items,
        "mode": mode,
    }


@register.simple_tag(takes_context=True)
def notifications_summary(context, limit=5):
    """Return a summary of notifications for the authenticated user."""
    user = context.get("user")

    if not user or not getattr(user, "is_authenticated", False):
        return {
            "notifications": [],
            "unread_count": 0,
        }

    # Avoid duplicated queries by caching on context
    cache_key = "_notifications_summary_cache"
    cached = context.get(cache_key)
    if cached is not None:
        return cached

    notifications_qs = user.notificationlog_set.all().order_by("-created_at")
    notifications = list(notifications_qs[:limit])
    unread_count = user.notificationlog_set.filter(is_read=False).count()

    summary = {
        "notifications": notifications,
        "unread_count": unread_count,
    }

    context[cache_key] = summary
    return summary

