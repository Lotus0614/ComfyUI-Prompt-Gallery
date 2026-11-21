import json

from storage.image_favorite import ImageFavoriteStorage


def read_favorites_file(tmp_path):
    return json.loads((tmp_path / "image_favorites.json").read_text(encoding="utf-8"))


def test_storage_starts_empty_and_creates_file(tmp_path):
    storage = ImageFavoriteStorage(tmp_path)

    assert storage.get_all() == set()
    assert (tmp_path / "image_favorites.json").exists()
    assert read_favorites_file(tmp_path) == {"favorites": []}


def test_toggle_adds_then_removes_and_persists(tmp_path):
    storage = ImageFavoriteStorage(tmp_path)
    image_path = "prompt_gallery/a.png"

    assert storage.toggle(image_path) is True
    assert storage.get_all() == {image_path}
    assert read_favorites_file(tmp_path) == {"favorites": [image_path]}

    reloaded = ImageFavoriteStorage(tmp_path)
    assert reloaded.is_favorite(image_path) is True

    assert reloaded.toggle(image_path) is False
    assert reloaded.get_all() == set()
    assert read_favorites_file(tmp_path) == {"favorites": []}


def test_remove_many_only_removes_existing_paths(tmp_path):
    storage = ImageFavoriteStorage(tmp_path)
    storage.toggle("prompt_gallery/a.png")
    storage.toggle("prompt_gallery/b.png")

    removed = storage.remove_many(["prompt_gallery/a.png", "prompt_gallery/missing.png"])

    assert removed == 1
    assert storage.get_all() == {"prompt_gallery/b.png"}
    assert storage.remove_many([]) == 0


def test_corrupt_file_recovers_to_empty_and_writes_valid_json(tmp_path):
    (tmp_path / "image_favorites.json").write_text("not-json", encoding="utf-8")

    storage = ImageFavoriteStorage(tmp_path)

    assert storage.get_all() == set()
    assert storage.toggle("prompt_gallery/a.png") is True
    assert read_favorites_file(tmp_path) == {"favorites": ["prompt_gallery/a.png"]}


def test_invalid_favorites_value_is_ignored(tmp_path):
    (tmp_path / "image_favorites.json").write_text(
        json.dumps({"favorites": ["prompt_gallery/a.png", "", 42, None]}),
        encoding="utf-8",
    )

    storage = ImageFavoriteStorage(tmp_path)

    assert storage.get_all() == {"prompt_gallery/a.png"}


def test_toggle_removes_duplicate_entries(tmp_path):
    (tmp_path / "image_favorites.json").write_text(
        json.dumps({"favorites": ["prompt_gallery/a.png", "prompt_gallery/a.png"]}),
        encoding="utf-8",
    )

    storage = ImageFavoriteStorage(tmp_path)

    assert storage.toggle("prompt_gallery/a.png") is False
    assert storage.get_all() == set()
