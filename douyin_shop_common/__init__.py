"""抖音店铺蓝图工厂。

调用 create_douyin_blueprint() 得到完整注册好路由的 Flask Blueprint，
两个店铺（香娜露儿、幕莲蔓）各调用一次。
"""

from __future__ import annotations

import json
from pathlib import Path
import threading
import time
import uuid

from flask import Blueprint, current_app, jsonify, render_template, render_template_string, request, url_for

from auth.decorators import module_required
from common.download_utils import send_excel_download, send_zip_download
from common.upload_staging import finish_staged_upload, stage_uploaded_files

from .services import (
    ShopConfig,
    export_commission_detail_zip,
    export_commission_summary_zip,
    export_detail_source_commission_detail_zip,
    export_detail_source_commission_summary_zip,
    export_data_to_excel,
    export_store_self_sale_zip_file,
    get_data_status_rows,
    get_export_table_config,
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


def _build_export_field_config(config: ShopConfig) -> dict:
    """构建前端字段选择器用的配置（与 wechat_shop 格式一致）。"""
    result = {}
    for key, cfg in get_export_table_config(config).items():
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
    fund_flow_format: str = 'standard',
    order_format: str = 'standard',
    enable_detail_source_commission: bool = False,
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
        fund_flow_format=fund_flow_format,
        order_format=order_format,
    )
    export_field_config = _build_export_field_config(config)
    store_self_sale_jobs: dict[str, dict] = {}
    store_self_sale_lock = threading.Lock()

    def _run_store_self_sale_job(app, job_id: str, start_date: str, end_date: str) -> None:
        with store_self_sale_lock:
            job = store_self_sale_jobs[job_id]
            job['status'] = 'running'
        try:
            with app.app_context():
                name = export_store_self_sale_zip_file(job['output_path'], start_date, end_date, config)
            with store_self_sale_lock:
                job['status'] = 'complete'
                job['download_name'] = name
        except Exception as exc:
            Path(job['output_path']).unlink(missing_ok=True)
            with store_self_sale_lock:
                job['status'] = 'failed'
                job['message'] = str(exc)

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

    def _get_commission_export_date(field_name: str) -> str | None:
        aliases = {
            'start_date': ('start_date', 'dy_commission_start_date', 'date_start'),
            'end_date': ('end_date', 'dy_commission_end_date', 'date_end'),
        }
        for key in aliases[field_name]:
            value = (request.form.get(key) or '').strip()
            if value:
                return value
        return None

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
            order_accept_exts='.csv,.xlsx,.xls,.zip' if config.order_format == 'overseas' else '.csv,.xlsx,.xls',
            is_overseas_orders=(config.order_format == 'overseas'),
            enable_detail_source_commission=enable_detail_source_commission,
        )

    @bp.route('/import_orders', methods=['POST'])
    @module_required(module_key)
    def import_orders():
        files = request.files.getlist('files')
        allowed_exts = ('.csv', '.xlsx', '.xls', '.zip') if config.order_format == 'overseas' else ('.csv', '.xlsx', '.xls')
        return _do_import(files, import_orders_files,
                          f'{table_prefix}/orders', allowed_exts)

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
                start_date=_get_commission_export_date('start_date'),
                end_date=_get_commission_export_date('end_date'),
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
                start_date=_get_commission_export_date('start_date'),
                end_date=_get_commission_export_date('end_date'),
                nickname_query=request.form.get('nickname_query'),
                config=config,
            )
            return send_zip_download(output, filename)
        except Exception as exc:
            return jsonify({'success': False, 'message': str(exc)}), 400

    if enable_detail_source_commission:
        @bp.route('/export_detail_source_commission_summary', methods=['POST'])
        @module_required(module_key)
        def export_detail_source_commission_summary():
            try:
                output, filename = export_detail_source_commission_summary_zip(
                    start_date=_get_commission_export_date('start_date'),
                    end_date=_get_commission_export_date('end_date'),
                    nickname_query=request.form.get('nickname_query'),
                    exemption_mode=request.form.get('exemption_mode'),
                    config=config,
                )
                return send_zip_download(output, filename)
            except Exception as exc:
                return jsonify({'success': False, 'message': str(exc)}), 400

        @bp.route('/export_detail_source_commission_details', methods=['POST'])
        @module_required(module_key)
        def export_detail_source_commission_details():
            try:
                output, filename = export_detail_source_commission_detail_zip(
                    start_date=_get_commission_export_date('start_date'),
                    end_date=_get_commission_export_date('end_date'),
                    nickname_query=request.form.get('nickname_query'),
                    exemption_mode=request.form.get('exemption_mode'),
                    config=config,
                )
                return send_zip_download(output, filename)
            except Exception as exc:
                return jsonify({'success': False, 'message': str(exc)}), 400

    @bp.route('/export_store_self_sale', methods=['POST'])
    @module_required(module_key)
    def export_store_self_sale():
        start_date = _get_commission_export_date('start_date')
        end_date = _get_commission_export_date('end_date')
        if not start_date or not end_date:
            return jsonify({'success': False, 'message': '请选择开始日期和结束日期'}), 400
        with store_self_sale_lock:
            if any(job['status'] in {'queued', 'running'} for job in store_self_sale_jobs.values()):
                return jsonify({'success': False, 'message': '已有店铺自卖任务正在生成，请等待完成'}), 409
            job_id = uuid.uuid4().hex
            output_dir = Path(current_app.config['DATABASE_PATH']).resolve().parent / 'douyin_store_self_sale_jobs'
            output_dir.mkdir(parents=True, exist_ok=True)
            cutoff = time.time() - 24 * 60 * 60
            for stale_file in output_dir.glob('*.zip'):
                if stale_file.stat().st_mtime < cutoff:
                    stale_file.unlink(missing_ok=True)
            store_self_sale_jobs[job_id] = {
                'status': 'queued', 'message': '', 'download_name': '',
                'output_path': str(output_dir / f'{shop_name}_{job_id}.zip'),
            }
        worker = threading.Thread(
            target=_run_store_self_sale_job,
            args=(current_app._get_current_object(), job_id, start_date, end_date),
            daemon=True,
        )
        worker.start()
        return jsonify({
            'success': True, 'job_id': job_id,
            'status_url': url_for(f'{bp.name}.store_self_sale_job_status', job_id=job_id),
        }), 202

    @bp.route('/export_store_self_sale/jobs/<job_id>')
    @module_required(module_key)
    def store_self_sale_job_status(job_id: str):
        with store_self_sale_lock:
            job = store_self_sale_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'message': '任务不存在或已过期'}), 404
            return jsonify({
                'success': True, 'status': job['status'], 'message': job['message'],
                'download_name': job['download_name'],
                'download_url': url_for(f'{bp.name}.store_self_sale_job_download', job_id=job_id),
            })

    @bp.route('/export_store_self_sale/jobs/<job_id>/download')
    @module_required(module_key)
    def store_self_sale_job_download(job_id: str):
        with store_self_sale_lock:
            job = store_self_sale_jobs.get(job_id)
            if not job or job['status'] != 'complete':
                return jsonify({'success': False, 'message': '文件尚未生成完成'}), 409
            path, name = job['output_path'], job['download_name']
        if not Path(path).is_file():
            return jsonify({'success': False, 'message': '导出文件不存在或已清理'}), 404
        return send_zip_download(path, name)

    return bp
