import os
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_GET

@require_GET
def bootstrap_admin(request):
    token = request.GET.get("token", "")
    if not token or token != os.getenv("BOOTSTRAP_TOKEN"):
        return HttpResponseForbidden("Forbidden")

    User = get_user_model()
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")

    if not password:
        return HttpResponse("BOOTSTRAP_ADMIN_PASSWORD not set", status=500)

    if User.objects.filter(username=username).exists():
        return HttpResponse("Admin already exists")

    user = User.objects.create_superuser(username=username, email=email, password=password)
    return HttpResponse(f"Created superuser: {user.username}")