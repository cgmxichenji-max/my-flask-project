from flask import Blueprint, g, redirect, render_template, request, session, url_for

from .decorators import login_required
from .services import authenticate_user, change_user_password


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    next_url = request.values.get('next') or url_for('index')
    if getattr(g, 'current_user', None):
        return redirect(next_url)

    if request.method == 'POST':
        username = request.form.get('username') or ''
        password = request.form.get('password') or ''
        user = authenticate_user(username, password)
        if user:
            session.clear()
            session['user_id'] = user['id']
            return redirect(next_url)
        error = '用户名或密码错误，或用户已被禁用'

    return render_template('login.html', error=error, next_url=next_url)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    error = ''
    message = ''
    if request.method == 'POST':
        old_password = request.form.get('old_password') or ''
        new_password = request.form.get('new_password') or ''
        ok, error = change_user_password(g.current_user['id'], old_password, new_password)
        if ok:
            message = '密码修改成功'
            error = ''
    return render_template('change_password.html', error=error, message=message)
