from datetime import datetime
import json
import sqlite3

from flask import current_app, jsonify, render_template, render_template_string, request, send_file

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
    export_data_to_excel,
)


DATA_STATUS_TABLE_NAME = 'wechat_shop_data_status'

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


@wechat_shop_bp.route('/')
def index():
    data_status_rows = _get_data_status_rows()
    export_field_config_json = json.dumps(EXPORT_FIELD_CONFIG, ensure_ascii=False)
    return render_template(
        'wechat_shop.html',
        data_status_rows=data_status_rows,
        export_field_config_json=export_field_config_json,
    )


@wechat_shop_bp.route('/import_orders', methods=['POST'])
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

    result = read_order_excel_files(files)

    if not result.get('success'):
        return jsonify(result), 400

    result = _attach_status_rows(result)
    return jsonify(result)


@wechat_shop_bp.route('/import_fund_flow', methods=['POST'])
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

    result = read_fund_flow_excel_files(files)

    if not result.get('success'):
        return jsonify(result), 400

    result = _attach_status_rows(result)
    return jsonify(result)


@wechat_shop_bp.route('/import_after_sales', methods=['POST'])
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

    result = read_after_sales_excel_files(files)

    if not result.get('success'):
        return jsonify(result), 400

    result = _attach_status_rows(result)
    return jsonify(result)


# 新增导出数据接口
@wechat_shop_bp.route('/export_data', methods=['POST'])
def export_data():
    """原始数据导出为 Excel"""
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

        print('筛选条件：', filter_conditions)
        output, download_name = export_data_to_excel(
            table_key=table_key,
            start_time=start_time,
            end_time=end_time,
            selected_fields=selected_fields,
            filter_conditions=filter_conditions,
        )
        return send_file(
            output,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400