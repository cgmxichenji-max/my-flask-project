from flask import jsonify, render_template, request

from auth.decorators import module_required

from . import exemption_management_bp
from .services import (
    BRANDS,
    STATUSES,
    create_exemption,
    delete_exemption,
    ensure_tables,
    list_exemptions,
    stop_exemption,
    update_exemption,
)


def json_error(message, status_code=400):
    return jsonify({'success': False, 'message': message}), status_code


@exemption_management_bp.route('/', strict_slashes=False)
@module_required('exemption_management')
def index():
    ensure_tables()
    return render_template(
        'exemption_management.html',
        brands=BRANDS,
        statuses=STATUSES,
    )


@exemption_management_bp.route('/api/list')
@module_required('exemption_management')
def api_list():
    try:
        rows = list_exemptions(request.args)
        return jsonify({'success': True, 'rows': rows, 'total': len(rows)})
    except ValueError as exc:
        return json_error(str(exc))


@exemption_management_bp.route('/api/create', methods=['POST'])
@module_required('exemption_management')
def api_create():
    try:
        row = create_exemption(request.get_json(silent=True) or {})
        return jsonify({'success': True, 'row': row, 'message': '新增成功'})
    except ValueError as exc:
        return json_error(str(exc))


@exemption_management_bp.route('/api/update/<int:record_id>', methods=['POST'])
@module_required('exemption_management')
def api_update(record_id):
    try:
        row = update_exemption(record_id, request.get_json(silent=True) or {})
        return jsonify({'success': True, 'row': row, 'message': '保存成功'})
    except ValueError as exc:
        return json_error(str(exc))


@exemption_management_bp.route('/api/stop/<int:record_id>', methods=['POST'])
@module_required('exemption_management')
def api_stop(record_id):
    data = request.get_json(silent=True) or {}
    try:
        row = stop_exemption(record_id, data.get('end_date'))
        return jsonify({'success': True, 'row': row, 'message': '已停止'})
    except ValueError as exc:
        return json_error(str(exc))


@exemption_management_bp.route('/api/delete/<int:record_id>', methods=['POST'])
@module_required('exemption_management')
def api_delete(record_id):
    try:
        delete_exemption(record_id)
        return jsonify({'success': True, 'message': '删除成功'})
    except ValueError as exc:
        return json_error(str(exc))
