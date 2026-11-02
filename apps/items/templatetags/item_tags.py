"""Template tags and filters for the items application."""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Preserve existing GET query parameters while updating specific ones (e.g., page).
    
    Usage:
        <a href="?{% query_transform page=page_obj.next_page_number %}">Next</a>
    """
    request = context.get("request")
    if not request:
        return ""
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None and value != "":
            updated[key] = value
        else:
            updated.pop(key, None)
    return updated.urlencode()
