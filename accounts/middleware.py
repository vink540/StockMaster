from django.utils.deprecation import MiddlewareMixin

class CompanyMiddleware(MiddlewareMixin):
    """Middleware para agregar company al request"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            if hasattr(request.user, 'company'):
                request.company = request.user.company
            else:
                from accounts.models import Company
                company = Company.objects.create(
                    owner=request.user,
                    name=f"Tienda de {request.user.username}"
                )
                request.company = company
        else:
            request.company = None