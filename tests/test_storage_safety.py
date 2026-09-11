import json

import pytest

from storage.backup import BackupManager
from storage.custom_filter import CustomFilterStorage
from storage.image_field import ImageFieldStorage
from storage.image_mapping import ImageMappingStorage
from storage.prompt import PromptStorage


def test_backup_includes_all_storage_files_and_restores_exact_snapshot(tmp_path):
    files = {
        "prompts.json": {"prompts": [{"value": "a"}]},
        "images.json": {"mappings": []},
        "categories.json": {"categories": []},
        "custom_filters.json": {"filters": []},
        "image_fields.json": {"fields": []},
        "storage_config.json": {"disabled_files": ["x"]},
    }
    for name, data in files.items():
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")

    manager = BackupManager(tmp_path)
    backup = manager.create_backup()
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    assert set(files).issubset(manifest["files"])

    # 当前目录新增的受管分片应在精确恢复时被清掉。
    (tmp_path / "stale.prompts.json").write_text('{"prompts": []}', encoding="utf-8")
    manager.restore_backup(backup)
    assert not (tmp_path / "stale.prompts.json").exists()
    assert json.loads((tmp_path / "storage_config.json").read_text(encoding="utf-8")) == files["storage_config.json"]


def test_corrupt_custom_filter_file_is_not_overwritten(tmp_path):
    path = tmp_path / "custom_filters.json"
    original = "{broken"
    path.write_text(original, encoding="utf-8")

    storage = CustomFilterStorage(tmp_path)
    assert storage.get_all()
    assert path.read_text(encoding="utf-8") == original
    with pytest.raises(RuntimeError):
        storage.create("new", "def filter_func(item, keywords):\n    return True")


def test_corrupt_image_field_file_is_not_overwritten(tmp_path):
    path = tmp_path / "image_fields.json"
    original = "[]"
    path.write_text(original, encoding="utf-8")

    storage = ImageFieldStorage(tmp_path)
    assert storage.get_all()
    assert path.read_text(encoding="utf-8") == original
    with pytest.raises(RuntimeError):
        storage.create("new", "def extract_func(item):\n    return ''")


def test_mapping_batch_is_idempotent_for_background_retry(tmp_path):
    storage = ImageMappingStorage(tmp_path)
    item = {
        "image_path": "prompt_gallery/a.png",
        "prompt_string": "a",
        "file_info": {},
    }
    assert storage.add_mappings_batch([item]) == 1
    assert storage.add_mappings_batch([item]) == 0
    assert len(storage.get_all_mappings()) == 1


def test_write_skips_unchanged_shards(tmp_path, monkeypatch):
    shard = tmp_path / "import.prompts.json"
    shard.write_text(json.dumps({"prompts": [{"value": "from-shard"}]}), encoding="utf-8")
    writes = []

    import storage._json_store as json_store
    original_write = json_store.write_json_atomic

    def tracking_write(path, data):
        writes.append(path.name)
        return original_write(path, data)

    monkeypatch.setattr(json_store, "write_json_atomic", tracking_write)
    storage = PromptStorage(tmp_path)
    storage.add_prompt("from-main")

    assert writes == ["prompts.json"]
