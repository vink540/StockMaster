from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class CompanyMiddleware(MiddlewareMixin):
    """Middleware para agregar company al request"""
    
    def process_request(self, request):
        try:
            if request.user.is_authenticated:
                # Intentar obtener la empresa
                if hasattr(request.user, 'company'):
                    request.company = request.user.company
                else:
                    # Si no tiene empresa, asignar None
                    # NO crear aquí - debe crearse en la vista de registro
                    request.company = None
                    logger.warning(f"Usuario {request.user.username} no tiene empresa asignada")
            else:
                request.company = None
        except Exception as e:
            logger.error(f"Error en CompanyMiddleware: {str(e)}", exc_info=True)
            request.company = None
        
        return None