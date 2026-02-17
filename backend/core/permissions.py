from django.core.exceptions import PermissionDenied

def in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

def require_group(group_name: str):
    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if in_group(request.user, group_name) or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to access this page.")
        return _wrapped
    return decorator
