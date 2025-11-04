from django import template
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def breadcrumb(context):
    """
    Generate breadcrumb navigation based on the current URL and context.
    """
    request = context['request']
    path_parts = request.path.strip('/').split('/')
    breadcrumbs = []
    
    # Always start with Home
    breadcrumbs.append({
        'name': 'Home',
        'url': reverse('home'),
        'active': False
    })
    
    # Build breadcrumbs based on URL patterns
    current_url = ''
    
    for i, part in enumerate(path_parts):
        if not part:
            continue
            
        current_url += '/' + part
        
        # Determine breadcrumb name and URL based on the path
        breadcrumb_info = get_breadcrumb_info(part, current_url, context)
        
        if breadcrumb_info:
            breadcrumb_info['active'] = (i == len(path_parts) - 1)
            breadcrumbs.append(breadcrumb_info)
    
    # Generate HTML
    html_parts = ['<nav aria-label="breadcrumb" class="mb-4">', '<ol class="breadcrumb">']
    
    for breadcrumb in breadcrumbs:
        name = breadcrumb['name']
        url = breadcrumb.get('url')

        if breadcrumb['active']:
            html_parts.append(f'<li class="breadcrumb-item active" aria-current="page">{name}</li>')
        elif url:
            html_parts.append(f'<li class="breadcrumb-item"><a href="{url}">{name}</a></li>')
        else:
            html_parts.append(f'<li class="breadcrumb-item">{name}</li>')
    
    html_parts.extend(['</ol>', '</nav>'])
    
    return mark_safe(''.join(html_parts))

def get_breadcrumb_info(part, current_url, context):
    """
    Get breadcrumb information for a URL part.
    """
    # Define breadcrumb mappings
    breadcrumb_mappings = {
        'connections': {
            'name': 'Connections',
            'url': reverse('connections:qr_display')
        },
        'business': {
            'name': 'Business',
            'url': reverse('business:business_list')
        },
        'knowledge': {
            'name': 'Knowledge Base',
            'url': reverse('knowledgebase:knowledge_base_list')
        },
        'aiengine': {
            'name': 'AI Agent',
            'url': reverse('aiengine:agent_detail')
        },
        'products': {
            'name': 'Products',
            'url': reverse('business:product_list')
        },
        'services': {
            'name': 'Services',
            'url': reverse('business:service_list')
        },
        'appointments': {
            'name': 'Appointments',
            'url': reverse('business:appointment_list')
        },
        'carts': {
            'name': 'Orders',
            'url': reverse('business:cart_list')
        },
        'categories': {
            'name': 'Categories',
            'url': reverse('business:category_list')
        },
        'create': {
            'name': 'Create',
            'url': None  # Will be handled by parent
        },
        'edit': {
            'name': 'Edit',
            'url': None  # Will be handled by parent
        },
        'delete': {
            'name': 'Delete',
            'url': None  # Will be handled by parent
        },
        'detail': {
            'name': 'Details',
            'url': None  # Will be handled by parent
        }
    }
    
    # Check for specific patterns
    if part in breadcrumb_mappings:
        return breadcrumb_mappings[part]
    
    # Handle dynamic parts (like IDs or slugs)
    if part.isdigit() or len(part) > 10:  # Likely an ID or slug
        # Try to get context information
        if 'object' in context:
            obj = context['object']
            if hasattr(obj, 'name'):
                return {
                    'name': obj.name,
                    'url': None
                }
            elif hasattr(obj, 'title'):
                return {
                    'name': obj.title,
                    'url': None
                }
    
    # Default fallback
    return {
        'name': part.replace('_', ' ').title(),
        'url': None
    }
