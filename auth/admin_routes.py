from flask import Blueprint, g, redirect, render_template, request, url_for

from .decorators import admin_required
from .services import (
    MODULE_LABELS,
    create_user,
    get_user_by_id,
    get_user_permissions,
    list_users,
    update_user,
)


admin_bp = Blueprint('auth_admin', __name__, url_prefix='/auth/admin')


@admin_bp.route('/users')
@admin_required
def users():
    return render_template('admin_users.html', users=list_users())


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create():
    error = ''
    selected_modules = []
    form_user = {'username': '', 'is_admin': 0}
    if request.method == 'POST':
        selected_modules = request.form.getlist('modules')
        form_user = {
            'username': request.form.get('username') or '',
            'is_admin': 1 if request.form.get('is_admin') else 0,
        }
        ok, error, user_id = create_user(
            username=form_user['username'],
            password=request.form.get('password') or '',
            is_admin=bool(form_user['is_admin']),
            module_keys=selected_modules,
            granted_by_user_id=g.current_user['id'],
        )
        if ok:
            return redirect(url_for('auth_admin.edit', user_id=user_id))

    return render_template(
        'admin_user_edit.html',
        mode='create',
        error=error,
        user=form_user,
        module_labels=MODULE_LABELS,
        selected_modules=selected_modules,
        is_self=False,
    )


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit(user_id):
    error = ''
    user = get_user_by_id(user_id)
    if not user:
        return '用户不存在', 404

    selected_modules = get_user_permissions(user_id)
    if request.method == 'POST':
        selected_modules = request.form.getlist('modules')
        is_self = user_id == g.current_user['id']
        ok, error = update_user(
            user_id=user_id,
            is_admin=True if is_self else bool(request.form.get('is_admin')),
            is_active=True if is_self else bool(request.form.get('is_active')),
            module_keys=selected_modules,
            current_user_id=g.current_user['id'],
            reset_password=request.form.get('reset_password') or '',
        )
        if ok:
            return redirect(url_for('auth_admin.users'))
        user = get_user_by_id(user_id)

    return render_template(
        'admin_user_edit.html',
        mode='edit',
        error=error,
        user=user,
        module_labels=MODULE_LABELS,
        selected_modules=selected_modules,
        is_self=user_id == g.current_user['id'],
    )
