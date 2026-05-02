from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import shutil
import uuid
from pathlib import Path
from typing import Iterable

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


UPLOAD_STAGING_DIR = 'upload_staging'
TMP_DIR_NAME = 'tmp'
LOG_FILENAME = 'import_log.jsonl'
DEFAULT_STALE_HOURS = 2


@dataclass(frozen=True)
class StagedUploadFile:
    original_filename: str
    stored_filename: str
    path: Path

    @property
    def filename(self) -> str:
        return self.original_filename


@dataclass(frozen=True)
class StagedUploadBatch:
    batch_id: str
    import_key: str
    batch_dir: Path
    files: list[StagedUploadFile]


def _data_dir() -> Path:
    root_path = Path(current_app.root_path)
    data_dir = root_path / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _staging_dir() -> Path:
    path = _data_dir() / UPLOAD_STAGING_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _tmp_root() -> Path:
    path = _staging_dir() / TMP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_path() -> Path:
    return _staging_dir() / LOG_FILENAME


def _now_text() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _safe_import_key(import_key: str) -> str:
    cleaned = str(import_key or '').strip().replace('\\', '/').strip('/')
    parts = [secure_filename(part) for part in cleaned.split('/') if secure_filename(part)]
    if not parts:
        raise ValueError('导入类型不能为空')
    return '/'.join(parts)


def _write_event(event: dict) -> None:
    log_path = _log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'time': _now_text(), **event}
    with open(log_path, 'a', encoding='utf-8') as log_file:
        log_file.write(json.dumps(payload, ensure_ascii=False) + '\n')


def cleanup_stale_upload_batches(max_age_hours: int = DEFAULT_STALE_HOURS) -> int:
    """删除异常中断留下的旧批次目录，避免临时文件长期占用硬盘。"""
    tmp_root = _tmp_root()
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    removed_count = 0

    for batch_dir in tmp_root.rglob('*'):
        if not batch_dir.is_dir():
            continue
        if len(batch_dir.name) != 32:
            continue
        try:
            int(batch_dir.name, 16)
        except ValueError:
            continue
        try:
            modified_at = datetime.fromtimestamp(batch_dir.stat().st_mtime)
            if modified_at >= cutoff:
                continue
            shutil.rmtree(batch_dir, ignore_errors=True)
            removed_count += 1
            _write_event({
                'event': 'cleanup_stale_batch',
                'batch_dir': str(batch_dir.relative_to(_data_dir())),
            })
        except OSError as exc:
            _write_event({
                'event': 'cleanup_stale_batch_failed',
                'batch_dir': str(batch_dir),
                'error': str(exc),
            })

    return removed_count


def stage_uploaded_files(
    files: Iterable[FileStorage],
    import_key: str,
    allowed_extensions: tuple[str, ...],
) -> StagedUploadBatch:
    """把上传文件保存到独立批次目录；调用方必须在导入结束后清理该批次。"""
    cleanup_stale_upload_batches()

    safe_key = _safe_import_key(import_key)
    normalized_extensions = tuple(ext.lower() for ext in allowed_extensions)
    batch_id = uuid.uuid4().hex
    batch_dir = _tmp_root() / safe_key / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)

    staged_files: list[StagedUploadFile] = []

    try:
        for index, file_obj in enumerate(files, start=1):
            original_filename = (file_obj.filename or '').strip()
            if not original_filename:
                raise ValueError('存在未命名文件')
            if not original_filename.lower().endswith(normalized_extensions):
                raise ValueError(f'不支持的文件类型：{original_filename}')

            safe_name = secure_filename(original_filename) or f'upload_{index}'
            stored_filename = f'{index:03d}_{uuid.uuid4().hex[:8]}_{safe_name}'
            stored_path = batch_dir / stored_filename
            file_obj.save(str(stored_path))
            staged_files.append(StagedUploadFile(
                original_filename=original_filename,
                stored_filename=stored_filename,
                path=stored_path,
            ))

        if not staged_files:
            raise ValueError('未接收到任何文件')

        _write_event({
            'event': 'stage_created',
            'batch_id': batch_id,
            'import_key': safe_key,
            'file_count': len(staged_files),
            'filenames': [item.original_filename for item in staged_files],
        })
        return StagedUploadBatch(
            batch_id=batch_id,
            import_key=safe_key,
            batch_dir=batch_dir,
            files=staged_files,
        )
    except Exception:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise


def finish_staged_upload(batch: StagedUploadBatch | None, status: str, message: str = '') -> None:
    """记录轻量结果并删除批次目录，防止临时文件影响后续导入。"""
    if batch is None:
        return

    cleanup_ok = True
    cleanup_error = ''
    try:
        shutil.rmtree(batch.batch_dir, ignore_errors=False)
    except FileNotFoundError:
        cleanup_ok = True
    except OSError as exc:
        cleanup_ok = False
        cleanup_error = str(exc)
        shutil.rmtree(batch.batch_dir, ignore_errors=True)

    _write_event({
        'event': 'stage_finished',
        'batch_id': batch.batch_id,
        'import_key': batch.import_key,
        'status': status,
        'message': str(message or '')[:500],
        'file_count': len(batch.files),
        'filenames': [item.original_filename for item in batch.files],
        'cleanup_ok': cleanup_ok,
        'cleanup_error': cleanup_error,
    })
