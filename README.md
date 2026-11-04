# Lightweight AI 2D Cartoon Daily Video Automation

A production-ready, modular, lightweight Windows application that automatically creates **ONE 10–15 second 2D cartoon video per day** and publishes the **SAME MASTER FINAL MP4** file to:

1. **Facebook Reel** (Meta Graph API)
2. **Facebook Story** (Only if officially supported by Meta API)
3. **YouTube Shorts** (YouTube Data API v3 OAuth 2.0)

> ⚡ **Target Hardware**: Windows 10/11 | NVIDIA GeForce MX110 2GB VRAM | Intel i5 7th Gen | 8GB RAM (`LEGACY_LOW` Profile).
> 🔒 **Single Render Guarantee**: Generates and renders ONLY ONE master final video (`output/final.mp4`) per daily run. No duplicate renders or permanent video archives.

---

## 🚀 Execution Workflow

```
                        Detect Hardware Specs
                                  │
                                  ▼
                       Check Today's Job State
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
   [If Already Completed]                       [If Pending / Recovery]
    Show COMPLETED & exit                        Start Automation Workflow
                                                          │
                                                          ▼
                                                 Find Cartoon Concept
                                                          │
                                                          ▼
                                                  Generate Script
                                                          │
                                                          ▼
                                                 Generate Scene Plan
                                                          │
                                                          ▼
                                                  Generate Cloud TTS
                                                          │
                                                          ▼
                                                2D Character Rigging
                                                          │
                                                          ▼
                                                Viseme Lip Sync & Subs
                                                          │
                                                          ▼
                                                FFmpeg Master Render
                                                          │
                                                          ▼
                                                Pre-Upload Quality Check
                                                          │
                                                          ▼
                                                 ONE MASTER FINAL MP4
                                               (output/final.mp4)
                                                          │
                                        ┌─────────────────┴─────────────────┐
                                        ▼                                   ▼
                                 Facebook Reel                        YouTube Shorts
                                        │                                   │
                                        ▼                                   │
                                 Facebook Story*                            │
                                        │                                   │
                                        └─────────────────┬─────────────────┘
                                                          │
                                                          ▼
                                               Save Minimal State JSON
                                                          │
                                                          ▼
                                                Purge Temporary Files
                                                          │
                                                          ▼
                                                        DONE
```

*\*Story publishing strictly uses official Meta Graph API endpoints. If Story publishing is unavailable for your Page/App permissions, the system logs the limitation and continues Reel and Shorts publishing without breaking.*

---

## 📦 Project Architecture

```
.
├── app/
│   ├── ai/                         # Gemini & OpenAI cartoon script/topic providers
│   │   ├── base.py
│   │   ├── gemini.py
│   │   └── openai_provider.py
│   ├── animation/                  # Lightweight 2D rigging, actions, viseme lip-sync, subtitles
│   │   ├── actions.py
│   │   ├── rig.py
│   │   ├── lip_sync.py
│   │   ├── subtitles.py
│   │   └── engine.py
│   ├── hardware/                   # Hardware detection, performance profiles, memory safety
│   │   ├── detector.py
│   │   ├── profiles.py
│   │   └── monitor.py
│   ├── jobs/                       # State management, recovery, & workflow orchestrator
│   │   ├── state.py
│   │   ├── manager.py
│   │   └── recovery.py
│   ├── facebook/                   # Meta Graph API publishers (Reels & Stories)
│   │   ├── auth.py
│   │   ├── reels.py
│   │   └── stories.py
│   ├── youtube/                    # YouTube Data API v3 Shorts publisher (OAuth 2.0)
│   │   ├── auth.py
│   │   └── publisher.py
│   ├── tts/                        # Cloud TTS provider
│   │   ├── base.py
│   │   └── online.py
│   ├── video/                      # FFmpeg master renderer & quality verifier
│   │   ├── renderer.py
│   │   ├── quality.py
│   │   ├── processor.py
│   │   └── music.py
│   ├── ui/                         # Native Windows Tkinter GUI (<15MB RAM)
│   │   └── main_window.py
│   ├── utils/                      # Config, secret redaction, retries, temp cleanup
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── retry.py
│   │   └── cleanup.py
│   └── main.py                     # Entry point (GUI & CLI modes)
├── assets/
│   ├── music/                      # Background audio tracks (.mp3, .wav)
│   ├── sfx/                        # Sound effects
│   └── characters/                 # Custom character PNG layers
├── tests/                          # Automated Pytest suite
├── project_config.json             # Non-sensitive project settings
├── daily_job.json                  # Local job state persistence (no database)
├── .env.example                    # Secrets template
└── requirements.txt                # Dependencies
```

---

## ⚙️ Performance Profiles

The system automatically detects host hardware upon startup and applies the optimal performance profile:

| Profile | Target Hardware Specs | Resolution | FPS | Preset | Processing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LEGACY_LOW`** | NVIDIA MX110 2GB VRAM, i5 7th Gen, 8GB RAM | **720x1280 (9:16)** | **24** | `ultrafast` | Sequential, 1 job |
| **`LOW`** | Older 4GB GPU, 8GB RAM | **720x1280 (9:16)** | **24** | `veryfast` | Sequential |
| **`BALANCED`** | Modern 4GB-6GB GPU, 16GB RAM | **1080x1920 (9:16)** | **30** | `medium` | Parallel layers |
| **`HIGH`** | Modern 8GB+ GPU, 16-32GB RAM | **1080x1920 (9:16)** | **60** | `slow` | Full particle/blur |

---

## 🛠️ Quick Commands

```bash
# 1. Run Lightweight Windows GUI
python -m app.main

# 2. Run Headless CLI Mode (Dry-Run Test)
python -m app.main --cli --dry-run

# 3. Reset Today's Daily Job State
python -m app.main --reset-job

# 4. Run Pytest Automated Suite
python -m pytest
```

---

## 🔑 Security & Guidelines

- **No Heavy Local Models**: Cloud AI APIs (Gemini, Cloud TTS) are used to prevent overloading MX110 GPUs or 8GB RAM.
- **Zero Database**: Job state is stored statelssly in `daily_job.json`.
- **No Browser Automation**: Only official Meta Graph API and YouTube Data API endpoints are used.
#   F A  
 