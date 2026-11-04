import os
from app.video.music import MusicManager
from app.video.processor import FFmpegProcessor


def test_music_manager():
    mgr = MusicManager(music_dir="assets/music")
    tracks = mgr.get_music_tracks()
    assert isinstance(tracks, list)


def test_ffmpeg_processor_availability():
    processor = FFmpegProcessor()
    # Should safely return boolean True/False without crashing
    avail = processor.is_ffmpeg_available()
    assert isinstance(avail, bool)
