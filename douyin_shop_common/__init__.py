"""抖音店铺蓝图工厂。

调用 create_douyin_blueprint() 得到完整注册好路由的 Flask Blueprint，
两个店铺（香娜露儿、幕莲蔓）各调用一次。
"""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, render_template, render_template_string, request

from auth.decorators import module_required
from common.download_utils import send_excel_download, send_zip_download
from common.upload_staging import finish_staged_upload, stage_uploaded_files

from .services import (
    ShopConfig,
    export_commission_detail_zip,
    export_commission_summary_zip,
    export_data_to_excel,
    get_data_status_rows,
)
from .services import (
    import_orders_files,
    import_fund_flow_files,
    import_commission_files,
    import_merchant_files,
)
from .table_schemas import (
    ORDERS_COLUMN_MAPPING, ORDERS_COLUMN_TYPES,
    FUND_FLOW_COLUMN_MAPPING, FUND_FLOW_COLUMN_TYPES,
    COMMISSION_COLUMN_MAPPING, COMMISSION_COLUMN_TYPES,
    MERCHANT_COLUMN_MAPPING, MERCHANT_COLUMN_TYPES,
    EXPORT_TABLE_CONFIG,
)

_STATUS_ROWS_TEMPLATE = '''
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


def _build_export_field_config() -> dict:
    """构建前端字段选择器用的配置（与 wechat_shop 格式一致）。"""
    result = {}
    for key, cfg in EXPORT_TABLE_CONFIG.items():
        col_mapping = cfg['column_mapping']
        col_types = cfg['column_types']
        rev_map = {v: k for k, v in col_mapping.items()}
        result[key] = {
            'label': cfg['label'],
            'fields': [
                {
                    'value': field_name,
                    'label': rev_map.get(field_name, field_name),
                    'checked': idx < 6,
                }
                for idx, field_name in enumerate(col_types.keys())
            ],
        }
    return result


def create_douyin_blueprint(
    shop_name: str,
    display_name: str,
    module_key: str,
    table_prefix: str,
) -> Blueprint:
    """
    创建一个完整的抖音店铺蓝图。

    参数:
        shop_name    蓝图名（须唯一），如 'douyin_chantelle'
        display_name 页面显示名，如 '香娜露儿（抖音）'
        module_key   权限 key，如 'douyin_shop_chantelle'
        table_prefix 数据库表名前缀，如 'dy_chantelle'
    """
    bp = Blueprint(shop_name, __name__, template_folder='../templates')
    config = ShopConfig(
        shop_name=shop_name,
        display_name=display_name,
        module_key=module_key,
        table_prefix=table_prefix,
    )
    export_field_config = _build_export_field_config()

    # ---------- 辅助函数（闭包捕获 config） ----------

    def _attach_status(result: dict) -> dict:
        try:
            rows = get_data_status_rows(config)
            result['data_status_rows'] = rows
            result['status_rows_html'] = render_template_string(
                _STATUS_ROWS_TEMPLATE, data_status_rows=rows
            )
        except Exception as exc:
            result['status_rows_error'] = str(exc)
        return result

    def _do_import(files, import_fn, import_key, allowed_exts):
        if not files:
            return jsonify({'success': False, 'message': '未接收到任何文件'}), 400
        staged = None
        try:
            staged = stage_uploaded_files(files, import_key, allowed_exts)
            result = import_fn(staged.files, config)
            finish_staged_upload(staged, 'success' if result.get('success') else 'failed',
                                 result.get('message', ''))
            staged = None
        except ValueError as exc:
            finish_staged_upload(staged, 'failed', str(exc))
            return jsonify({'success': False, 'message': str(exc)}), 400
        except Exception as exc:
            finish_staged_upload(staged, 'failed', str(exc))
            return jsonify({'success': False, 'message': f'导入失败：{exc}'}), 400

        if not result.get('success'):
            return jsonify(result), 400
        result = _attach_status(result)
        return jsonify(result)

    # ---------- 路由 ----------

    @bp.route('/', strict_slashes=False)
    @module_required(module_key)
    def index():
        rows = get_data_status_rows(config)
        export_date_ranges: dict = {}
        for row in rows:
            key = row.get('table_key')
            if key:
                export_date_ranges[key] = {
                    'start_date': (row.get('min_date') or '')[:10].replace('/', '-'),
                    'end_date': (row.get('max_date') or '')[:10].replace('/', '-'),
                }
        return render_template(
            'douyin_shop.html',
            shop_display_name=display_name,
            url_prefix=f'/{table_prefix.replace("_", "/", 1)}',
            bp_name=shop_name,
            data_status_rows=rows,
            export_field_config_json=json.dumps(export_field_config, ensure_ascii=False),
            export_date_ranges_json=json.dumps(export_date_ranges, ensure_ascii=False),
        )

    @bp.route('/import_orders', methods=['POST'])
    @module_required(module_key)
    def import_orders():
        files = request.files.getlist('files')
        return _do_import(files, import_orders_files,
                          f'{table_prefix}/orders', ('.csv', '.xlsx', '.xls'))

    @bp.route('/import_fund_flow', methods=['POST'])
    @module_required(module_key)
    def import_fund_flow():
        files = request.files.getlist('files')
        return _do_import(files, import_fund_flow_files,
                          f'{table_prefix}/fund_flow', ('.csv', '.xlsx', '.xls'))

    @bp.route('/import_commission', methods=['POST'])
    @module_required(module_key)
    def import_commission():
        files = request.files.getlist('files')
        return _do_import(files, import_commission_files,
                          f'{table_prefix}/commission', ('.xlsx', '.xls'))

    @bp.route('/import_merchant', methods=['POST'])
    @module_required(module_key)
    def import_merchant():
        files = request.files.getlist('files')
        return _do_import(files, import_merchant_files,
                          f'{table_prefix}/merchant', ('.xlsx', '.xls'))

    @bp.route('/export_data', methods=['POST'])
    @module_required(module_key)
    def export_data():
        try:
            table_key = request.form.get('table_key')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            selected_fields = request.form.getlist('fields')
            raw_filters = request.form.get('filters')
            try:
                filter_conditions = json.loads(raw_filters) if raw_filters else []
            except Exception:
                filter_conditions = []

            output, filename = export_data_to_excel(
                table_key=table_key,
                start_time=start_time,
                end_time=end_time,
                selected_fields=selected_fields,
                filter_conditions=filter_conditions,
                config=config,
            )
            return send_excel_download(output, filename)
        except Exception as exc:
            return jsonify({'success': False, 'message': str(exc)}), 400

    @bp.route('/export_commission_summary', methods=['POST'])
    @module_required(module_key)
    def export_commission_summary():
        try:
            output, filename = export_commission_summary_zip(
                start_date=request.form.get('start_date'),
                end_date=request.form.get('end_date'),
                nickname_query=request.form.get('nickname_query'),
                config=config,
            )
            return send_zip_download(output, filename)
        except Exception as exc:
            return jsonify({'success': False, 'message': str(exc)}), 400

    @bp.route('/export_commission_details', methods=['POST'])
    @module_required(module_key)
    def export_commission_details():
        try:
            output, filename = export_commission_detail_zip(
                start_date=request.form.get('start_date'),
                end_date=request.form.get('end_date'),
                nickname_query=request.form.get('nickname_query'),
                config=config,
            )
            return send_zip_download(output, filename)
        except Exception as exc:
            return jsonify({'success': False, 'message': str(exc)}), 400

    return bp
