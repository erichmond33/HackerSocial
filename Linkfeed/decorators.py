from django.http import HttpResponseForbidden

def prevent_iframe_embedding(view_func):
    def wrapper(*args, **kwargs):
        response = view_func(*args, **kwargs)
        response['X-Frame-Options'] = 'DENY'
        return response
    return wrapper


from django.conf import settings
from .models import AllowedDomain  # Adjust if your model path is different

class CSPDecorator:
   def __init__(self, view_func):
       self.view_func = view_func

   def __call__(self, request, *args, **kwargs):
       allowed_domains = self.get_allowed_domains(request)
       csp_directive = "frame-ancestors 'self' {}".format(' '.join(allowed_domains))

       response = self.view_func(request, *args, **kwargs)
       response['Content-Security-Policy'] = csp_directive
       return response

   @classmethod
   def get_allowed_domains(cls, request):
       domains = []
       if request.user.is_authenticated:
           domains = list(AllowedDomain.objects.all().values_list('domain', flat=True))
       else:
           domains = list(AllowedDomain.objects.all().values_list('domain', flat=True))

       domains.append(settings.EXPLICIT_TRUSTED_DOMAIN) 
       return domains 
