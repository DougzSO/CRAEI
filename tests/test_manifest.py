from craei.manifest import Manifest


def test_register_then_is_intact(tmp_path):
    data_file = tmp_path / "data.nc"
    data_file.write_bytes(b"some bytes")
    manifest = Manifest(tmp_path / "manifest.json")

    entry = manifest.register("key1", data_file, origin="https://example.com/data.nc")

    assert entry["size"] == data_file.stat().st_size
    assert manifest.is_intact("key1")


def test_is_intact_false_for_unregistered_key(tmp_path):
    manifest = Manifest(tmp_path / "manifest.json")
    assert manifest.is_intact("missing") is False


def test_is_intact_false_when_file_modified(tmp_path):
    data_file = tmp_path / "data.nc"
    data_file.write_bytes(b"original")
    manifest = Manifest(tmp_path / "manifest.json")
    manifest.register("key1", data_file, origin="local")

    data_file.write_bytes(b"tampered content")

    assert manifest.is_intact("key1") is False


def test_is_intact_false_when_file_deleted(tmp_path):
    data_file = tmp_path / "data.nc"
    data_file.write_bytes(b"original")
    manifest = Manifest(tmp_path / "manifest.json")
    manifest.register("key1", data_file, origin="local")

    data_file.unlink()

    assert manifest.is_intact("key1") is False


def test_manifest_persists_across_instances(tmp_path):
    data_file = tmp_path / "data.nc"
    data_file.write_bytes(b"original")
    manifest_path = tmp_path / "manifest.json"

    Manifest(manifest_path).register("key1", data_file, origin="local")
    reloaded = Manifest(manifest_path)

    assert reloaded.is_intact("key1")
