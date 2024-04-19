from django import template
import re

register = template.Library()

@register.filter
def remove_protocol_and_trailing_slash(url):
    url = re.sub(r'^https?://', '', url)
    return url.rstrip('/')