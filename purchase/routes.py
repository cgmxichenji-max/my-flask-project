from flask import Blueprint, render_template, request, jsonify
import sqlite3
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "packaging.db")

purchase_bp = Blueprint('purchase', __name__, template_folder='../templates')

# ===== 数据库连接函数 =====
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# 渲染采购页面
@purchase_bp.route('/')
def purchase():
    print("进入 /purchase/ 路由")  # 打印调试信息
    return render_template('purchase.html')

# 解析采购数据（处理POST请求）
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

    # 提取包材型号（先做基础版，后面再细化）
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
        # 先保留“气泡袋”，后续再细分尺寸
        pack_item_name = '气泡袋'
    else:
        # 实在匹配不到，先保留原始描述前半段
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
