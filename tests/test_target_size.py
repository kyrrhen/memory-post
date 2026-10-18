from sender import compute_target_size


def test_auto_does_not_upscale_small_images():
    assert compute_target_size(800, 600, "auto", 1024, 1_600_000)[:2] == (800, 600)


def test_auto_caps_large_images_by_longest_side_and_pixels():
    width, height, scale = compute_target_size(3000, 2000, "auto", 1024, 1_600_000)
    assert (width, height) == (1024, 683)
    assert 0.0 < scale < 1.0


def test_fixed_mode_uses_requested_longest_side():
    assert compute_target_size(3000, 2000, "fixed", 512, 99_999_999)[:2] == (512, 341)
