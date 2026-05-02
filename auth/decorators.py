from functools import wraps

from flask import g, jsonify, redirect, request, session, url_for

from .services import has_module_permission


def _wants_json_response():
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
    )


def _auth_required_response():
    if _wants_json_response():
        return jsonify({
            'success': False,
            'message': '登录状态已失效，请刷新页面后重新登录。',
        }), 401
    return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))


def _forbidden_response():
    if _wants_json_response():
        return jsonify({
            'success': False,
            'message': '当前用户没有访问该模块的权限。',
        }), 403
    return '403 Forbidden', 403


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not getattr(g, 'current_user', None):
            return _auth_required_response()
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not getattr(g, 'current_user', None):
            return _auth_required_response()
        if not g.current_user.get('is_admin'):
            return _forbidden_response()
        return view_func(*args, **kwargs)
    return wrapper


def module_required(module_key):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not getattr(g, 'current_user', None):
                return _auth_required_response()
            if not has_module_permission(g.current_user, module_key):
                return _forbidden_response()
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
