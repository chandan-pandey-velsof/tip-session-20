from django.http import JsonResponse
from tip_client.client import TipClient, TipApiError


def index(request):
    """Sample view: fetches the first page of cases from TIP and returns as JSON."""
    try:
        client = TipClient()
        data = client.get('/cases/')
        return JsonResponse({'status': 'ok', 'data': data})
    except TipApiError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=502)
