"""
图片收藏存储。

收藏以 imagePath 为键独立保存在 image_favorites.json，不写入 images.json，
避免每次收藏切换都重写图片映射（包括超大 comfy_output 分片）。
"""
import json
import threading
from pathlib import Path
from typing import Iterable, Set

from ._config import write_json_atomic


class ImageFavoriteStorage:
    """按图片路径记录收藏状态。"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.favorites_file = storage_dir / "image_favorites.json"
        self._lock = threading.Lock()
        self._cache = None
        self._ensure_file()

    def _ensure_file(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.favorites_file.exists():
            self._write_data({"favorites": []})

    def _read_data(self) -> dict:
        if self._cache is not None:
            return self._cache
        try:
            with open(self.favorites_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"favorites": []}
        if not isinstance(data, dict):
            data = {"favorites": []}
        favorites = data.get("favorites")
        if not isinstance(favorites, list):
            favorites = []
        # 只保留非空字符串，容忍手改/历史脏数据
        data["favorites"] = [p for p in favorites if isinstance(p, str) and p]
        self._cache = data
        return data

    def _write_data(self, data: dict):
        write_json_atomic(self.favorites_file, {"favorites": list(data.get("favorites", []))})
        self._cache = None

    def get_all(self) -> Set[str]:
        """获取所有已收藏的图片路径。"""
        with self._lock:
            return set(self._read_data().get("favorites", []))

    def is_favorite(self, image_path: str) -> bool:
        """判断图片是否已收藏。"""
        if not image_path:
            return False
        return image_path in self.get_all()

    def toggle(self, image_path: str) -> bool:
        """切换收藏状态，返回切换后的状态（True 表示已收藏）。"""
        if not image_path:
            raise ValueError("imagePath 不能为空")
        with self._lock:
            data = self._read_data()
            favorites = data.get("favorites", [])
            if image_path in favorites:
                data["favorites"] = [p for p in favorites if p != image_path]
                favorite = False
            else:
                favorites.append(image_path)
                favorite = True
            self._write_data(data)
            return favorite

    def remove_many(self, image_paths: Iterable[str]) -> int:
        """批量移除收藏，返回实际移除数量。"""
        path_set = {p for p in (image_paths or []) if p}
        if not path_set:
            return 0
        with self._lock:
            data = self._read_data()
            favorites = data.get("favorites", [])
            kept = [p for p in favorites if p not in path_set]
            removed = len(favorites) - len(kept)
            if removed:
                data["favorites"] = kept
                self._write_data(data)
            return removed
