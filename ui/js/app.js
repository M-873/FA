/* ==============================================================================
   UI APPLICATION CONTROLLER & STATE MANAGER
   Clean, decoupled frontend controller. No real APIs / backend required.
   ============================================================================== */

// Active State Tracker
let currentUIState = 'SUCCESS'; // 'SUCCESS', 'RUNNING', 'READY', 'FAILED', 'DISCONNECTED'
let isPlayingVideo = false;
let videoTimer = null;
let currentVideoSec = 5;
const TOTAL_VIDEO_SEC = 12;

// Wizard State Tracker
let currentWizardStep = 1;
const TOTAL_WIZARD_STEPS = 6;

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initThemeToggle();
  initStateSwitcher();
  initWizard();
  
  // Initial Render
  applyUIState(currentUIState);
  renderJobsTable();
  renderAnalytics();
  renderYouTubePage();
  renderFacebookPage();
  renderDevicePage();
  renderSettingsPage();
  renderLogsConsole();
  initPhase1Dashboard();
});

/* ------------------------------------------------------------------------------
   1. NAVIGATION SYSTEM
   ------------------------------------------------------------------------------ */
function initNavigation() {
  const navItems = document.querySelectorAll('#sidebar-nav .nav-item');
  const pageViews = document.querySelectorAll('.page-view');
  const titleText = document.getElementById('current-page-title');
  const subtitleText = document.getElementById('current-page-subtitle');

  const pageSubtitles = {
    'dashboard': "Daily Automation Overview & Platform Telemetry",
    'todays-video': "Master 9:16 Video Metadata & Multi-Platform Status",
    'jobs': "Job Ledger & Multi-Platform Upload History",
    'analytics': "Performance Metrics & Daily Video Cadence",
    'youtube': "YouTube Data API v3 Shorts Publisher Settings",
    'facebook': "Meta Graph API Reels & Story Settings",
    'settings': "General Configuration, Voice, Subtitles & AI Providers",
    'device': "Host Hardware Telemetry & Performance Profiles"
  };

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const pageId = item.getAttribute('data-page');

      navItems.forEach(n => n.classList.remove('active'));
      pageViews.forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      const targetPage = document.getElementById(`page-${pageId}`);
      if (targetPage) targetPage.classList.add('active');

      if (titleText) titleText.textContent = item.querySelector('span:last-child').textContent.trim();
      if (subtitleText && pageSubtitles[pageId]) subtitleText.textContent = pageSubtitles[pageId];
    });
  });
}

/* ------------------------------------------------------------------------------
   2. THEME CONTROLLER (LIGHT / DARK)
   ------------------------------------------------------------------------------ */
function initThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle-btn');
  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    toggleBtn.textContent = newTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
    UIComponents.showToast(`Switched to ${newTheme.toUpperCase()} theme`, 'info');
  });
}

/* ------------------------------------------------------------------------------
   3. PROTOTYPE STATE DEMO SWITCHER
   ------------------------------------------------------------------------------ */
function initStateSwitcher() {
  const switcher = document.getElementById('ui-state-switcher');
  if (!switcher) return;

  switcher.addEventListener('change', (e) => {
    applyUIState(e.target.value);
  });
}

function applyUIState(stateKey) {
  currentUIState = stateKey;
  let jobData = MOCK_DATA.today_video_success;
  
  const statusBadge = document.getElementById('dash-status-badge');
  const statusMsg = document.getElementById('dash-status-msg');
  const runBtn = document.getElementById('dash-run-btn');
  const errorCard = document.getElementById('dash-error-card');
  const sideDot = document.getElementById('sidebar-status-dot');
  const sideText = document.getElementById('sidebar-status-text');
  const bottomDot = document.getElementById('bottom-status-dot');
  const bottomText = document.getElementById('bottom-status-text');
  const bottomStage = document.getElementById('bottom-stage-text');
  const bottomProgressBox = document.getElementById('bottom-progress-box');
  const bottomProgressFill = document.getElementById('bottom-progress-fill');
  const bottomProgressLabel = document.getElementById('bottom-progress-label');

  // Answer strip elements
  const ans1 = document.getElementById('ux-ans-1');
  const ans2 = document.getElementById('ux-ans-2');
  const ans3 = document.getElementById('ux-ans-3');
  const ans4 = document.getElementById('ux-ans-4');
  const ans5 = document.getElementById('ux-ans-5');

  if (stateKey === 'SUCCESS') {
    jobData = MOCK_DATA.today_video_success;
    statusBadge.className = 'badge badge-success';
    statusBadge.textContent = '● COMPLETED';
    statusMsg.textContent = `Published successfully today at ${jobData.published_time}.`;
    runBtn.className = 'btn btn-secondary';
    runBtn.textContent = '▶ RUN AGAIN (RE-RUN TODAY)';
    if (errorCard) errorCard.style.display = 'none';

    sideDot.className = 'status-dot-mini success';
    sideText.textContent = 'System Ready';
    bottomDot.className = 'live-status-dot success';
    bottomText.textContent = '● System Ready';
    bottomStage.textContent = '| Standby (Next Run: 06:00 AM)';
    if (bottomProgressBox) bottomProgressBox.style.display = 'none';

    if (ans1) ans1.innerHTML = '<span class="badge badge-success">✓ Completed</span>';
    if (ans2) ans2.innerHTML = '<span class="badge badge-neutral">Standby</span>';
    if (ans3) ans3.innerHTML = '<span class="badge badge-success">✓ Published</span>';
    if (ans4) ans4.innerHTML = '<span class="badge badge-success">✓ Published</span>';
    if (ans5) ans5.innerHTML = '<span class="badge badge-success">● Ready for Tomorrow</span>';

  } else if (stateKey === 'RUNNING') {
    jobData = MOCK_DATA.today_video_running;
    statusBadge.className = 'badge badge-warning';
    statusBadge.textContent = '🟡 GENERATING TODAY\'S VIDEO...';
    statusMsg.textContent = `Current Stage: ${jobData.current_stage} (${jobData.progress_percentage}%)`;
    runBtn.className = 'btn btn-secondary';
    runBtn.textContent = '⏳ GENERATING IN PROGRESS...';
    if (errorCard) errorCard.style.display = 'none';

    sideDot.className = 'status-dot-mini warning';
    sideText.textContent = 'Generating Video...';
    bottomDot.className = 'live-status-dot warning';
    bottomText.textContent = '🟡 Generating Video...';
    bottomStage.textContent = `| Stage: ${jobData.current_stage}`;
    if (bottomProgressBox) {
      bottomProgressBox.style.display = 'flex';
      bottomProgressFill.style.width = `${jobData.progress_percentage}%`;
      bottomProgressLabel.textContent = `Progress: ${jobData.progress_percentage}%`;
    }

    if (ans1) ans1.innerHTML = '<span class="badge badge-warning">🟡 In Progress</span>';
    if (ans2) ans2.innerHTML = '<span class="badge badge-warning">2D Animation</span>';
    if (ans3) ans3.innerHTML = '<span class="badge badge-neutral">○ Queued</span>';
    if (ans4) ans4.innerHTML = '<span class="badge badge-neutral">○ Queued</span>';
    if (ans5) ans5.innerHTML = '<span class="badge badge-neutral">In Execution</span>';

  } else if (stateKey === 'READY') {
    jobData = MOCK_DATA.today_video_ready;
    statusBadge.className = 'badge badge-neutral';
    statusBadge.textContent = '○ READY TO GENERATE';
    statusMsg.textContent = "Today's daily AI video automation is ready to start.";
    runBtn.className = 'btn btn-primary';
    runBtn.textContent = '▶ RUN TODAY\'S AUTOMATION';
    if (errorCard) errorCard.style.display = 'none';

    sideDot.className = 'status-dot-mini success';
    sideText.textContent = 'System Ready';
    bottomDot.className = 'live-status-dot success';
    bottomText.textContent = '● System Ready';
    bottomStage.textContent = '| Ready to Generate';
    if (bottomProgressBox) bottomProgressBox.style.display = 'none';

    if (ans1) ans1.innerHTML = '<span class="badge badge-neutral">○ Ready</span>';
    if (ans2) ans2.innerHTML = '<span class="badge badge-neutral">Idle</span>';
    if (ans3) ans3.innerHTML = '<span class="badge badge-neutral">○ Ready</span>';
    if (ans4) ans4.innerHTML = '<span class="badge badge-neutral">○ Ready</span>';
    if (ans5) ans5.innerHTML = '<span class="badge badge-success">● Ready</span>';

  } else if (stateKey === 'FAILED') {
    jobData = MOCK_DATA.today_video_failed;
    statusBadge.className = 'badge badge-danger';
    statusBadge.textContent = '✕ AUTOMATION FAILED';
    statusMsg.textContent = "Error occurred during YouTube upload step. Retry is available.";
    runBtn.className = 'btn btn-danger';
    runBtn.textContent = '🔄 RETRY TODAY\'S AUTOMATION';
    if (errorCard) errorCard.style.display = 'flex';

    sideDot.className = 'status-dot-mini danger';
    sideText.textContent = 'Automation Failed';
    bottomDot.className = 'live-status-dot danger';
    bottomText.textContent = '✕ Upload Error';
    bottomStage.textContent = '| YouTube Quota Exceeded';
    if (bottomProgressBox) bottomProgressBox.style.display = 'none';

    if (ans1) ans1.innerHTML = '<span class="badge badge-danger">✕ Failed</span>';
    if (ans2) ans2.innerHTML = '<span class="badge badge-danger">YouTube Upload</span>';
    if (ans3) ans3.innerHTML = '<span class="badge badge-success">✓ Published</span>';
    if (ans4) ans4.innerHTML = '<span class="badge badge-danger">✕ Failed</span>';
    if (ans5) ans5.innerHTML = '<span class="badge badge-warning">Retry Needed</span>';

  } else if (stateKey === 'DISCONNECTED') {
    statusBadge.className = 'badge badge-neutral';
    statusBadge.textContent = '⚪ DISCONNECTED';
    statusMsg.textContent = "Social API accounts disconnected. Reconnection required.";
    runBtn.className = 'btn btn-secondary';
    runBtn.textContent = '⚙ CONFIGURE CONNECTIONS';
    if (errorCard) errorCard.style.display = 'none';

    sideDot.className = 'status-dot-mini neutral';
    sideText.textContent = 'Disconnected';
    bottomDot.className = 'live-status-dot neutral';
    bottomText.textContent = '⚪ Disconnected';
    bottomStage.textContent = '| Accounts Unlinked';

    if (ans1) ans1.innerHTML = '<span class="badge badge-neutral">--</span>';
    if (ans2) ans2.innerHTML = '<span class="badge badge-neutral">Offline</span>';
    if (ans3) ans3.innerHTML = '<span class="badge badge-danger">○ Disconnected</span>';
    if (ans4) ans4.innerHTML = '<span class="badge badge-danger">○ Disconnected</span>';
    if (ans5) ans5.innerHTML = '<span class="badge badge-warning">Action Required</span>';
  }

  // Render Visual Pipeline
  UIComponents.renderPipeline('dash-pipeline-container', jobData.pipeline_steps);

  // Render Today's Video Page Details
  renderTodaysVideo(jobData);
}

/* ------------------------------------------------------------------------------
   4. TODAY'S VIDEO PAGE RENDERER
   ------------------------------------------------------------------------------ */
function renderTodaysVideo(jobData) {
  if (!jobData) jobData = MOCK_DATA.today_video_success;

  const topicText = document.getElementById('tv-topic-text');
  const durationVal = document.getElementById('tv-duration-val');
  const resVal = document.getElementById('tv-res-val');
  const statusBadge = document.getElementById('tv-status-badge');
  const fbReelStatus = document.getElementById('tv-fb-reel-status');
  const ytShortsStatus = document.getElementById('tv-yt-shorts-status');
  const fbStoryStatus = document.getElementById('tv-fb-story-status');

  if (topicText) topicText.textContent = `"${jobData.topic}"`;
  if (durationVal) durationVal.textContent = jobData.duration;
  if (resVal) resVal.textContent = jobData.resolution;
  
  if (statusBadge) {
    if (jobData.status === 'Published') {
      statusBadge.className = 'badge badge-success';
      statusBadge.textContent = '● Published';
    } else if (jobData.status === 'Running') {
      statusBadge.className = 'badge badge-warning';
      statusBadge.textContent = '🟡 Running';
    } else if (jobData.status === 'Failed') {
      statusBadge.className = 'badge badge-danger';
      statusBadge.textContent = '✕ Failed';
    } else {
      statusBadge.className = 'badge badge-neutral';
      statusBadge.textContent = '○ Pending';
    }
  }

  if (fbReelStatus) fbReelStatus.textContent = jobData.platforms.facebook_reel.text;
  if (ytShortsStatus) ytShortsStatus.textContent = jobData.platforms.youtube_shorts.text;
  if (fbStoryStatus) fbStoryStatus.textContent = jobData.platforms.facebook_story.text;
}

/* ------------------------------------------------------------------------------
   5. VIDEO PREVIEW PLAYER CONTROLS (MOCK CANVAS)
   ------------------------------------------------------------------------------ */
function togglePlayPreview() {
  const playBtn = document.getElementById('player-play-btn');
  const progressFill = document.getElementById('player-progress-bar');
  const timeDisp = document.getElementById('player-time-display');

  if (isPlayingVideo) {
    // Pause
    isPlayingVideo = false;
    if (playBtn) playBtn.textContent = '▶';
    if (videoTimer) clearInterval(videoTimer);
    UIComponents.showToast('Preview Paused', 'info');
  } else {
    // Play
    isPlayingVideo = true;
    if (playBtn) playBtn.textContent = '⏸';
    UIComponents.showToast('Playing 9:16 Cartoon Preview', 'info');

    videoTimer = setInterval(() => {
      currentVideoSec += 1;
      if (currentVideoSec > TOTAL_VIDEO_SEC) {
        currentVideoSec = 0;
      }
      const pct = (currentVideoSec / TOTAL_VIDEO_SEC) * 100;
      if (progressFill) progressFill.style.width = `${pct}%`;
      if (timeDisp) {
        const secStr = currentVideoSec < 10 ? `0${currentVideoSec}` : currentVideoSec;
        timeDisp.textContent = `00:${secStr} / 00:${TOTAL_VIDEO_SEC}`;
      }
    }, 1000);
  }
}

function restartPreview() {
  currentVideoSec = 0;
  const progressFill = document.getElementById('player-progress-bar');
  const timeDisp = document.getElementById('player-time-display');
  if (progressFill) progressFill.style.width = '0%';
  if (timeDisp) timeDisp.textContent = `00:00 / 00:${TOTAL_VIDEO_SEC}`;
  UIComponents.showToast('Restarted preview from start', 'info');
}

function toggleMute() {
  UIComponents.showToast('Audio Muted / Unmuted', 'info');
}

/* ------------------------------------------------------------------------------
   6. JOBS LEDGER & ANALYTICS
   ------------------------------------------------------------------------------ */
function renderJobsTable() {
  UIComponents.renderJobsTable('jobs-table-body', MOCK_DATA.jobs);
}

function renderAnalytics() {
  const a = MOCK_DATA.analytics;
  const total = document.getElementById('an-val-total');
  const week = document.getElementById('an-val-week');
  const fb = document.getElementById('an-val-fb');
  const yt = document.getElementById('an-val-yt');
  const rate = document.getElementById('an-val-rate');

  if (total) total.textContent = a.videos_published_total;
  if (week) week.textContent = a.this_week;
  if (fb) fb.textContent = a.facebook_success;
  if (yt) yt.textContent = a.youtube_success;
  if (rate) rate.textContent = `${a.success_rate} SUCCESS RATE`;
}

/* ------------------------------------------------------------------------------
   7. YOUTUBE & FACEBOOK PAGES
   ------------------------------------------------------------------------------ */
function renderYouTubePage() {
  const yt = MOCK_DATA.youtube;
  const cName = document.getElementById('yt-channel-name');
  const cHandle = document.getElementById('yt-channel-handle');
  const lTitle = document.getElementById('yt-latest-title');
  const lMeta = document.getElementById('yt-latest-meta');

  if (cName) cName.textContent = yt.channel_name;
  if (cHandle) cHandle.textContent = yt.handle;
  if (lTitle) lTitle.textContent = yt.latest_upload.title;
  if (lMeta) lMeta.textContent = `Published: ${yt.latest_upload.date} • Views: ${yt.latest_upload.views} • Status: ✓ ${yt.latest_upload.status}`;
}

function renderFacebookPage() {
  const fb = MOCK_DATA.facebook;
  const pName = document.getElementById('fb-page-name');
  const pId = document.getElementById('fb-page-id');

  if (pName) pName.textContent = fb.page_name;
  if (pId) pId.textContent = `Page ID: ${fb.page_id}`;
}

/* ------------------------------------------------------------------------------
   8. DEVICE & PERFORMANCE PROFILE PAGE
   ------------------------------------------------------------------------------ */
function renderDevicePage() {
  const d = MOCK_DATA.device;
  const comp = document.getElementById('dev-computer');
  const os = document.getElementById('dev-os');
  const cpu = document.getElementById('dev-cpu');
  const ram = document.getElementById('dev-ram');
  const gpu = document.getElementById('dev-gpu');
  const vram = document.getElementById('dev-vram');
  const cuda = document.getElementById('dev-cuda');
  const driver = document.getElementById('dev-driver');
  const profName = document.getElementById('dev-profile-name');
  const profReason = document.getElementById('dev-profile-reason');

  if (comp) comp.textContent = d.computer_name;
  if (os) os.textContent = d.os;
  if (cpu) cpu.textContent = d.cpu;
  if (ram) ram.textContent = d.ram;
  if (gpu) gpu.textContent = d.gpu;
  if (vram) vram.textContent = d.vram;
  if (cuda) cuda.textContent = d.cuda;
  if (driver) driver.textContent = d.driver_version;
  if (profName) profName.textContent = `${d.current_profile} Profile Active`;
  if (profReason) profReason.textContent = `"${d.profile_reason}"`;
}

function renderSettingsPage() {
  // Settings values are static / mock controls
}

/* ------------------------------------------------------------------------------
   9. LOG CONSOLE & MODAL
   ------------------------------------------------------------------------------ */
function renderLogsConsole() {
  UIComponents.renderLogs('log-console-text', MOCK_DATA.logs);
}

function openLogsModal() {
  const modal = document.getElementById('logs-modal');
  if (modal) modal.classList.add('open');
}

function closeLogsModal() {
  const modal = document.getElementById('logs-modal');
  if (modal) modal.classList.remove('open');
}

function copyLogsToClipboard() {
  const text = MOCK_DATA.logs.join('\n');
  navigator.clipboard.writeText(text).then(() => {
    UIComponents.showToast('✓ Logs copied to clipboard!', 'success');
  }).catch(() => {
    UIComponents.showToast('Logs copied', 'info');
  });
}

function clearLogConsole() {
  const container = document.getElementById('log-console-text');
  if (container) container.innerHTML = '<div class="log-line log-info">[Console logs cleared by user]</div>';
  UIComponents.showToast('Log console cleared', 'info');
}

/* ------------------------------------------------------------------------------
   10. ONBOARDING WIZARD
   ------------------------------------------------------------------------------ */
function initWizard() {
  // Wizard initializes step 1
}

function openOnboardingModal() {
  currentWizardStep = 1;
  updateWizardUI();
  const modal = document.getElementById('onboarding-modal');
  if (modal) modal.classList.add('open');
}

function closeOnboardingModal() {
  const modal = document.getElementById('onboarding-modal');
  if (modal) modal.classList.remove('open');
  UIComponents.showToast('✓ Onboarding completed successfully!', 'success');
}

function wizardNextStep() {
  if (currentWizardStep < TOTAL_WIZARD_STEPS) {
    currentWizardStep += 1;
    updateWizardUI();
  }
}

function wizardPrevStep() {
  if (currentWizardStep > 1) {
    currentWizardStep -= 1;
    updateWizardUI();
  }
}

function updateWizardUI() {
  // Update step indicators
  const stepTags = document.querySelectorAll('.wiz-step');
  stepTags.forEach((tag, idx) => {
    if (idx + 1 === currentWizardStep) {
      tag.classList.add('active');
    } else {
      tag.classList.remove('active');
    }
  });

  // Update step bodies
  for (let i = 1; i <= TOTAL_WIZARD_STEPS; i++) {
    const body = document.getElementById(`wiz-step-i`);
    const target = document.getElementById(`wiz-step-${i}`);
    if (target) {
      target.classList.toggle('active', i === currentWizardStep);
    }
  }

  // Buttons
  const prevBtn = document.getElementById('wiz-prev-btn');
  const nextBtn = document.getElementById('wiz-next-btn');
  const doneBtn = document.getElementById('wiz-done-btn');

  if (prevBtn) prevBtn.style.display = currentWizardStep > 1 ? 'inline-flex' : 'none';
  if (nextBtn) nextBtn.style.display = currentWizardStep < TOTAL_WIZARD_STEPS ? 'inline-flex' : 'none';
  if (doneBtn) doneBtn.style.display = currentWizardStep === TOTAL_WIZARD_STEPS ? 'inline-flex' : 'none';
}

/* ------------------------------------------------------------------------------
   11. RUN TODAY'S AUTOMATION CLICK HANDLER (PROTOTYPE DEMO SIMULATION)
   ------------------------------------------------------------------------------ */
function handleRunAutomationClick() {
  if (currentUIState === 'RUNNING') {
    UIComponents.showToast('Automation is already currently running...', 'warning');
    return;
  }

  // Switch to RUNNING State
  UIComponents.showToast("Starting today's daily 2D cartoon automation pipeline...", "info");
  const switcher = document.getElementById('ui-state-switcher');
  if (switcher) switcher.value = 'RUNNING';
  applyUIState('RUNNING');

  // Simulate Progress Transitions
  setTimeout(() => {
    UIComponents.showToast("✓ Script & Viseme TTS generated. Master video rendering...", "info");
  }, 1400);

  setTimeout(() => {
    UIComponents.showToast("✓ Published to Facebook Reel (Page 61593188125705) & YouTube Shorts!", "success");
    if (switcher) switcher.value = 'SUCCESS';
    applyUIState('SUCCESS');
  }, 3200);
}

// Global shortcut for toasts
function showToast(msg, type) {
  UIComponents.showToast(msg, type);
}

/* ==============================================================================
   PHASE 1 DASHBOARD CONTROLLER & STATE
   Independent toggles, local persistence via localStorage, and mock job queue.
   ============================================================================== */
let webDapEnabled = localStorage.getItem('phase1_dap_enabled') === 'true';
let webLtrEnabled = localStorage.getItem('phase1_ltr_enabled') === 'true';
let webActiveFilter = 'ALL';

let webReelsJobs = JSON.parse(localStorage.getItem('phase1_reels_jobs')) || [
  {
    id: "reel_job_101",
    url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    status: "COMPLETED",
    progress: 100,
    created_at: "Today, 10:15 AM",
    note: "Mock highlight reel rendered (Demo)"
  },
  {
    id: "reel_job_102",
    url: "https://vimeo.com/76979871",
    status: "PROCESSING",
    progress: 65,
    created_at: "Today, 11:20 AM",
    note: "Simulating highlight extraction (Demo)"
  },
  {
    id: "reel_job_103",
    url: "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
    status: "QUEUED",
    progress: 0,
    created_at: "Today, 11:45 AM",
    note: "Waiting in simulated queue"
  },
  {
    id: "reel_job_104",
    url: "https://www.youtube.com/watch?v=2vjPBrBU-TM",
    status: "FAILED",
    progress: 25,
    created_at: "Yesterday, 04:30 PM",
    note: "Mock Error: Simulated video stream timeout"
  }
];

function initPhase1Dashboard() {
  const dapToggle = document.getElementById('web-dap-toggle');
  const ltrToggle = document.getElementById('web-ltr-toggle');
  if (dapToggle) dapToggle.checked = webDapEnabled;
  if (ltrToggle) ltrToggle.checked = webLtrEnabled;

  updateWebDapUI();
  updateWebLtrUI();
  renderWebJobs();
  updateWebHardwareUI();
}

const DEFAULT_HW_DATA = {
  gpu: "NVIDIA GeForce MX110",
  vram: "2048 MB Dedicated (GDDR5)",
  ram: "7.89 GB Total (1.49 GB Available)",
  cpu: "Intel Core i5-7200U @ 2.50GHz (4 Threads)",
  os: "Windows 10 Home (Build 19045) AMD64",
  disk: "80.7 GB Free / 237.7 GB Total",
  cuda: "CUDA Ready (Driver 531.79)",
  profile: "LEGACY_2GB",
  status: "DETECTED",
  rationale: "Target Low-Resource Hardware (NVIDIA GeForce MX110 target GPU detected, 2048 MB dedicated VRAM, 7.9 GB system RAM). Classified as LEGACY_2GB. Local Ollama and heavy AI video rendering strictly disabled.",
  bottlenecks: "Low dedicated VRAM (2048 MB) • Limited system RAM (7.9 GB) • Low currently available RAM (1.5 GB)"
};

function updateWebHardwareUI(data = DEFAULT_HW_DATA) {
  const badge = document.getElementById('web-hw-status-badge');
  const gpu = document.getElementById('web-hw-gpu');
  const vram = document.getElementById('web-hw-vram');
  const ram = document.getElementById('web-hw-ram');
  const cpu = document.getElementById('web-hw-cpu');
  const os = document.getElementById('web-hw-os');
  const disk = document.getElementById('web-hw-disk');
  const cuda = document.getElementById('web-hw-cuda');
  const profileBadge = document.getElementById('web-hw-profile-badge');
  const rationale = document.getElementById('web-hw-rationale');
  const bottlenecks = document.getElementById('web-hw-bottlenecks');

  if (badge) {
    badge.className = data.status === 'DETECTED' ? 'badge badge-success' : 'badge badge-warning';
    badge.textContent = `● ${data.status}`;
  }
  if (gpu) gpu.textContent = data.gpu;
  if (vram) vram.textContent = data.vram;
  if (ram) ram.textContent = data.ram;
  if (cpu) cpu.textContent = data.cpu;
  if (os) os.textContent = data.os;
  if (disk) disk.textContent = data.disk;
  if (cuda) cuda.textContent = data.cuda;
  if (profileBadge) {
    profileBadge.className = 'badge badge-warning';
    profileBadge.textContent = data.profile;
  }
  if (rationale) rationale.textContent = data.rationale;
  if (bottlenecks) bottlenecks.textContent = data.bottlenecks;
}

function handleWebRefreshHardware() {
  const btn = document.querySelector('#page-dashboard button[onclick="handleWebRefreshHardware()"]');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Scanning...';
  }

  setTimeout(() => {
    updateWebHardwareUI(DEFAULT_HW_DATA);
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🔄 Refresh';
    }
    showToast('Hardware detection completed: classified as LEGACY_2GB', 'success');
  }, 600);
}

function handleWebDapToggle(checked) {
  webDapEnabled = Boolean(checked);
  localStorage.setItem('phase1_dap_enabled', webDapEnabled);
  updateWebDapUI();
  showToast(`Daily Auto Post is now ${webDapEnabled ? 'ON' : 'OFF'}`, webDapEnabled ? 'success' : 'info');
}

function updateWebDapUI() {
  const badge = document.getElementById('web-dap-status-badge');
  const nextRun = document.getElementById('web-dap-next-run');
  if (badge) {
    badge.className = webDapEnabled ? 'badge badge-success' : 'badge badge-neutral';
    badge.textContent = webDapEnabled ? '● ON' : '○ OFF';
  }
  if (nextRun) {
    nextRun.textContent = webDapEnabled ? 'Tomorrow, 09:00 AM (Scheduled)' : 'Disabled / Standing by';
    nextRun.style.color = webDapEnabled ? '#60A5FA' : 'var(--text-muted)';
  }
}

function handleWebLtrToggle(checked) {
  webLtrEnabled = Boolean(checked);
  localStorage.setItem('phase1_ltr_enabled', webLtrEnabled);
  updateWebLtrUI();
  showToast(`Link to Reels is now ${webLtrEnabled ? 'ON' : 'OFF'}`, webLtrEnabled ? 'success' : 'info');
}

function updateWebLtrUI() {
  const badge = document.getElementById('web-ltr-status-badge');
  if (badge) {
    badge.className = webLtrEnabled ? 'badge badge-success' : 'badge badge-neutral';
    badge.textContent = webLtrEnabled ? '● ON' : '○ OFF';
  }
}

function handleWebAddReelsLink() {
  const input = document.getElementById('web-reels-url-input');
  const msg = document.getElementById('web-reels-validation-msg');
  if (!input || !msg) return;

  const url = input.value.trim();
  if (!url) {
    msg.textContent = '⚠️ URL cannot be empty. Please enter a video link.';
    msg.style.color = 'var(--status-danger)';
    return;
  }

  // URL format validation
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      throw new Error();
    }
  } catch (e) {
    msg.textContent = '⚠️ Invalid video URL. Please enter a valid HTTP/HTTPS link (e.g. https://www.youtube.com/watch?v=...)';
    msg.style.color = 'var(--status-danger)';
    return;
  }

  // Valid URL - Add mock job
  const newJob = {
    id: `reel_job_${webReelsJobs.length + 101}`,
    url: url,
    status: 'QUEUED',
    progress: 0,
    created_at: 'Just now',
    note: 'Queued for highlight analysis (Phase 1 Mock)'
  };

  webReelsJobs.unshift(newJob);
  localStorage.setItem('phase1_reels_jobs', JSON.stringify(webReelsJobs));

  input.value = '';
  msg.textContent = `✓ Valid video link added to queue as ${newJob.id}. (Phase 1 Mock Simulation)`;
  msg.style.color = 'var(--status-success)';

  renderWebJobs();
  showToast(`Mock job ${newJob.id} added to queue!`, 'success');
}

function filterWebJobs(filterName, btn) {
  webActiveFilter = filterName.toUpperCase();
  document.querySelectorAll('#page-dashboard .btn-secondary').forEach(b => b.classList.remove('active-filter'));
  if (btn) btn.classList.add('active-filter');
  renderWebJobs();
}

function renderWebJobs() {
  const list = document.getElementById('web-reels-jobs-list');
  if (!list) return;

  let filtered = webReelsJobs;
  if (webActiveFilter !== 'ALL') {
    filtered = webReelsJobs.filter(j => j.status === webActiveFilter);
  }

  if (filtered.length === 0) {
    list.innerHTML = '<div style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 13px;">No jobs found in this category.</div>';
    return;
  }

  list.innerHTML = filtered.map(job => {
    let badgeClass = 'badge-neutral';
    if (job.status === 'COMPLETED') badgeClass = 'badge-success';
    else if (job.status === 'PROCESSING') badgeClass = 'badge-warning';
    else if (job.status === 'QUEUED') badgeClass = 'badge-neutral';
    else if (job.status === 'FAILED') badgeClass = 'badge-danger';

    return `
      <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-card-inner); padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        <div style="flex: 1; min-width: 0; padding-right: 12px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: monospace; font-weight: 700; color: var(--accent-cyan); font-size: 13px;">${job.id}</span>
            <span style="font-size: 11px; color: var(--text-muted);">• ${job.created_at}</span>
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            🔗 ${job.url}
          </div>
          <div style="font-size: 11px; color: var(--text-muted); font-style: italic;">
            ${job.note || ''}
          </div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
          <div style="display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary);">
            <span>${job.progress}%</span>
            <div style="width: 50px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
              <div style="width: ${job.progress}%; height: 100%; background: var(--accent-cyan);"></div>
            </div>
          </div>
          <span class="badge ${badgeClass}" style="font-size: 10px;">${job.status}</span>
        </div>
      </div>
    `;
  }).join('');
}
