/* ==============================================================================
   UI COMPONENTS & MODULAR CONTROLLERS
   Clean, reusable UI rendering functions separated from business logic.
   ============================================================================== */

const UIComponents = {
  
  /**
   * Renders the 9-stage visual automation pipeline
   * @param {string} containerId 
   * @param {Array} steps 
   */
  renderPipeline(containerId, steps) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '<div class="pipeline-track">';
    steps.forEach((step, idx) => {
      let stateClass = step.status; // 'completed', 'current', 'pending', 'failed'
      let icon = '○';
      if (stateClass === 'completed') icon = '✓';
      else if (stateClass === 'failed') icon = '✕';
      else if (stateClass === 'current') icon = '●';
      else icon = (idx + 1);

      html += `
        <div class="pipeline-step ${stateClass}">
          <div class="step-circle">${icon}</div>
          <div class="step-label">${step.name}</div>
          <div class="step-status-sub">${stateClass.toUpperCase()}</div>
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;
  },

  /**
   * Renders a toast notification
   * @param {string} message 
   * @param {'success'|'warning'|'danger'|'info'} type 
   */
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = 'ℹ';
    if (type === 'success') icon = '✓';
    else if (type === 'warning') icon = '⚠️';
    else if (type === 'danger') icon = '✕';

    toast.innerHTML = `
      <span class="toast-icon">${icon}</span>
      <span class="toast-msg">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3800);
  },

  /**
   * Renders the jobs ledger table
   * @param {string} tbodyId 
   * @param {Array} jobs 
   */
  renderJobsTable(tbodyId, jobs) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    let html = '';
    jobs.forEach(job => {
      const isSuccess = job.status === 'Published';
      const statusBadge = isSuccess 
        ? '<span class="badge badge-success">● Published</span>' 
        : '<span class="badge badge-danger">✕ Failed</span>';
      
      const fbStatus = job.facebook 
        ? '<span style="color: var(--status-success); font-weight: 600;">✓ Published</span>' 
        : '<span style="color: var(--status-danger); font-weight: 600;">✕ Failed</span>';
      
      const ytStatus = job.youtube 
        ? '<span style="color: var(--status-success); font-weight: 600;">✓ Published</span>' 
        : '<span style="color: var(--status-danger); font-weight: 600;">✕ Failed</span>';

      const actionBtn = isSuccess
        ? `<button class="btn btn-secondary btn-xs" onclick="UIComponents.showToast('Viewing job details for ${job.id}', 'info')">View</button>`
        : `<button class="btn btn-danger btn-xs" onclick="UIComponents.showToast('Retrying job ${job.id}...', 'warning')">Retry</button>`;

      html += `
        <tr>
          <td style="font-weight: 700; color: var(--text-primary);">${job.date}</td>
          <td><b>${job.topic}</b></td>
          <td>${statusBadge}</td>
          <td>${fbStatus}</td>
          <td>${ytStatus}</td>
          <td><span class="badge badge-neutral">${job.duration}</span></td>
          <td>${actionBtn}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  },

  /**
   * Renders the console logs list
   * @param {string} containerId 
   * @param {Array} logs 
   */
  renderLogs(containerId, logs) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';
    logs.forEach(log => {
      let lineClass = 'log-info';
      if (log.includes('Failed') || log.includes('ERROR') || log.includes('error')) {
        lineClass = 'log-error';
      } else if (log.includes('warning') || log.includes('Limitation') || log.includes('WARNING')) {
        lineClass = 'log-warn';
      } else if (log.includes('Published') || log.includes('completed') || log.includes('SUCCESS') || log.includes('initialized')) {
        lineClass = 'log-success';
      }
      html += `<div class="log-line ${lineClass}">${escapeHtml(log)}</div>`;
    });
    container.innerHTML = html;
  }
};

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
