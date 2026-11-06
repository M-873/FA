"""
tests/test_music_rotation.py
=============================
Tests for MusicManager:
- Consecutive-day track rotation
- Fallback when only single track is available
- Persistent history storage
- Verifiable license source URL resolution (licenses.json, sidecar .url, or UNVERIFIED)
"""

import json
import os
import pytest
from app.video.music import MusicManager


@pytest.fixture
def temp_music_env(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    history_file = tmp_path / "music_history.json"
    licenses_file = music_dir / "licenses.json"

    # Create dummy tracks
    track_a = music_dir / "track_alpha.mp3"
    track_b = music_dir / "track_beta.wav"
    track_c = music_dir / "track_gamma.mp3"
    for t in (track_a, track_b, track_c):
        t.write_text("dummy audio content")

    return {
        "music_dir": str(music_dir),
        "history_file": str(history_file),
        "licenses_file": str(licenses_file),
        "tracks": [str(track_a), str(track_b), str(track_c)],
    }


def test_music_rotation_avoids_consecutive_repeat(temp_music_env):
    """Ensures select_track rotates and avoids repeating previous_track."""
    mgr = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=temp_music_env["history_file"],
        licenses_file=temp_music_env["licenses_file"],
    )

    track_a = temp_music_env["tracks"][0]
    for _ in range(10):
        selected = mgr.select_track(previous_track=track_a)
        assert os.path.basename(selected) != os.path.basename(track_a)


def test_sequential_rotation_never_repeats_immediately(temp_music_env):
    """Simulates consecutive daily runs, ensuring no two successive days share the same track."""
    mgr = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=temp_music_env["history_file"],
        licenses_file=temp_music_env["licenses_file"],
    )

    prev = None
    for _ in range(15):
        current = mgr.select_track()
        if prev is not None:
            assert os.path.basename(current) != os.path.basename(prev)
        prev = current


def test_music_rotation_with_single_track(tmp_path):
    """When only 1 track exists, select_track returns it without error."""
    music_dir = tmp_path / "single_music"
    music_dir.mkdir()
    only_track = music_dir / "solo.wav"
    only_track.write_text("solo content")

    mgr = MusicManager(music_dir=str(music_dir), history_file=str(tmp_path / "hist.json"))
    selected = mgr.select_track(previous_track=str(only_track))
    assert selected == str(only_track)


def test_music_persists_history_file(temp_music_env):
    """Verifies that selected track is saved and read across MusicManager instances."""
    hist_path = temp_music_env["history_file"]
    mgr1 = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=hist_path,
        licenses_file=temp_music_env["licenses_file"],
    )
    first_choice = mgr1.select_track()
    assert os.path.exists(hist_path)

    # Read with new instance
    mgr2 = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=hist_path,
        licenses_file=temp_music_env["licenses_file"],
    )
    assert mgr2.get_last_used_track() == first_choice


def test_get_track_source_url_from_licenses_json(temp_music_env):
    """Resolves verifiable source URL from licenses.json."""
    licenses = {
        "track_alpha.mp3": "https://pixabay.com/music/beats-track-alpha-1234/",
        "track_beta.wav": {"source_url": "https://freemusicarchive.org/music/beta-5678/"},
    }
    with open(temp_music_env["licenses_file"], "w", encoding="utf-8") as f:
        json.dump(licenses, f)

    mgr = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=temp_music_env["history_file"],
        licenses_file=temp_music_env["licenses_file"],
    )

    url_a = mgr.get_track_source_url(temp_music_env["tracks"][0])
    assert url_a == "https://pixabay.com/music/beats-track-alpha-1234/"

    url_b = mgr.get_track_source_url(temp_music_env["tracks"][1])
    assert url_b == "https://freemusicarchive.org/music/beta-5678/"


def test_get_track_source_url_from_sidecar_file(temp_music_env):
    """Resolves verifiable URL from <track_name>.url sidecar file."""
    track_c = temp_music_env["tracks"][2]
    sidecar_url = os.path.splitext(track_c)[0] + ".url"
    with open(sidecar_url, "w", encoding="utf-8") as f:
        f.write("https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1100")

    mgr = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=temp_music_env["history_file"],
        licenses_file=temp_music_env["licenses_file"],
    )

    url_c = mgr.get_track_source_url(track_c)
    assert url_c == "https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1100"


def test_get_track_source_url_unverified_fallback(temp_music_env):
    """Returns 'UNVERIFIED' when no valid URL is found (no synthetic or invented source)."""
    mgr = MusicManager(
        music_dir=temp_music_env["music_dir"],
        history_file=temp_music_env["history_file"],
        licenses_file=temp_music_env["licenses_file"],
    )

    assert mgr.get_track_source_url(temp_music_env["tracks"][0]) == "UNVERIFIED"
    assert mgr.get_track_source_url(None) == "UNVERIFIED"
    assert mgr.get_track_source_url("") == "UNVERIFIED"

