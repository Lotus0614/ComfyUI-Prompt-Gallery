"""
备份管理模块
在删除操作前自动备份存储数据，最多保留指定份数。
"""
import re
import shutil
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 只匹配用户/删除前自动备份目录（backup_YYYYMMDD_HHMMSS，可带去重后缀），
# 排除迁移备份（backup_prompt_schema_*、backup_image_schema_* 等）。
_USER_BACKUP_RE = re.compile(r"^backup_\d{8}_\d{6}(_\d+)?$")


class BackupManager:
    def __init__(self, storage_dir: Path, max_backups: int = 3):
        self.storage_dir = storage_dir
        self.max_backups = max_backups

    # 存储文件模式
    BACKUP_PATTERNS = [
        "prompts.json", "images.json", "categories.json",
        "*.prompts.json", "*.images.json", "*.categories.json",
        "custom_filters.json", "image_fields.json", "storage_config.json",
        ".migration_version",
        ".pending_save_tasks.json",
    ]

    MANIFEST_NAME = "manifest.json"

    def create_backup(self, protected_names=None) -> Optional[Path]:
        """创建备份，返回备份目录路径。无文件可备份时返回 None。"""
        files_to_backup = self._collect_files()
        if not files_to_backup:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.storage_dir / f"backup_{timestamp}"
        suffix = 2
        while backup_dir.exists():
            backup_dir = self.storage_dir / f"backup_{timestamp}_{suffix}"
            suffix += 1
        backup_dir.mkdir()

        for f in files_to_backup:
            shutil.copy2(f, backup_dir / f.name)

        # 记录快照中的完整文件集合。恢复时可据此删除当前目录中多出来的旧分片。
        manifest = {
            "version": 1,
            "createdAt": datetime.now().isoformat(),
            "files": sorted(f.name for f in files_to_backup),
        }
        (backup_dir / self.MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self._cleanup_old_backups(protected_names or set())
        return backup_dir

    def list_backups(self) -> List[dict]:
        """列出所有备份（时间戳、大小、文件数）。"""
        backups = []
        for d in sorted(self.storage_dir.glob("backup_*")):
            if not d.is_dir():
                continue
            if not _USER_BACKUP_RE.match(d.name):
                continue
            files = list(d.iterdir())
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            backups.append({
                "name": d.name,
                "path": str(d),
                "file_count": len(files),
                "total_size": total_size,
            })
        return backups

    def _collect_files(self) -> List[Path]:
        """收集所有需要备份的存储文件。"""
        files = []
        for pattern in self.BACKUP_PATTERNS:
            files.extend(self.storage_dir.glob(pattern))
        # 某些 glob 可能重叠，按绝对路径去重并排除目录。
        unique = {}
        for file_path in files:
            if file_path.is_file():
                unique[str(file_path.resolve())] = file_path
        return sorted(unique.values(), key=lambda p: p.name)

    def restore_backup(self, backup_dir: Path) -> None:
        """恢复一个用户备份，并清理快照中不存在的受管文件。

        新备份带 manifest，可实现精确恢复。旧版本没有 manifest 时只覆盖其中
        明确存在的文件，不主动删除当前文件，避免破坏旧备份未记录的配置。
        """
        if not backup_dir.is_dir():
            raise FileNotFoundError(f"备份不存在: {backup_dir}")

        manifest_path = backup_dir / self.MANIFEST_NAME
        manifest_files = None
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            listed = manifest.get("files") if isinstance(manifest, dict) else None
            if not isinstance(listed, list) or any(
                not isinstance(name, str) or Path(name).name != name for name in listed
            ):
                raise ValueError("备份 manifest 无效")
            manifest_files = set(listed)

        source_files = {
            f.name: f for f in backup_dir.iterdir()
            if f.is_file() and f.name != self.MANIFEST_NAME
        }
        if manifest_files is not None:
            missing = manifest_files - set(source_files)
            if missing:
                raise ValueError(f"备份文件缺失: {', '.join(sorted(missing))}")

        # 先把所有文件复制到同目录临时目录，避免中途读失败时只恢复一半。
        temp_dir = Path(tempfile.mkdtemp(prefix=".restore_", dir=self.storage_dir))
        try:
            for name, source in source_files.items():
                shutil.copy2(source, temp_dir / name)

            if manifest_files is not None:
                current_files = set(self._collect_files())
                current_by_name = {p.name: p for p in current_files}
                for name in set(current_by_name) - manifest_files:
                    current_by_name[name].unlink(missing_ok=True)

            for name in source_files:
                os_target = self.storage_dir / name
                os_target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_dir / name, os_target)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _cleanup_old_backups(self, protected_names=None):
        """保留最新的 max_backups 份，删除其余。只清理用户备份，不动迁移备份。"""
        protected_names = set(protected_names or ())
        backup_dirs = sorted(
            [
                d for d in self.storage_dir.glob("backup_*")
                if d.is_dir() and _USER_BACKUP_RE.match(d.name)
                and d.name not in protected_names
            ],
            key=lambda d: d.name,
        )
        while len(backup_dirs) > self.max_backups:
            oldest = backup_dirs.pop(0)
            shutil.rmtree(oldest, ignore_errors=True)
