from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from flask import send_file


EXCEL_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
ZIP_MIMETYPE = 'application/zip'
PDF_MIMETYPE = 'application/pdf'


def send_download(
    file_obj: str | Path | BytesIO | BinaryIO,
    download_name: str,
    mimetype: str,
    as_attachment: bool = True,
):
    """统一文件下载响应，集中管理下载名、MIME 类型和附件行为。"""
    return send_file(
        file_obj,
        mimetype=mimetype,
        as_attachment=as_attachment,
        download_name=download_name,
    )


def send_excel_download(file_obj: BytesIO | BinaryIO, download_name: str):
    return send_download(file_obj, download_name, EXCEL_MIMETYPE)


def send_zip_download(file_obj: BytesIO | BinaryIO, download_name: str):
    return send_download(file_obj, download_name, ZIP_MIMETYPE)


def send_pdf_inline(file_path: str | Path):
    return send_file(str(file_path), mimetype=PDF_MIMETYPE)
