"""Photo uploads are type- and size-checked and stay inside their garden folder."""

import pytest

from verdant.services.photos import MAX_BYTES, photo_belongs_to, save_photo

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_valid_png_is_stored_per_garden(tmp_path):
    path = save_photo("garden-a", PNG, tmp_path)
    assert path.endswith(".png")
    assert photo_belongs_to(path, "garden-a", tmp_path)
    assert not photo_belongs_to(path, "garden-b", tmp_path)


@pytest.mark.parametrize("data", [b"", b"GIF89a....", b"%PDF-1.7", PNG + b"0" * MAX_BYTES],
                         ids=["empty", "gif", "pdf", "oversized"])
def test_rejects_empty_wrong_type_and_oversized(tmp_path, data):
    with pytest.raises(ValueError):
        save_photo("garden-a", data, tmp_path)
