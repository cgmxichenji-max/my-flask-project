from flask import jsonify, render_template, request

from auth.decorators import login_required, module_required

from . import reminder_center_bp
from .services import (
    create_monthly_reminder,
    delete_monthly_reminder,
    get_active_reminders,
    get_settings,
    update_exemption_setting,
    update_global_setting,
    update_monthly_reminder,
)


def json_error(message, status_code=400):
    return jsonify({'success': False, 'message': message}), status_code


@reminder_center_bp.route('/', strict_slashes=False)
@module_required('reminder_center')
def index():
    return render_template('reminder_center.html')


@reminder_center_bp.route('/api/settings')
@module_required('reminder_center')
def api_settings():
    return jsonify({'success': True, 'settings': get_settings()})


@reminder_center_bp.route('/api/global', methods=['POST'])
@module_required('reminder_center')
def api_update_global():
    try:
        update_global_setting(request.get_json(silent=True) or {})
        return jsonify({'success': True, 'message': '广播设置已保存'})
    except ValueError as exc:
        return json_error(str(exc))


@reminder_center_bp.route('/api/exemption', methods=['POST'])
@module_required('reminder_center')
def api_update_exemption():
    try:
        update_exemption_setting(request.get_json(silent=True) or {})
        return jsonify({'success': True, 'message': '豁免到期提醒已保存'})
    except ValueError as exc:
        return json_error(str(exc))


@reminder_center_bp.route('/api/monthly', methods=['POST'])
@module_required('reminder_center')
def api_create_monthly():
    try:
        create_monthly_reminder(request.get_json(silent=True) or {})
        return jsonify({'success': True, 'message': '月度提醒已新增'})
    except ValueError as exc:
        return json_error(str(exc))


@reminder_center_bp.route('/api/monthly/<int:record_id>', methods=['POST'])
@module_required('reminder_center')
def api_update_monthly(record_id):
    try:
        update_monthly_reminder(record_id, request.get_json(silent=True) or {})
        return jsonify({'success': True, 'message': '月度提醒已保存'})
    except ValueError as exc:
        return json_error(str(exc))


@reminder_center_bp.route('/api/monthly/<int:record_id>/delete', methods=['POST'])
@module_required('reminder_center')
def api_delete_monthly(record_id):
    try:
        delete_monthly_reminder(record_id)
        return jsonify({'success': True, 'message': '月度提醒已删除'})
    except ValueError as exc:
        return json_error(str(exc))


@reminder_center_bp.route('/api/active')
@login_required
def api_active():
    return jsonify({'success': True, 'reminders': get_active_reminders()})
