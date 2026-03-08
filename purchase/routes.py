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
    data = request.get_json()  # 获取前端 JSON 数据
    input_data = data.get('data', '')  # 获取输入框内容，如果没有则默认为空字符串
    print(f"收到的数据：{input_data}")  # 打印调试信息
    return jsonify({
        'purchase_date': input_data  # 将输入的内容返回给前端
    })
