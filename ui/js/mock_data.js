/* ==============================================================================
   MOCK DATASET FOR UI PROTOTYPE
   No real APIs or backend dependencies used. All state interfaces are mockable.
   ============================================================================== */

const MOCK_DATA = {
  app_version: "v2.4.0 • Windows x64",
  system_status: "Ready",
  auto_run_on_start: true,
  
  // Hardware & Performance Profile
  device: {
    computer_name: "DESKTOP-MX110-DEV",
    os: "Windows 11 Home 64-bit",
    cpu: "Intel Core i5-7200U @ 2.50GHz (4 Threads)",
    ram: "8 GB DDR4",
    gpu: "NVIDIA GeForce MX110",
    vram: "2 GB Dedicated GDDR5",
    cuda: "Available (CUDA 11.8)",
    driver_version: "536.23",
    current_profile: "LEGACY_LOW",
    profile_mode: "AUTO", // AUTO or MANUAL
    profile_reason: "Your system has limited VRAM (2GB) and RAM (8GB), so lightweight rendering and sequential processing are enabled."
  },

  // Today's Job State (Success Scenario)
  today_video_success: {
    date: "11 Aug 2026",
    topic: "AI Agents Are Changing How Programmers Code",
    summary: "A witty 2D cartoon debate between a senior cat engineer and a junior robot coder.",
    duration: "12 sec",
    resolution: "720 × 1280 (9:16)",
    status: "Published", // 'Published', 'Running', 'Pending', 'Failed'
    published_time: "10:32 AM",
    progress_percentage: 100,
    current_stage: "Cleanup Completed",
    platforms: {
      facebook_reel: { status: "Published", text: "✓ Reel Published" },
      youtube_shorts: { status: "Published", text: "✓ Shorts Published" },
      facebook_story: { status: "Not Available", text: "⚠ API Limitation (Page Story)" }
    },
    pipeline_steps: [
      { name: "TOPIC", status: "completed" },
      { name: "SCRIPT", status: "completed" },
      { name: "VOICE", status: "completed" },
      { name: "2D ANIMATION", status: "completed" },
      { name: "LIP SYNC", status: "completed" },
      { name: "RENDER", status: "completed" },
      { name: "FACEBOOK", status: "completed" },
      { name: "YOUTUBE", status: "completed" },
      { name: "CLEANUP", status: "completed" }
    ]
  },

  // Running State Mock
  today_video_running: {
    date: "11 Aug 2026",
    topic: "AI Agents Are Changing How Programmers Code",
    summary: "Generating 2D character mouth visemes and syncing subtitle keyframes...",
    duration: "12 sec",
    resolution: "720 × 1280 (9:16)",
    status: "Running",
    published_time: "--",
    progress_percentage: 62,
    current_stage: "2D Animation & Lip-Sync",
    platforms: {
      facebook_reel: { status: "Pending", text: "○ Queued" },
      youtube_shorts: { status: "Pending", text: "○ Queued" },
      facebook_story: { status: "Not Available", text: "⚠ API Limitation" }
    },
    pipeline_steps: [
      { name: "TOPIC", status: "completed" },
      { name: "SCRIPT", status: "completed" },
      { name: "VOICE", status: "completed" },
      { name: "2D ANIMATION", status: "current" },
      { name: "LIP SYNC", status: "pending" },
      { name: "RENDER", status: "pending" },
      { name: "FACEBOOK", status: "pending" },
      { name: "YOUTUBE", status: "pending" },
      { name: "CLEANUP", status: "pending" }
    ]
  },

  // Ready State Mock
  today_video_ready: {
    date: "11 Aug 2026",
    topic: "AI Coding Assistant Showdown",
    summary: "Ready to generate today's scheduled 10-15s cartoon short.",
    duration: "12 sec",
    resolution: "720 × 1280 (9:16)",
    status: "Pending",
    published_time: "--",
    progress_percentage: 0,
    current_stage: "Idle / Standing By",
    platforms: {
      facebook_reel: { status: "Pending", text: "○ Ready" },
      youtube_shorts: { status: "Pending", text: "○ Ready" },
      facebook_story: { status: "Not Available", text: "⚠ API Limitation" }
    },
    pipeline_steps: [
      { name: "TOPIC", status: "pending" },
      { name: "SCRIPT", status: "pending" },
      { name: "VOICE", status: "pending" },
      { name: "2D ANIMATION", status: "pending" },
      { name: "LIP SYNC", status: "pending" },
      { name: "RENDER", status: "pending" },
      { name: "FACEBOOK", status: "pending" },
      { name: "YOUTUBE", status: "pending" },
      { name: "CLEANUP", status: "pending" }
    ]
  },

  // Failed State Mock
  today_video_failed: {
    date: "11 Aug 2026",
    topic: "AI Agents Explained",
    summary: "Video rendered successfully, but YouTube upload timed out.",
    duration: "12 sec",
    resolution: "720 × 1280 (9:16)",
    status: "Failed",
    published_time: "--",
    progress_percentage: 88,
    current_stage: "YouTube Upload",
    platforms: {
      facebook_reel: { status: "Published", text: "✓ Reel Published" },
      youtube_shorts: { status: "Failed", text: "✕ Upload Failed" },
      facebook_story: { status: "Not Available", text: "⚠ API Limitation" }
    },
    pipeline_steps: [
      { name: "TOPIC", status: "completed" },
      { name: "SCRIPT", status: "completed" },
      { name: "VOICE", status: "completed" },
      { name: "2D ANIMATION", status: "completed" },
      { name: "LIP SYNC", status: "completed" },
      { name: "RENDER", status: "completed" },
      { name: "FACEBOOK", status: "completed" },
      { name: "YOUTUBE", status: "failed" },
      { name: "CLEANUP", status: "pending" }
    ]
  },

  // Job History
  jobs: [
    { id: "JOB-2026-0811", date: "11 Aug 2026", topic: "AI Agents Explained", status: "Published", facebook: true, youtube: true, duration: "12 sec" },
    { id: "JOB-2026-0810", date: "10 Aug 2026", topic: "AI Coding Tools Comparison", status: "Published", facebook: true, youtube: true, duration: "14 sec" },
    { id: "JOB-2026-0809", date: "09 Aug 2026", topic: "Robot Learns Bengali Cooking", status: "Published", facebook: true, youtube: true, duration: "11 sec" },
    { id: "JOB-2026-0808", date: "08 Aug 2026", topic: "Quantum Computing vs AI", status: "Published", facebook: true, youtube: true, duration: "13 sec" },
    { id: "JOB-2026-0807", date: "07 Aug 2026", topic: "Autonomous AI Flying Cars", status: "Failed", facebook: true, youtube: false, duration: "12 sec" },
    { id: "JOB-2026-0806", date: "06 Aug 2026", topic: "Why AI Cats Rule The Internet", status: "Published", facebook: true, youtube: true, duration: "15 sec" },
    { id: "JOB-2026-0805", date: "05 Aug 2026", topic: "AI Doctor vs Human Doctor", status: "Published", facebook: true, youtube: true, duration: "10 sec" }
  ],

  // Analytics
  analytics: {
    videos_published_total: 7,
    this_week: 7,
    facebook_success: "7 / 7",
    youtube_success: "7 / 7",
    success_rate: "100%",
    avg_render_time: "42s",
    avg_video_size: "3.6 MB"
  },

  // YouTube Connection
  youtube: {
    connected: true,
    channel_name: "My AI Cartoon Channel",
    channel_id: "UC••••••••••••••••",
    handle: "@Life-X-873",
    privacy: "Public",
    auto_publish: true,
    upload_type: "YouTube Shorts",
    latest_upload: {
      title: "AI Agents Explained 🤖 #Shorts",
      date: "11 Aug 2026",
      status: "Published",
      views: "1.4k"
    }
  },

  // Facebook Connection
  facebook: {
    connected: true,
    page_name: "My AI Cartoon Page",
    page_id: "61593188125705",
    reel_enabled: true,
    story_enabled: true,
    story_api_available: false,
    story_warning_text: "Facebook Story publishing is currently unavailable through the official Meta Graph API for Page Story videos. Reel publishing remains active."
  },

  // AI Providers & Settings
  settings: {
    auto_run_startup: true,
    start_windows: false,
    daily_automation: true,
    niche: "AI & Technology",
    language: "English",
    duration: "10–15 sec",
    character_style: "2D Cartoon",
    voice_style: "Friendly",
    subtitle_style: "Bold Yellow",
    providers: {
      gemini: { connected: true, key_masked: "●●●●●●●●●●●●●●●●" },
      openai: { connected: false, key_masked: "●●●●●●●●●●●●●●●●" },
      tts: { connected: true, key_masked: "●●●●●●●●●●●●●●●●" }
    }
  },

  // Console Logs
  logs: [
    "10:00:01  Application UI started in Windows desktop mode",
    "10:00:02  Hardware detected: Intel i5-7200U (4 threads) | 8GB RAM | NVIDIA MX110 2GB",
    "10:00:02  Profile classified: LEGACY_LOW (Lightweight rendering active)",
    "10:00:05  Today's daily job created (JOB-2026-0811)",
    "10:00:12  Topic generated: AI Agents Are Changing How Programmers Code",
    "10:00:20  Dialogue script generated (2-character humorous exchange)",
    "10:00:30  TTS voice audio synthesized with viseme timestamp extraction",
    "10:00:45  2D Character viseme animation frames rendered into buffer",
    "10:01:10  Master single FFmpeg render completed -> output/final.mp4",
    "10:01:12  Pre-upload quality check PASSED (720x1280, 24fps, yuv420p, audio sync)",
    "10:01:20  Published to Facebook Reel (Page 61593188125705)",
    "10:01:35  Published to YouTube Shorts (@Life-X-873)",
    "10:01:36  Temporary render frames purged cleanly. State saved to daily_job.json"
  ]
};
