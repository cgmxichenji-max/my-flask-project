from datetime import datetime
import json
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from flask import current_app, jsonify, render_template, render_template_string, request

from auth.decorators import module_required
from common.download_utils import send_zip_download
from common.upload_staging import (
    ImportAlreadyRunningError,
    finish_staged_upload,
    import_lock,
    stage_uploaded_files,
)

from .table_schemas import (
    ORDER_COLUMN_MAPPING,
    ORDER_COLUMN_TYPES,
    FUND_FLOW_COLUMN_MAPPING,
    FUND_FLOW_COLUMN_TYPES,
    AFTER_SALES_COLUMN_MAPPING,
    AFTER_SALES_COLUMN_TYPES,
)

from . import wechat_shop_bp
from .services import (
    read_after_sales_excel_files,
    read_fund_flow_excel_files,
    read_order_excel_files,
    export_commission_detail_zip,
    export_commission_summary_zip,
    export_data_to_zip,
    export_store_self_sale_zip_file,
)


DATA_STATUS_TABLE_NAME = 'wechat_shop_data_status'
STORE_SELF_SALE_JOB_TTL_SECONDS = 24 * 60 * 60
_store_self_sale_jobs: dict[str, dict] = {}
_store_self_sale_jobs_lock = threading.Lock()


def _cleanup_store_self_sale_jobs() -> None:
    cutoff = time.time() - STORE_SELF_SALE_JOB_TTL_SECONDS
    stale_paths: list[str] = []
    with _store_self_sale_jobs_lock:
        stale_job_ids = [
            job_id
            for job_id, job in _store_self_sale_jobs.items()
            if job.get('updated_at', 0) < cutoff
        ]
        for job_id in stale_job_ids:
            job = _store_self_sale_jobs.pop(job_id)
            if job.get('output_path'):
                stale_paths.append(job['output_path'])

    for output_path in stale_paths:
        Path(output_path).unlink(missing_ok=True)


def _run_store_self_sale_export_job(app, job_id: str, start_date: str, end_date: str) -> None:
    with _store_self_sale_jobs_lock:
        job = _store_self_sale_jobs[job_id]
        job['status'] = 'running'
        job['updated_at'] = time.time()
        output_path = job['output_path']

    try:
        with app.app_context():
            download_name = export_store_self_sale_zip_file(output_path, start_date, end_date)
        with _store_self_sale_jobs_lock:
            job = _store_self_sale_jobs[job_id]
            job['status'] = 'complete'
            job['download_name'] = download_name
            job['updated_at'] = time.time()
    except Exception as exc:
        Path(output_path).unlink(missing_ok=True)
        with _store_self_sale_jobs_lock:
            job = _store_self_sale_jobs[job_id]
            job['status'] = 'failed'
            job['message'] = str(exc)
            job['updated_at'] = time.time()

EXPORT_FIELD_CONFIG = {
    'orders': {
        'label': '订单表',
        'fields': [
            {
                'value': field_name,
                'label': next((cn for cn, en in ORDER_COLUMN_MAPPING.items() if en == field_name), field_name),
                'checked': index < 6,
            }
            for index, field_name in enumerate(ORDER_COLUMN_TYPES.keys())
        ],
    },
    'fund_flows': {
        'label': '资金流水表',
        'fields': [
            {
                'value': field_name,
                'label': next((cn for cn, en in FUND_FLOW_COLUMN_MAPPING.items() if en == field_name), field_name),
                'checked': index < 6,
            }
            for index, field_name in enumerate(FUND_FLOW_COLUMN_TYPES.keys())
        ],
    },
    'aftersales': {
        'label': '售后表',
        'fields': [
            {
                'value': field_name,
                'label': next((cn for cn, en in AFTER_SALES_COLUMN_MAPPING.items() if en == field_name), field_name),
                'checked': index < 6,
            }
            for index, field_name in enumerate(AFTER_SALES_COLUMN_TYPES.keys())
        ],
    },
}


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
    <tr>
        <td colspan="5">暂无数据</td>
    </tr>
{% endif %}
'''


def _parse_datetime_value(value):
    """尽量把不同格式的日期时间字符串解析为 datetime 对象。"""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None



def _format_datetime_display(value):
    """把日期时间统一格式化为页面展示字符串。"""
    dt = _parse_datetime_value(value)
    if dt is None:
        return '' if value is None else str(value)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _get_data_status_rows() -> list[dict]:
    """读取当前数据状态表，用于页面展示。"""
    db_path = current_app.config['DATABASE_PATH']

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (DATA_STATUS_TABLE_NAME,),
        )
        table_exists = cursor.fetchone()
        if not table_exists:
            return []

        cursor.execute(
            f'''
            SELECT table_key, table_name, record_count, min_date, max_date, last_import_time
            FROM {DATA_STATUS_TABLE_NAME}
            ORDER BY CASE table_key
                WHEN 'orders' THEN 1
                WHEN 'fund_flows' THEN 2
                WHEN 'aftersales' THEN 3
                ELSE 99
            END, id
            '''
        )
        rows = [dict(row) for row in cursor.fetchall()]

        for row in rows:
            row['min_date'] = _format_datetime_display(row.get('min_date'))
            row['max_date'] = _format_datetime_display(row.get('max_date'))
            row['last_import_time'] = _format_datetime_display(row.get('last_import_time'))

        return rows


def _attach_status_rows(result: dict) -> dict:
    """给导入接口返回结果补充最新状态表数据和 HTML。"""
    data_status_rows = _get_data_status_rows()
    result['data_status_rows'] = data_status_rows
    result['status_rows_html'] = render_template_string(
        STATUS_ROWS_TEMPLATE,
        data_status_rows=data_status_rows,
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


@wechat_shop_bp.route('/', strict_slashes=False)
@module_required('wechat_shop')
def index():
    data_status_rows = _get_data_status_rows()
    export_field_config_json = json.dumps(EXPORT_FIELD_CONFIG, ensure_ascii=False)
    export_date_ranges = {}
    for row in data_status_rows:
        table_key = row.get('table_key')
        min_date = (row.get('min_date') or '')[:10].replace('/', '-')
        max_date = (row.get('max_date') or '')[:10].replace('/', '-')
        if table_key:
            export_date_ranges[table_key] = {
                'start_date': min_date,
                'end_date': max_date,
            }
    export_date_ranges_json = json.dumps(export_date_ranges, ensure_ascii=False)
    return render_template(
        'wechat_shop.html',
        data_status_rows=data_status_rows,
        export_field_config_json=export_field_config_json,
        export_date_ranges_json=export_date_ranges_json,
    )


@wechat_shop_bp.route('/import_orders', methods=['POST'])
@module_required('wechat_shop')
def import_orders():
    """
    接收前端上传的多个订单文件（Excel），
    调用 service 层进行读取、校验、写入。
    """
    files = request.files.getlist('files')

    if not files:
        return jsonify({
            'success': False,
            'message': '未接收到任何文件'
        }), 400

    staged_batch = None
    try:
        staged_batch = stage_uploaded_files(files, 'wechat_shop/orders', ('.xlsx', '.xls'))
        upload_batch_id = staged_batch.batch_id
        result = read_order_excel_files(staged_batch.files)
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

    result['upload_batch_id'] = upload_batch_id
    if not result.get('success'):
        return jsonify(result), 400

    result = _attach_status_rows_safely(result)
    return jsonify(result)


@wechat_shop_bp.route('/import_fund_flow', methods=['POST'])
@module_required('wechat_shop')
def import_fund_flow():
    """
    接收前端上传的资金流水 Excel 文件，
    调用 service 层进行读取、校验、写入。
    """
    files = request.files.getlist('files')

    if not files:
        return jsonify({
            'success': False,
            'message': '未接收到任何文件'
        }), 400

    staged_batch = None
    try:
        with import_lock('wechat_shop/fund_flows'):
            staged_batch = stage_uploaded_files(files, 'wechat_shop/fund_flows', ('.xlsx', '.xls'))
            upload_batch_id = staged_batch.batch_id
            result = read_fund_flow_excel_files(staged_batch.files)
            finish_staged_upload(
                staged_batch,
                'success' if result.get('success') else 'failed',
                result.get('message', ''),
            )
            staged_batch = None
    except ImportAlreadyRunningError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 409
    except ValueError as exc:
        finish_staged_upload(staged_batch, 'failed', str(exc))
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception as exc:
        finish_staged_upload(staged_batch, 'failed', str(exc))
        return jsonify({'success': False, 'message': f'导入失败：{exc}'}), 400

    result['upload_batch_id'] = upload_batch_id
    if not result.get('success'):
        return jsonify(result), 400

    result = _attach_status_rows_safely(result)
    return jsonify(result)


@wechat_shop_bp.route('/import_after_sales', methods=['POST'])
@module_required('wechat_shop')
def import_after_sales():
    """
    接收前端上传的售后 Excel 文件，
    调用 service 层进行读取、校验、写入。
    """
    files = request.files.getlist('files')

    if not files:
        return jsonify({
            'success': False,
            'message': '未接收到任何文件'
        }), 400

    staged_batch = None
    try:
        staged_batch = stage_uploaded_files(files, 'wechat_shop/aftersales', ('.xlsx', '.xls'))
        upload_batch_id = staged_batch.batch_id
        result = read_after_sales_excel_files(staged_batch.files)
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

    result['upload_batch_id'] = upload_batch_id
    if not result.get('success'):
        return jsonify(result), 400

    result = _attach_status_rows_safely(result)
    return jsonify(result)


# 新增导出数据接口
@wechat_shop_bp.route('/export_data', methods=['POST'])
@module_required('wechat_shop')
def export_data():
    """原始数据导出为 ZIP，内部 Excel 按行数切割。"""
    try:
        table_key = request.form.get('table_key')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        selected_fields = request.form.getlist('fields')
        filter_conditions = request.form.get('filters')
        if filter_conditions:
            try:
                filter_conditions = json.loads(filter_conditions)
            except Exception:
                filter_conditions = []
        else:
            filter_conditions = []

        output, download_name = export_data_to_zip(
            table_key=table_key,
            start_time=start_time,
            end_time=end_time,
            selected_fields=selected_fields,
            filter_conditions=filter_conditions,
        )
        return send_zip_download(output, download_name)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@wechat_shop_bp.route('/export_commission_summary', methods=['POST'])
@module_required('wechat_shop')
def export_commission_summary():
    """导出佣金汇总 ZIP：包含 VBA 风格汇总和发票应开金额导入格式。"""
    try:
        output, download_name = export_commission_summary_zip(
            start_date=request.form.get('start_date'),
            end_date=request.form.get('end_date'),
            nickname_query=request.form.get('nickname_query'),
        )
        return send_zip_download(output, download_name)
    except Exception as exc:
        return jsonify({
            'success': False,
            'message': str(exc),
        }), 400


@wechat_shop_bp.route('/export_commission_details', methods=['POST'])
@module_required('wechat_shop')
def export_commission_details():
    """按带货账号昵称拆分导出主播/团长佣金明细 ZIP。"""
    try:
        output, download_name = export_commission_detail_zip(
            start_date=request.form.get('start_date'),
            end_date=request.form.get('end_date'),
            nickname_query=request.form.get('nickname_query'),
        )
        return send_zip_download(output, download_name)
    except Exception as exc:
        return jsonify({
            'success': False,
            'message': str(exc),
        }), 400


@wechat_shop_bp.route('/export_store_self_sale', methods=['POST'])
@module_required('wechat_shop')
def export_store_self_sale():
    """启动店铺自卖 ZIP 后台导出任务。"""
    try:
        start_date = (request.form.get('start_date') or '').strip()
        end_date = (request.form.get('end_date') or '').strip()
        if not start_date or not end_date:
            raise ValueError('请选择开始日期和结束日期')

        _cleanup_store_self_sale_jobs()
        with _store_self_sale_jobs_lock:
            active_job = next(
                (
                    job for job in _store_self_sale_jobs.values()
                    if job.get('status') in {'queued', 'running'}
                ),
                None,
            )
            if active_job:
                return jsonify({
                    'success': False,
                    'message': '已有店铺自卖导出任务正在生成，请等待当前任务完成',
                    'job_id': active_job['job_id'],
                }), 409

            job_id = uuid.uuid4().hex
            database_path = Path(current_app.config['DATABASE_PATH']).resolve()
            output_dir = database_path.parent / 'wechat_shop_export_jobs'
            output_dir.mkdir(parents=True, exist_ok=True)
            cutoff = time.time() - STORE_SELF_SALE_JOB_TTL_SECONDS
            for stale_file in output_dir.glob('*.zip'):
                if stale_file.stat().st_mtime < cutoff:
                    stale_file.unlink(missing_ok=True)
            output_path = output_dir / f'{job_id}.zip'
            now = time.time()
            _store_self_sale_jobs[job_id] = {
                'job_id': job_id,
                'status': 'queued',
                'message': '',
                'download_name': '',
                'output_path': str(output_path),
                'created_at': now,
                'updated_at': now,
            }

        app = current_app._get_current_object()
        worker = threading.Thread(
            target=_run_store_self_sale_export_job,
            args=(app, job_id, start_date, end_date),
            daemon=True,
        )
        worker.start()
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'queued',
            'status_url': f'/wechat_shop/export_store_self_sale/jobs/{job_id}',
            'download_url': f'/wechat_shop/export_store_self_sale/jobs/{job_id}/download',
        }), 202
    except Exception as exc:
        return jsonify({
            'success': False,
            'message': str(exc),
        }), 400


@wechat_shop_bp.route('/export_store_self_sale/jobs/<job_id>', methods=['GET'])
@module_required('wechat_shop')
def store_self_sale_export_job_status(job_id: str):
    with _store_self_sale_jobs_lock:
        job = _store_self_sale_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': '导出任务不存在或已过期'}), 404
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': job['status'],
            'message': job.get('message', ''),
            'download_name': job.get('download_name', ''),
            'download_url': f'/wechat_shop/export_store_self_sale/jobs/{job_id}/download',
        })


@wechat_shop_bp.route('/export_store_self_sale/jobs/<job_id>/download', methods=['GET'])
@module_required('wechat_shop')
def download_store_self_sale_export_job(job_id: str):
    with _store_self_sale_jobs_lock:
        job = _store_self_sale_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': '导出任务不存在或已过期'}), 404
        if job.get('status') != 'complete':
            return jsonify({'success': False, 'message': '导出文件尚未生成完成'}), 409
        output_path = job['output_path']
        download_name = job['download_name']

    if not Path(output_path).is_file():
        return jsonify({'success': False, 'message': '导出文件不存在或已清理'}), 404
    return send_zip_download(output_path, download_name)
