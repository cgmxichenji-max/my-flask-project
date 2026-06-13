import json as _json

from flask import jsonify, render_template, request, send_file

from auth.decorators import module_required
from common.download_utils import send_excel_download
from common.upload_staging import finish_staged_upload, stage_uploaded_files

from . import courier_fee_bp
from .services import (
    export_shipments_to_excel,
    get_data_status,
    get_pricing_rules,
    save_pricing_rule,
    delete_pricing_rule,
    query_shipments,
    read_shipment_excel_files,
)
from .bill_services import (
    check_file_exists,
    delete_bill_file,
    discard_unverified,
    generate_corrected_zip,
    generate_raw_zip,
    generate_summary_workbook,
    get_bill_anomaly_counts,
    get_bill_file_meta,
    get_bill_files,
    get_bill_months,
    import_bill_file,
    query_bills,
    run_calculation,
    run_opt07,
    save_verified,
)
from .table_schemas import (
    BILLS_DISPLAY_COLUMNS,
    CARRIER_NAMES,
    SHIPMENT_DISPLAY_COLUMNS,
    BASE_WEIGHT_OP_OPTIONS,
)


@courier_fee_bp.route('/', strict_slashes=False)
@module_required('courier_fee')
def index():
    import json
    status          = get_data_status()
    display_headers = [cn for cn, _ in SHIPMENT_DISPLAY_COLUMNS]
    pricing_rules   = get_pricing_rules()

    # Tab 3 初始数据
    from datetime import datetime
    bill_months   = get_bill_months()
    default_ym    = datetime.now().strftime('%Y%m')
    bill_headers  = [(col, label) for col, label, _ in BILLS_DISPLAY_COLUMNS]
    bill_sortable = {col: sortable for col, _, sortable in BILLS_DISPLAY_COLUMNS}

    return render_template(
        'courier_fee.html',
        status              = status,
        display_headers     = display_headers,
        pricing_rules_json  = json.dumps(pricing_rules, ensure_ascii=False),
        base_weight_op_options = BASE_WEIGHT_OP_OPTIONS,
        # Tab 3
        bill_months_json    = json.dumps(bill_months, ensure_ascii=False),
        default_ym          = default_ym,
        bill_headers_json   = json.dumps(bill_headers, ensure_ascii=False),
        bill_sortable_json  = json.dumps(bill_sortable, ensure_ascii=False),
        carrier_names       = CARRIER_NAMES,
    )


@courier_fee_bp.route('/import_shipments', methods=['POST'])
@module_required('courier_fee')
def import_shipments():
    """导入底单记录 Excel 文件。"""
    files = request.files.getlist('files')
    if not files:
        return jsonify({'success': False, 'message': '未接收到任何文件'}), 400

    staged_batch = None
    try:
        staged_batch = stage_uploaded_files(files, 'courier_fee/shipments', ('.xlsx', '.xls'))
        result = read_shipment_excel_files(staged_batch.files)
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

    # 刷新数据状态并附加到返回值
    try:
        result['status'] = get_data_status()
    except Exception:
        pass

    return jsonify(result)


@courier_fee_bp.route('/query_shipments', methods=['POST'])
@module_required('courier_fee')
def query_shipments_route():
    """分页查询底单记录，返回 JSON。"""
    data = request.get_json(silent=True) or {}
    try:
        result = query_shipments(
            ship_time_start=data.get('ship_time_start', ''),
            ship_time_end=data.get('ship_time_end', ''),
            platform=data.get('platform', ''),
            shop_name=data.get('shop_name', ''),
            courier_name=data.get('courier_name', ''),
            tracking_no=data.get('tracking_no', ''),
            order_no=data.get('order_no', ''),
            ship_content_keyword=data.get('ship_content_keyword', ''),
            page=int(data.get('page', 1)),
            page_size=int(data.get('page_size', 100)),
        )
        return jsonify({'success': True, **result})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@courier_fee_bp.route('/export_shipments', methods=['POST'])
@module_required('courier_fee')
def export_shipments():
    """按筛选条件导出底单记录为 Excel。"""
    data = request.get_json(silent=True) or {}
    try:
        buf, filename = export_shipments_to_excel(
            ship_time_start=data.get('ship_time_start', ''),
            ship_time_end=data.get('ship_time_end', ''),
            platform=data.get('platform', ''),
            shop_name=data.get('shop_name', ''),
            courier_name=data.get('courier_name', ''),
            tracking_no=data.get('tracking_no', ''),
            order_no=data.get('order_no', ''),
            ship_content_keyword=data.get('ship_content_keyword', ''),
        )
        return send_excel_download(buf, filename)
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


# ──────────────────────────────────────────────
# 计费规则路由
# ──────────────────────────────────────────────

@courier_fee_bp.route('/pricing_rules', methods=['GET'])
@module_required('courier_fee')
def list_pricing_rules():
    """返回所有计费规则 JSON。"""
    try:
        rules = get_pricing_rules()
        return jsonify({'success': True, 'rules': rules})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@courier_fee_bp.route('/pricing_rules/save', methods=['POST'])
@module_required('courier_fee')
def save_pricing_rule_route():
    """新增或更新一条计费规则。"""
    data = request.get_json(silent=True) or {}
    ok, error, rule_id = save_pricing_rule(data)
    if not ok:
        return jsonify({'success': False, 'message': error}), 400
    try:
        rules = get_pricing_rules()
    except Exception:
        rules = []
    return jsonify({'success': True, 'rule_id': rule_id, 'rules': rules})


@courier_fee_bp.route('/pricing_rules/delete', methods=['POST'])
@module_required('courier_fee')
def delete_pricing_rule_route():
    """删除一条计费规则。"""
    data = request.get_json(silent=True) or {}
    ok, error = delete_pricing_rule(data.get('id'))
    if not ok:
        return jsonify({'success': False, 'message': error}), 400
    try:
        rules = get_pricing_rules()
    except Exception:
        rules = []
    return jsonify({'success': True, 'rules': rules})


# ══════════════════════════════════════════════════════════════════
# Tab 3：快递费账单
# ══════════════════════════════════════════════════════════════════

@courier_fee_bp.route('/bill_months', methods=['GET'])
@module_required('courier_fee')
def bill_months_route():
    """返回已有账单数据的年月列表。"""
    try:
        months = get_bill_months()
        return jsonify({'success': True, 'months': months})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_check_duplicate', methods=['POST'])
@module_required('courier_fee')
def bill_check_duplicate_route():
    """检查同快递公司+年月是否已有上传文件。"""
    data = request.get_json(silent=True) or {}
    try:
        result = check_file_exists(data.get('carrier_name', ''), data.get('year_month', ''))
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_upload', methods=['POST'])
@module_required('courier_fee')
def bill_upload_route():
    """
    上传快递账单文件。
    multipart form: file, carrier_name, year_month, action(''|'replace'|'add')
    若 action=='' 且同月同快递已有文件 → 返回 conflict=true，由前端弹窗。
    """
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': '未收到文件'}), 400

    carrier_name = (request.form.get('carrier_name') or '').strip()
    year_month   = (request.form.get('year_month') or '').strip()
    action       = (request.form.get('action') or '').strip()

    if not carrier_name or not year_month:
        return jsonify({'success': False, 'message': '请指定快递公司和年月'}), 400

    # 第一次上传（无 action）：检查重复
    if not action:
        dup = check_file_exists(carrier_name, year_month)
        if dup['exists']:
            return jsonify({
                'success':  False,
                'conflict': True,
                'message':  f'{year_month} 已有 {carrier_name} 账单文件，请选择：替换 或 保存为第 {len(dup["files"])+1} 份',
                'files':    dup['files'],
                'next_seq': len(dup['files']) + 1,
            })
        action = 'add'

    try:
        result = import_bill_file(file, carrier_name, year_month, action)
        if result['success']:
            result['files'] = get_bill_files(year_month)
            result['months'] = get_bill_months()
        return jsonify(result), (200 if result['success'] else 400)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_files', methods=['GET'])
@module_required('courier_fee')
def bill_files_route():
    """返回账单文件列表，可按年月过滤。"""
    ym = request.args.get('ym', '')
    try:
        files = get_bill_files(ym or None)
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_delete_file', methods=['POST'])
@module_required('courier_fee')
def bill_delete_file_route():
    data = request.get_json(silent=True) or {}
    try:
        ok, msg = delete_bill_file(int(data.get('file_id', 0)))
        if ok:
            ym    = data.get('year_month', '')
            files = get_bill_files(ym or None)
            return jsonify({'success': True, 'message': msg, 'files': files})
        return jsonify({'success': False, 'message': msg}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_download_file/<int:file_id>', methods=['GET'])
@module_required('courier_fee')
def bill_download_file_route(file_id):
    """下载单个原始账单文件。"""
    meta = get_bill_file_meta(file_id)
    if not meta:
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    import os
    if not os.path.exists(meta['stored_path']):
        return jsonify({'success': False, 'message': '文件已被删除'}), 404
    return send_file(
        meta['stored_path'],
        as_attachment=True,
        download_name=meta['stored_filename'],
    )


@courier_fee_bp.route('/bill_download_raw_zip', methods=['POST'])
@module_required('courier_fee')
def bill_download_raw_zip_route():
    """将指定 file_id 列表打包为 ZIP 下载。"""
    data = request.get_json(silent=True) or {}
    file_ids = [int(i) for i in (data.get('file_ids') or [])]
    try:
        buf, filename = generate_raw_zip(file_ids)
        return send_file(
            buf,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_run_calc', methods=['POST'])
@module_required('courier_fee')
def bill_run_calc_route():
    """执行 OPT_02+03 计算。"""
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    if not ym:
        return jsonify({'success': False, 'message': '请指定年月'}), 400
    try:
        result = run_calculation(ym)
        result['counts'] = get_bill_anomaly_counts(ym)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_anomaly_counts', methods=['POST'])
@module_required('courier_fee')
def bill_anomaly_counts_route():
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    try:
        return jsonify({'success': True, 'counts': get_bill_anomaly_counts(ym)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_query', methods=['POST'])
@module_required('courier_fee')
def bill_query_route():
    """横表分页查询。"""
    data = request.get_json(silent=True) or {}
    try:
        result = query_bills(
            year_month  = data.get('year_month', ''),
            filter_type = data.get('filter_type', 'all'),
            search      = data.get('search', ''),
            page        = int(data.get('page', 1)),
            page_size   = int(data.get('page_size', 100)),
            sort_col    = data.get('sort_col', 'bill_date'),
            sort_dir    = data.get('sort_dir', 'ASC'),
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_run_opt07', methods=['POST'])
@module_required('courier_fee')
def bill_run_opt07_route():
    """OPT_07：对未勾选异常行写回修正费用。"""
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    ok_ids = data.get('ok_ids') or []
    if not ym:
        return jsonify({'success': False, 'message': '请指定年月'}), 400
    try:
        result = run_opt07(ym, ok_ids)
        result['counts'] = get_bill_anomaly_counts(ym)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_download_corrected_zip', methods=['POST'])
@module_required('courier_fee')
def bill_download_corrected_zip_route():
    """生成修正后的账单文件并以 ZIP 下载（不在服务器上保留副本）。"""
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    if not ym:
        return jsonify({'success': False, 'message': '请指定年月'}), 400
    try:
        buf, filename = generate_corrected_zip(ym)
        return send_file(
            buf,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_download_summary_workbook', methods=['POST'])
@module_required('courier_fee')
def bill_download_summary_workbook_route():
    """基于当前年月已核查入库数据生成快递费汇总表。"""
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    if not ym:
        return jsonify({'success': False, 'message': '请指定年月'}), 400
    try:
        buf, filename = generate_summary_workbook(ym)
        return send_excel_download(buf, filename)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_save_verified', methods=['POST'])
@module_required('courier_fee')
def bill_save_verified_route():
    """将本月所有未核查数据标记为已核查（正式入库）。"""
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    if not ym:
        return jsonify({'success': False, 'message': '请指定年月'}), 400
    try:
        result = save_verified(ym)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@courier_fee_bp.route('/bill_discard_unverified', methods=['POST'])
@module_required('courier_fee')
def bill_discard_unverified_route():
    """丢弃本月所有未核查数据及对应文件。"""
    data = request.get_json(silent=True) or {}
    ym = (data.get('year_month') or '').strip()
    if not ym:
        return jsonify({'success': False, 'message': '请指定年月'}), 400
    try:
        result = discard_unverified(ym)
        result['months'] = get_bill_months()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
