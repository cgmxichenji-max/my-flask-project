from flask import Blueprint, render_template, request, jsonify
import sqlite3
import os
import re
from datetime import datetime
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "packaging.db")

purchase_bp = Blueprint('purchase', __name__, template_folder='../templates')


# ===== 数据库连接函数 =====
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def generate_purchase_order_id():
    """当订单号为空时，自动生成采购订单号"""
    now_str = datetime.now().strftime('%Y%m%d%H%M%S')
    rand_str = f"{random.randint(0, 999):03d}"
    return f"PCG{now_str}{rand_str}"


def get_pack_item_id_by_name(conn, pack_item_name):
    """根据包材名称查找 pack_item_id"""
    row = conn.execute(
        "SELECT pack_item_id FROM pack_item WHERE name = ? LIMIT 1",
        (pack_item_name,)
    ).fetchone()
    return row["pack_item_id"] if row else None


# 渲染采购页面
@purchase_bp.route('/')
def purchase():
    print("进入 /purchase/ 路由")
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT pr.purchase_id,
                   pr.order_id,
                   pr.purchase_date,
                   COALESCE(pi.name, '') AS pack_item_name,
                   pr.bag_count,
                   pr.total_quantity AS total_qty,
                   pr.total_amount,
                   pr.notes
            FROM purchase_record pr
            LEFT JOIN pack_item pi ON pr.pack_item_id = pi.pack_item_id
            ORDER BY pr.purchase_id DESC
            LIMIT 50
        """).fetchall()
    finally:
        conn.close()

    return render_template('purchase.html', rows=rows)


# 解析采购数据
@purchase_bp.route('/parse_purchase_data', methods=['POST'])
def parse_purchase_data():
    data = request.get_json() or {}
    input_data = data.get('data', '').strip()
    print(f"收到的数据：{input_data}")

    if not input_data:
        return jsonify({
            'success': False,
            'message': '没有可解析的数据'
        }), 400

    # 拆成多行，取第一条非空行
    lines = [line.strip() for line in input_data.splitlines() if line.strip()]
    if not lines:
        return jsonify({
            'success': False,
            'message': '没有可解析的数据行'
        }), 400

    first_line = lines[0]
    remaining_text = '\n'.join(lines[1:])

    # 按制表符拆分
    parts = first_line.split('\t')

    purchase_date = parts[0].strip() if len(parts) > 0 else ''
    order_no = parts[1].strip() if len(parts) > 1 else ''
    item_desc = parts[2].strip() if len(parts) > 2 else ''
    total_price = parts[4].strip() if len(parts) > 4 else ''

    # 默认值
    pack_item_name = ''
    piece_qty = ''
    remark = item_desc

    # 提取每袋件数，例如 400个、300个、100个
    qty_match = re.search(r'(\d+)\s*个', item_desc)
    if qty_match:
        piece_qty = qty_match.group(1)

    # 提取包材型号（基础版）
    if item_desc.startswith('半高9号'):
        pack_item_name = '9.5'
    elif item_desc.startswith('半高10号'):
        pack_item_name = '10.5'
    elif item_desc.startswith('半高11号'):
        pack_item_name = '11.5'
    elif item_desc.startswith('半高7号'):
        pack_item_name = '7.5'
    elif item_desc.startswith('半高6号'):
        pack_item_name = '6.5'
    elif item_desc.startswith('10号'):
        pack_item_name = '10'
    elif item_desc.startswith('8号'):
        pack_item_name = '8'
    elif item_desc.startswith('6号'):
        pack_item_name = '6'
    elif item_desc.startswith('5号'):
        pack_item_name = '5'
    elif item_desc.startswith('缠绕膜'):
        pack_item_name = '缠绕膜'
    elif item_desc.startswith('气泡柱'):
        pack_item_name = '气泡柱'
    elif item_desc.startswith('气泡袋'):
        pack_item_name = '气泡袋'
    else:
        pack_item_name = item_desc.split('(')[0].split('（')[0].strip()

    return jsonify({
        'success': True,
        'remaining_text': remaining_text,
        'purchase_date': purchase_date,
        'order_no': order_no,
        'pack_item_name': pack_item_name,
        'piece_qty': piece_qty,
        'total_price': total_price,
        'remark': remark
    })


# 提交采购数据并写入数据库
@purchase_bp.route('/submit_purchase', methods=['POST'])
def submit_purchase():
    data = request.get_json() or {}

    purchase_date = (data.get('purchase_date') or '').strip()
    order_id = (data.get('order_id') or '').strip()
    batch_id = (data.get('batch_id') or '').strip()
    pack_item_name = (data.get('pack_item_name') or '').strip()
    supplier_name = (data.get('supplier_name') or '').strip()
    notes = (data.get('notes') or '').strip()

    bag_count_raw = str(data.get('bag_count') or '').strip()
    total_quantity_raw = str(data.get('total_quantity') or '').strip()
    total_amount_raw = str(data.get('total_amount') or '').strip()
    per_bag_quantity_raw = str(data.get('per_bag_quantity') or '').strip()

    if not purchase_date:
        return jsonify({'success': False, 'message': '采购日期不能为空'}), 400

    if not pack_item_name:
        return jsonify({'success': False, 'message': '包材型号不能为空'}), 400

    try:
        bag_count = int(float(bag_count_raw)) if bag_count_raw else 0
    except ValueError:
        return jsonify({'success': False, 'message': '袋数格式不正确'}), 400

    try:
        total_quantity = int(float(total_quantity_raw)) if total_quantity_raw else 0
    except ValueError:
        return jsonify({'success': False, 'message': '总件数格式不正确'}), 400

    try:
        total_amount = float(total_amount_raw) if total_amount_raw else 0.0
    except ValueError:
        return jsonify({'success': False, 'message': '总价格式不正确'}), 400

    # 如果前端没有先算出总件数，后端兜底再算一次
    if total_quantity <= 0 and bag_count > 0 and per_bag_quantity_raw:
        try:
            per_bag_quantity = int(float(per_bag_quantity_raw))
            total_quantity = bag_count * per_bag_quantity
        except ValueError:
            return jsonify({'success': False, 'message': '每袋件数格式不正确'}), 400

    # 订单号为空时自动生成
    if not order_id:
        order_id = generate_purchase_order_id()

    conn = get_db_connection()
    try:
        pack_item_id = get_pack_item_id_by_name(conn, pack_item_name)
        if not pack_item_id:
            return jsonify({'success': False, 'message': f'未找到对应包材：{pack_item_name}'}), 400

        conn.execute("""
            INSERT INTO purchase_record (
                order_id,
                purchase_date,
                pack_item_id,
                supplier_name,
                bag_count,
                total_quantity,
                total_amount,
                batch_id,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            purchase_date,
            pack_item_id,
            supplier_name,
            bag_count,
            total_quantity,
            total_amount,
            batch_id,
            notes
        ))
        conn.commit()

        return jsonify({
            'success': True,
            'message': '采购记录提交成功',
            'order_id': order_id,
            'batch_id': batch_id
        })

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': f'订单号已存在：{order_id}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'提交失败：{str(e)}'}), 500
    finally:
        conn.close()