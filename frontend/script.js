/**
 * script.js – AI Shorts Generator frontend logic
 *
 * Flow:
 *  1. User pastes URL → clicks "Generate Shorts"
 *  2. POST /api/generate  → receive job_id
 *  3. Poll GET /api/status/{job_id} every 2 s
 *  4. On progress updates → animate progress bar + pipeline steps
 *  5. On completion → render clip cards with video preview + download
 */

/* ── Constants ─────────────────────────────────────────────── */
const API_BASE      = '';          // same origin
const POLL_INTERVAL = 2000;        // ms between status polls

/* ── Pipeline step mapping ──────────────────────────────────── */
const STEP_MAP = [
  { id: 'step-download',   keywords: ['download', 'youtube', 'yt-dlp'],      pct: [0,  19] },
  { id: 'step-transcribe', keywords: ['transcri', 'whisper', 'audio'],        pct: [20, 39] },
  { id: 'step-analyse',    keywords: ['analys', 'scor', 'segment', 'select'], pct: [40, 54] },
  { id: 'step-hooks',      keywords: ['hook', 'llm', 'ollama', 'viral'],      pct: [55, 64] },
  { id: 'step-captions',   keywords: ['caption', 'emoji', 'subtitle'],        pct: [65, 74] },
  { id: 'step-render',     keywords: ['render', 'clip', 'export', 'ready'],   pct: [75, 100] },
];

/* ── State ─────────────────────────────────────────────────── */
let pollTimer  = null;
let currentJob = null;

/* ── DOM helpers ────────────────────────────────────────────── */
const $  = id  => document.getElementById(id);
const el = sel => document.querySelector(sel);

/* ── Input clear button ─────────────────────────────────────── */
$('youtube-url').addEventListener('input', e => {
  $('clear-btn').classList.toggle('visible', e.target.value.length > 0);
});

$('clear-btn').addEventListener('click', () => {
  $('youtube-url').value = '';
  $('clear-btn').classList.remove('visible');
  $('youtube-url').focus();
});

/* Allow pressing Enter in the URL field to trigger generation */
$('youtube-url').addEventListener('keydown', e => {
  if (e.key === 'Enter') startGeneration();
});

/* ═══════════════════════════════════════════════════════════
   startGeneration – entry point
   ═══════════════════════════════════════════════════════════ */
async function startGeneration() {
  const url = $('youtube-url').value.trim();

  if (!url) {
    shakeInput();
    return;
  }

  if (!isValidYouTubeUrl(url)) {
    showInputError('Please enter a valid YouTube URL.');
    return;
  }

  resetResultsUI();
  showProgressCard();
  disableGenerateBtn(true);

  try {
    const resp = await fetch(`${API_BASE}/api/generate`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ youtube_url: url }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Unknown server error' }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    currentJob = data.job_id;
    startPolling(currentJob);

  } catch (err) {
    showError(err.message);
    disableGenerateBtn(false);
  }
}

/* ═══════════════════════════════════════════════════════════
   Polling
   ═══════════════════════════════════════════════════════════ */
function startPolling(jobId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => pollStatus(jobId), POLL_INTERVAL);
  pollStatus(jobId);  // immediate first call
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function pollStatus(jobId) {
  try {
    const resp = await fetch(`${API_BASE}/api/status/${jobId}`);
    if (!resp.ok) throw new Error(`Status poll failed: HTTP ${resp.status}`);

    const data = await resp.json();
    updateProgressUI(data);

    if (data.status === 'done') {
      stopPolling();
      renderClips(data.clips);
      finishProgressUI();
      disableGenerateBtn(false);
    } else if (data.status === 'error') {
      stopPolling();
      showError(data.step || 'An unknown error occurred in the pipeline.');
      disableGenerateBtn(false);
    }

  } catch (err) {
    console.error('Poll error:', err);
    // Don't stop polling on transient network errors – retry next cycle
  }
}

/* ═══════════════════════════════════════════════════════════
   Progress UI
   ═══════════════════════════════════════════════════════════ */
function showProgressCard() {
  $('progress-card').style.display = 'block';
  $('error-card').style.display    = 'none';
  $('results-section').style.display = 'none';
  resetPipelineSteps();
}

function resetPipelineSteps() {
  STEP_MAP.forEach(s => {
    const el = $(s.id);
    el.classList.remove('active', 'done');
  });
}

function updateProgressUI(data) {
  const pct  = data.progress || 0;
  const step = data.step     || '';

  // Update bar
  $('progress-bar').style.width = `${pct}%`;
  $('progress-pct').textContent = `${pct}%`;
  $('progress-detail').textContent = step;

  // Update pipeline step states
  const stepLower = step.toLowerCase();
  STEP_MAP.forEach(s => {
    const domEl = $(s.id);
    const isActive  = s.keywords.some(k => stepLower.includes(k));
    const isDone    = pct > s.pct[1];

    if (isDone) {
      domEl.classList.remove('active');
      domEl.classList.add('done');
    } else if (isActive || (pct >= s.pct[0] && pct <= s.pct[1])) {
      domEl.classList.add('active');
      domEl.classList.remove('done');
    } else {
      domEl.classList.remove('active', 'done');
    }
  });
}

function finishProgressUI() {
  // Mark all steps done
  STEP_MAP.forEach(s => {
    const domEl = $(s.id);
    domEl.classList.remove('active');
    domEl.classList.add('done');
  });
  $('progress-spinner').style.animation = 'none';
  $('progress-spinner').textContent = '✅';
  $('progress-step-label').textContent = 'All clips are ready!';
  $('progress-detail').textContent = '';
}

/* ═══════════════════════════════════════════════════════════
   Clip cards renderer
   ═══════════════════════════════════════════════════════════ */
function renderClips(clips) {
  const section = $('results-section');
  const grid    = $('clips-grid');

  grid.innerHTML = '';

  if (!clips || clips.length === 0) {
    section.style.display = 'block';
    grid.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:24px">No clips were generated. Try a longer video.</p>';
    return;
  }

  // Update count badge
  $('clip-count-badge').textContent = `${clips.length} clip${clips.length > 1 ? 's' : ''}`;

  // Render each clip card
  clips.forEach((clip, idx) => {
    const card = buildClipCard(clip, idx);
    grid.appendChild(card);
  });

  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildClipCard(clip, idx) {
  const tpl  = document.getElementById('clip-card-template');
  const node = tpl.content.cloneNode(true);
  const card = node.querySelector('.clip-card');

  // Add staggered fade-in delay
  card.style.animationDelay = `${idx * 60}ms`;

  const fileUrl    = clip.file;
  const title      = clip.title      || `Clip ${idx + 1}`;
  const duration   = clip.duration   || 0;
  const score      = clip.viral_score || 0;
  const hook       = clip.hook       || '';
  const filename   = fileUrl.split('/').pop();

  // Video source
  const video = card.querySelector('.clip-video');
  video.querySelector('source').src = fileUrl;
  video.load();

  // Score badge
  const scoreBadge = card.querySelector('.clip-badge-score');
  scoreBadge.textContent = `🔥 ${score.toFixed(1)}`;

  // Info
  card.querySelector('.clip-title').textContent    = title;
  card.querySelector('.clip-duration').textContent = `⏱ ${formatDuration(duration)}`;
  card.querySelector('.clip-score').textContent    = `🔥 ${score.toFixed(1)} viral score`;
  card.querySelector('.clip-hook').textContent     = hook ? `"${hook}"` : '';

  // Download button
  const dlBtn = card.querySelector('.download-btn');
  dlBtn.href      = fileUrl;
  dlBtn.download  = filename;
  dlBtn.textContent = `⬇️ Download clip ${idx + 1}`;

  return card;
}

/* ═══════════════════════════════════════════════════════════
   Download All
   ═══════════════════════════════════════════════════════════ */
async function downloadAll() {
  const links = document.querySelectorAll('.download-btn');
  for (let i = 0; i < links.length; i++) {
    const a = document.createElement('a');
    a.href     = links[i].href;
    a.download = links[i].download;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Small delay to avoid browser blocking multiple downloads
    await new Promise(r => setTimeout(r, 400));
  }
}

/* ═══════════════════════════════════════════════════════════
   Error display
   ═══════════════════════════════════════════════════════════ */
function showError(msg) {
  $('progress-card').style.display = 'none';
  $('error-card').style.display    = 'block';
  $('error-msg').textContent       = msg;
}

/* ═══════════════════════════════════════════════════════════
   Reset / utilities
   ═══════════════════════════════════════════════════════════ */
function resetUI() {
  stopPolling();
  $('progress-card').style.display   = 'none';
  $('error-card').style.display      = 'none';
  $('results-section').style.display = 'none';
  $('progress-bar').style.width      = '0%';
  $('progress-pct').textContent      = '0%';
  $('progress-detail').textContent   = 'Initialising pipeline…';
  $('progress-spinner').style.animation = '';
  $('progress-spinner').textContent  = '⚙️';
  $('progress-step-label').textContent = 'Processing…';
  $('clips-grid').innerHTML          = '';
  resetPipelineSteps();
  disableGenerateBtn(false);
  currentJob = null;
}

function resetResultsUI() {
  $('results-section').style.display = 'none';
  $('clips-grid').innerHTML = '';
  $('error-card').style.display = 'none';
}

function disableGenerateBtn(disabled) {
  const btn = $('generate-btn');
  btn.disabled = disabled;
  btn.querySelector('.btn-text').textContent = disabled ? 'Processing…' : 'Generate Shorts';
  btn.querySelector('.btn-icon').textContent = disabled ? '⏳' : '🚀';
}

function shakeInput() {
  const input = $('youtube-url');
  input.style.borderColor = 'var(--error)';
  input.style.animation   = 'none';
  // Force reflow
  void input.offsetWidth;
  input.style.animation = 'shake 0.4s ease';
  setTimeout(() => {
    input.style.borderColor = '';
    input.style.animation   = '';
  }, 600);
}

function showInputError(msg) {
  $('youtube-url').style.borderColor = 'var(--error)';
  $('youtube-url').title = msg;
  setTimeout(() => {
    $('youtube-url').style.borderColor = '';
    $('youtube-url').title = '';
  }, 2500);
}

function isValidYouTubeUrl(url) {
  return /(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)[\w-]+/.test(url);
}

function formatDuration(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

/* ── Shake keyframe (injected dynamically) ────────────────── */
const shakeStyle = document.createElement('style');
shakeStyle.textContent = `
  @keyframes shake {
    0%,100% { transform: translateX(0); }
    20%      { transform: translateX(-8px); }
    40%      { transform: translateX(8px); }
    60%      { transform: translateX(-5px); }
    80%      { transform: translateX(5px); }
  }
`;
document.head.appendChild(shakeStyle);
