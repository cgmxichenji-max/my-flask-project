from functools import wraps

from flask import g, redirect, request, session, url_for

from .services import has_module_permission


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not getattr(g, 'current_user', None):
            return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not getattr(g, 'current_user', None):
            return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
        if not g.current_user.get('is_admin'):
            return '403 Forbidden', 403
        return view_func(*args, **kwargs)
    return wrapper


def module_required(module_key):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not getattr(g, 'current_user', None):
                return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
            if not has_module_permission(g.current_user, module_key):
                return '403 Forbidden', 403
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
