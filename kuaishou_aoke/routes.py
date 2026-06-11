import json
from datetime import datetime

from flask import jsonify, render_template, render_template_string, request

from auth.decorators import module_required
from common.download_utils import send_excel_download, send_zip_download
from common.upload_staging import finish_staged_upload, stage_uploaded_files

from . import kuaishou_aoke_bp
from .services import (
    export_commission_detail_zip,
    export_commission_summary_zip,
    export_data_to_excel,
    get_data_status_rows,
    import_after_sales_files,
    import_fund_flow_files,
    import_orders_files,
)
from .table_schemas import EXPORT_TABLE_CONFIG


STATUS_ROWS_TEMPLATE = '''
{% if data_status_rows %}
    {% for row in data_status_rows %}
    <tr>
        <td>{{ row.table_name or '' }}</td>
        <td>{{ row.record_count or 0 }}</td>
        <td>{{ row.min_date or '' }}</td>
        <td>{{ row.max_date or '' }}</td>
        <td>{{ row.last_import_time or '' }}</td>
    </tr>
    {% endfor %}
{% else %}
    <tr><td colspan="5">暂无数据</td></tr>
{% endif %}
'''


def _parse_datetime_value(value):
    if isinstance(value, datetime):
        return value
    text = str(value or '').strip()
    if not text:
        return None
    for fmt in (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d',
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _format_datetime_display(value):
    dt = _parse_datetime_value(value)
    if dt is None:
        return '' if value is None else str(value)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _format_status_rows(rows):
    for row in rows:
        row['min_date'] = _format_datetime_display(row.get('min_date'))
        row['max_date'] = _format_datetime_display(row.get('max_date'))
        row['last_import_time'] = _format_datetime_display(row.get('last_import_time'))
    return rows


def _build_export_field_config():
    result = {}
    for table_key, cfg in EXPORT_TABLE_CONFIG.items():
        reverse_mapping = {english: chinese for chinese, english in cfg['column_mapping'].items()}
        result[table_key] = {
            'label': cfg['label'],
            'fields': [
                {
                    'value': field_name,
                    'label': reverse_mapping.get(field_name, field_name),
                    'checked': index < 6,
                }
                for index, field_name in enumerate(cfg['column_types'].keys())
            ],
        }
    return result


def _attach_status_rows(result: dict) -> dict:
    rows = _format_status_rows(get_data_status_rows())
    result['data_status_rows'] = rows
    result['status_rows_html'] = render_template_string(
        STATUS_ROWS_TEMPLATE,
        data_status_rows=rows,
    )
    return result


def _attach_status_rows_safely(result: dict) -> dict:
    try:
        return _attach_status_rows(result)
    except Exception as exc:
        result['status_rows_error'] = str(exc)
        result['message'] = (
            f"{result.get('message', '')}\n"
            f"提示：导入已完成，但刷新页面数据状态失败，请刷新页面确认。错误：{exc}"
        ).strip()
        return result


def _do_import(files, import_key, import_fn):
    if not files:
        return jsonify({'success': False, 'message': '未接收到任何文件'}), 400

    staged_batch = None
    try:
        staged_batch = stage_uploaded_files(files, import_key, ('.xlsx', '.xls'))
        result = import_fn(staged_batch.files)
        finish_staged_upload(
            staged_batch,
            'success' if result.get('success') else 'failed',
            result.get('message', ''),
        )
        staged_batch = None
    except ValueError as exc:
        finish_staged_upload(staged_batch, 'failed', str(exc))
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:
        finish_staged_upload(staged_batch, 'failed', str(exc))
        return jsonify({'success': False, 'message': f'导入失败：{exc}'}), 400

    if not result.get('success'):
        return jsonify(result), 400
    result = _attach_status_rows_safely(result)
    return jsonify(result)


@kuaishou_aoke_bp.route('/', strict_slashes=False)
@module_required('kuaishou_aoke')
def index():
    data_status_rows = _format_status_rows(get_data_status_rows())
    export_date_ranges = {}
    for row in data_status_rows:
        table_key = row.get('table_key')
        if not table_key:
            continue
        export_date_ranges[table_key] = {
            'start_date': (row.get('min_date') or '')[:10].replace('/', '-'),
            'end_date': (row.get('max_date') or '')[:10].replace('/', '-'),
        }

    return render_template(
        'kuaishou_aoke.html',
        data_status_rows=data_status_rows,
        export_field_config_json=json.dumps(_build_export_field_config(), ensure_ascii=False),
        export_date_ranges_json=json.dumps(export_date_ranges, ensure_ascii=False),
    )


@kuaishou_aoke_bp.route('/import_orders', methods=['POST'])
@module_required('kuaishou_aoke')
def import_orders():
    return _do_import(request.files.getlist('files'), 'kuaishou_aoke/orders', import_orders_files)


@kuaishou_aoke_bp.route('/import_fund_flow', methods=['POST'])
@module_required('kuaishou_aoke')
def import_fund_flow():
    return _do_import(request.files.getlist('files'), 'kuaishou_aoke/fund_flows', import_fund_flow_files)


@kuaishou_aoke_bp.route('/import_after_sales', methods=['POST'])
@module_required('kuaishou_aoke')
def import_after_sales():
    return _do_import(request.files.getlist('files'), 'kuaishou_aoke/aftersales', import_after_sales_files)


@kuaishou_aoke_bp.route('/export_data', methods=['POST'])
@module_required('kuaishou_aoke')
def export_data():
    try:
        raw_filters = request.form.get('filters')
        try:
            filter_conditions = json.loads(raw_filters) if raw_filters else []
        except Exception:
            filter_conditions = []

        output, download_name = export_data_to_excel(
            table_key=request.form.get('table_key'),
            start_time=request.form.get('start_time'),
            end_time=request.form.get('end_time'),
            selected_fields=request.form.getlist('fields'),
            filter_conditions=filter_conditions,
        )
        return send_excel_download(output, download_name)
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@kuaishou_aoke_bp.route('/export_commission_summary', methods=['POST'])
@module_required('kuaishou_aoke')
def export_commission_summary():
    try:
        output, download_name = export_commission_summary_zip(
            start_date=request.form.get('start_date'),
            end_date=request.form.get('end_date'),
            nickname_query=request.form.get('nickname_query'),
        )
        return send_zip_download(output, download_name)
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@kuaishou_aoke_bp.route('/export_commission_details', methods=['POST'])
@module_required('kuaishou_aoke')
def export_commission_details():
    try:
        output, download_name = export_commission_detail_zip(
            start_date=request.form.get('start_date'),
            end_date=request.form.get('end_date'),
            nickname_query=request.form.get('nickname_query'),
        )
        return send_zip_download(output, download_name)
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400
