from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def home_view(request):
    """Return a simple status payload for the backend root URL."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "Axon backend",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )
