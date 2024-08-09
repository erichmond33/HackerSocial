from django import template
from django.utils import timezone
from django.utils.timesince import timesince
from django.contrib.humanize.templatetags.humanize import naturaltime

register = template.Library()

@register.filter
def smart_date(value):
    now = timezone.now()
    diff = now - value
    
    if diff.days < 1:
        return naturaltime(value)
    elif value.year == now.year:
        return value.strftime("%b %d")
    else:
        return value.strftime("%b %d, %Y")