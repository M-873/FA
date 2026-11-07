"""
capture_screens.py
==================
Renders and captures screenshots of all FA Studio screens to output/ui_screens/:
- home.png
- today_video.png
- history.png
- accounts.png
- settings.png
- logs.png
- wizard.png
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes
from PIL import Image

from app.ui.modern_app import ModernDesktopApp
from app.ui.controller import UIController
from app.jobs.state import JobStatus


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def capture_tk_window(app, hwnd: int) -> Image.Image:
    """Captures client area of the Tkinter window using Windows GDI PrintWindow."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    w = app.winfo_width()
    h = app.winfo_height()
    if w <= 100 or h <= 100:
        w, h = 1120, 720

    hdc = user32.GetDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)

    # PrintWindow flag 2 = PW_RENDERFULLCONTENT
    user32.PrintWindow(hwnd, mdc, 2)

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h  # top-down orientation
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = (ctypes.c_byte * (w * h * 4))()
    gdi32.GetDIBits(mdc, bmp, 0, h, ctypes.byref(buf), ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)

    # Clean up Win32 objects
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)

    return img.convert("RGB")


def capture_all():
    out_dir = os.path.join("output", "ui_screens")
    os.makedirs(out_dir, exist_ok=True)

    ctrl = UIController()

    # Populate mock today job so Today's Video and Home screens display rich data
    job = ctrl.job_mgr.get_or_create_today_job()
    job.status = JobStatus.AWAITING_APPROVAL
    job.topic_title = "এআই যখন বিড়ালের ভাষা বুঝতে চাইল!"
    job.clip_id = "855564"
    job.provider = "pexels"
    job.video_path = "output/final.mp4"
    ctrl.job_mgr.save_job(job)

    # Ensure publishing history has entries
    if not ctrl.get_publishing_history():
        ctrl.history_mgr.record_publication(
            date="2026-11-06",
            topic="এআই যখন বিড়ালের ভাষা বুঝতে চাইল!",
            clip_id="local_sample_tech_vertical",
            provider="local",
            video_id="DI-y14x2ib4",
            status="PUBLISHED",
        )

    app = ModernDesktopApp(controller=ctrl)
    app.geometry("1120x720")
    app.update_idletasks()
    app.update()
    time.sleep(0.3)

    hwnd = app.winfo_id()

    screens = [
        ("home", "home.png"),
        ("today_video", "today_video.png"),
        ("history", "history.png"),
        ("accounts", "accounts.png"),
        ("settings", "settings.png"),
        ("logs", "logs.png"),
        ("wizard", "wizard.png"),
    ]

    captured_files = []
    for route, filename in screens:
        app.navigate_to(route)
        app.update_idletasks()
        app.update()
        time.sleep(0.35)

        img = capture_tk_window(app, hwnd)
        file_path = os.path.join(out_dir, filename)
        img.save(file_path, "PNG")
        file_size_kb = os.path.getsize(file_path) / 1024
        print(f"Captured {route} -> {file_path} ({img.size[0]}x{img.size[1]}, {file_size_kb:.1f} KB)")
        captured_files.append((filename, file_path, file_size_kb))

    app.destroy()
    return captured_files


if __name__ == "__main__":
    captured = capture_all()
    print(f"\nAll {len(captured)} screens captured successfully:")
    for fn, fp, sz in captured:
        print(f"- {fn}: {sz:.1f} KB")
