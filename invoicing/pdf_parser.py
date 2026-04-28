"""发票 PDF 解析：纯函数模块，不依赖 Flask / DB。"""
import re

import pdfplumber
import fitz  # PyMuPDF
import cv2
import numpy as np


PROJECT_VALID_KEYWORDS = ('服务', '推广')
REMARK_BLOCKER_KEYWORDS = (
    '代扣代缴',
    '未按规定扣缴',
    '不得作为所得税前合法有效扣除凭证',
)


def _extract_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return '\n'.join(page.extract_text() or '' for page in pdf.pages)


def _clean(line):
    return re.sub(r'\s+', ' ', line or '').strip()


def _extract_invoice_number(text):
    m = re.search(r'发票号码[:：]?\s*(\d{8,})', text)
    return m.group(1) if m else ''


def _extract_invoice_date(text):
    m = re.search(r'开票日期[:：]?\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    return ''


def _extract_invoice_type(text):
    compact = re.sub(r'\s+', '', text or '')
    if '增值税专用发票' in compact or '电子发票(增值税专用发票)' in compact or '电子发票（增值税专用发票）' in compact:
        return '增值税专用发票'
    if '普通发票' in compact:
        return '普通发票'
    return ''


def _extract_amount(text):
    m = re.search(r'价税合计.*?[¥￥]\s*([\d,]+\.\d{2})', text, re.S)
    if m:
        return float(m.group(1).replace(',', ''))
    m = re.search(r'\(小写\)\s*[¥￥]\s*([\d,]+\.\d{2})', text)
    if m:
        return float(m.group(1).replace(',', ''))
    return None


def _extract_tax_rate(text):
    lines = [_clean(line) for line in text.splitlines()]
    for idx, line in enumerate(lines):
        if '税率' not in line and '征收率' not in line:
            continue
        candidates = [line] + lines[idx + 1:idx + 5]
        for candidate in candidates:
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', candidate)
            if m:
                return f'{m.group(1)}%'
            for word in ('免税', '不征税'):
                if word in candidate:
                    return word

    for pattern in (r'税率/征收率\s*(\d+(?:\.\d+)?%)', r'税率\s*(\d+(?:\.\d+)?%)', r'征收率\s*(\d+(?:\.\d+)?%)'):
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    return ''


def _extract_seller_name(text):
    patterns = [
        r'销\s*名称[:：]?\s*(.*?)\n买\s*售',
        r'销\s*售\s*方[\s\S]{0,300}?名\s*称[:：]?\s*([^\n]+)',
        r'销\s*[\s\S]{0,5}方[\s\S]{0,300}?名\s*称[:：]?\s*([^\n]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.S)
        if m:
            return _clean(m.group(1))
    return ''


def _extract_buyer_name(text):
    patterns = [
        r'购\s*名称[:：]?\s*(.*?)\s*销\s*名称[:：]',
        r'购\s*买\s*方[\s\S]{0,300}?名\s*称[:：]?\s*([^\n]+)',
        r'购\s*[\s\S]{0,5}方[\s\S]{0,300}?名\s*称[:：]?\s*([^\n]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.S)
        if m:
            return _clean(m.group(1))
    return ''


def _extract_project_name(text):
    lines = [_clean(line) for line in text.splitlines()]
    for idx, line in enumerate(lines):
        if '项目名称' not in line and '货物或应税劳务、服务名称' not in line:
            continue
        for candidate in lines[idx + 1:]:
            if not candidate:
                continue
            if any(t in candidate for t in ('规格型号', '单位', '数量', '单价', '税率', '税额')):
                continue
            if candidate.startswith('合 计') or candidate.startswith('价税合计'):
                return ''
            return candidate.split(' ', 1)[0] or candidate
    return ''


def _extract_pdf_remark(text):
    """以「价税合计」行为上界、「开票人」行为下界，收集中间所有备注内容。

    pdfplumber 提取增值税发票表格时，备注栏的左侧"备 注"二字会被拆成单字单行，
    且备注栏右侧内容可能出现在"备"字之前或之后。所以单纯以"备"为起点会漏行，
    用价税合计 + 开票人 包夹整个备注 cell 区间最稳定。
    """
    lines = [_clean(line) for line in text.splitlines()]
    upper_idx = None
    lower_idx = None
    for i, line in enumerate(lines):
        if upper_idx is None and '价税合计' in line:
            upper_idx = i
            continue
        if upper_idx is not None and line.startswith('开票人'):
            lower_idx = i
            break
    if upper_idx is None or lower_idx is None:
        return ''
    remark_lines = []
    for line in lines[upper_idx + 1:lower_idx]:
        if line in ('', '备', '注'):
            continue
        if line.startswith('注 '):
            line = _clean(line[1:])
        elif line.startswith('备 '):
            line = _clean(line[1:])
        if line:
            remark_lines.append(line)
    return '\n'.join(remark_lines)


def _extract_qr_content(pdf_path):
    doc = None
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img_data = pix.tobytes('png')
            arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                continue
            detector = cv2.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(img)
            if data:
                return data
        return ''
    except Exception:
        return ''
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def suggest_is_usable(project_name, pdf_remark):
    project_ok = bool(project_name) and any(k in project_name for k in PROJECT_VALID_KEYWORDS)
    remark_blocked = bool(pdf_remark) and any(k in pdf_remark for k in REMARK_BLOCKER_KEYWORDS)
    return 1 if (project_ok and not remark_blocked) else 0


def parse_pdf(pdf_path):
    """主入口。返回 dict，所有缺失字段为 '' 或 None，不抛异常。"""
    text = _extract_text(pdf_path)
    qr = _extract_qr_content(pdf_path)

    invoice_number = _extract_invoice_number(text)
    invoice_date = _extract_invoice_date(text)
    amount = _extract_amount(text)

    # QR 兜底（增值税电子发票二维码格式：01,版本,代码,号码,金额,日期YYYYMMDD,校验码,hash）
    if qr:
        parts = qr.split(',')
        if len(parts) >= 7:
            qr_num = parts[3].strip()
            qr_amt = parts[4].strip()
            qr_dt = parts[5].strip()
            if not invoice_number and qr_num:
                invoice_number = qr_num
            if amount is None and qr_amt:
                try:
                    amount = float(qr_amt)
                except ValueError:
                    pass
            if not invoice_date and len(qr_dt) == 8 and qr_dt.isdigit():
                invoice_date = f'{qr_dt[:4]}-{qr_dt[4:6]}-{qr_dt[6:8]}'

    return {
        'invoice_number': invoice_number,
        'invoice_date': invoice_date,
        'invoice_type': _extract_invoice_type(text),
        'amount': amount,
        'tax_rate': _extract_tax_rate(text),
        'seller_name': _extract_seller_name(text),
        'buyer_name': _extract_buyer_name(text),
        'project_name': _extract_project_name(text),
        'pdf_remark': _extract_pdf_remark(text),
        'qr_content': qr,
    }
