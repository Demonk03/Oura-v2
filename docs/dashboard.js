// ─────────────────────────────────────────────────────────────
// AUTH
// ─────────────────────────────────────────────────────────────
const jwt  = localStorage.getItem('oura_jwt');
const userMeta = JSON.parse(localStorage.getItem('oura_user') || 'null');

if (!jwt) {
  window.location.replace('login.html');
}

// ─────────────────────────────────────────────────────────────
// API HELPER
// ─────────────────────────────────────────────────────────────
async function apiFetch(path) {
  const res = await fetch(RENDER_URL + path, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (res.status === 401) {
    localStorage.removeItem('oura_jwt');
    localStorage.removeItem('oura_user');
    window.location.replace('login.html');
    return null;
  }
  return res.json();
}

// ─────────────────────────────────────────────────────────────
// DATA FETCHING
// ─────────────────────────────────────────────────────────────
async function fetchLogs() {
  const data = await apiFetch('/api/logs?days=90');
  return data || [];
}

async function fetchRecap() {
  const data = await apiFetch('/api/weekly');
  if (!data || !data.weekly_data) return null;
  const text = data.weekly_data?.summary || data.weekly_data?.text || null;
  return text ? { text, week_start: data.week_start } : null;
}

// ─────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────
function formatDateRu(isoDate) {
  const [y, m, d] = isoDate.split('-');
  return `${d}.${m}.${y}`;
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function delta(curr, prev) {
  if (curr == null || prev == null) return null;
  return curr - prev;
}

// ─────────────────────────────────────────────────────────────
// RENDER: header
// ─────────────────────────────────────────────────────────────
function renderHeader(user) {
  const nameEl = document.getElementById('user-name');
  if (nameEl && user.name) nameEl.textContent = user.name;

  const dateEl = document.getElementById('current-date');
  if (dateEl) {
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString('ru-RU', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  }
}

// ─────────────────────────────────────────────────────────────
// RENDER: alert banner
// ─────────────────────────────────────────────────────────────
function renderAlert(alert) {
  const banner = document.getElementById('alert-banner');
  if (!banner) return;
  if (alert && alert.exists && alert.text) {
    banner.removeAttribute('hidden');
    document.getElementById('alert-text').textContent = alert.text;
  }
}

// ─────────────────────────────────────────────────────────────
// RENDER: weekly recap
// ─────────────────────────────────────────────────────────────
function renderRecap(recap) {
  if (!recap) return;
  const textEl = document.getElementById('recap-text');
  const dateEl = document.getElementById('recap-date');
  if (textEl) textEl.textContent = recap.text;
  if (dateEl && recap.week_start) {
    dateEl.textContent = `Неделя с ${formatDateRu(recap.week_start)}`;
  }
}

// ─────────────────────────────────────────────────────────────
// RENDER: trend arrow
// ─────────────────────────────────────────────────────────────
function renderTrend(elementId, d) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const arrow = el.querySelector('.kpi-trend-arrow');
  const label = el.querySelector('span:last-child');

  el.classList.remove('kpi-trend--up', 'kpi-trend--down', 'kpi-trend--flat');

  if (d === null) {
    el.classList.add('kpi-trend--flat');
    arrow.textContent = '→';
    label.textContent = '—';
    return;
  }

  if (d > 2) {
    el.classList.add('kpi-trend--up');
    arrow.textContent = '↑';
    label.textContent = `+${d}`;
  } else if (d < -2) {
    el.classList.add('kpi-trend--down');
    arrow.textContent = '↓';
    label.textContent = `${d}`;
  } else {
    el.classList.add('kpi-trend--flat');
    arrow.textContent = '→';
    label.textContent = `${d > 0 ? '+' : ''}${d}`;
  }
}

// ─────────────────────────────────────────────────────────────
// DATE FILTER
// ─────────────────────────────────────────────────────────────
function populateDateFilter(logs) {
  const select = document.getElementById('date-filter');
  if (!select) return;

  select.innerHTML = '';
  const today = todayIso();

  // Сортируем по убыванию (новые даты сверху)
  const sorted = [...logs].sort((a, b) => b.date.localeCompare(a.date));

  sorted.forEach(row => {
    const opt = document.createElement('option');
    opt.value = row.date;
    const d = new Date(row.date + 'T00:00:00');
    const formatted = d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const weekday  = d.toLocaleDateString('ru-RU', { weekday: 'short' });
    opt.textContent = `${formatted} (${weekday})`;
    if (row.date === today) opt.selected = true;
    select.appendChild(opt);
  });

  // Если сегодня нет в данных — выбираем последнюю доступную дату
  if (!sorted.find(r => r.date === today) && sorted.length) {
    select.value = sorted[0].date;
  }
}

function renderKPIForDate(logs, isoDate) {
  const idx  = logs.findIndex(r => r.date === isoDate);
  if (idx === -1) return;
  const row  = logs[idx];
  const prev = idx > 0 ? logs[idx - 1] : null;

  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val != null ? val : '--';
  };

  set('readiness-score', row.readiness_score);
  set('sleep-score',     row.sleep_score);
  set('activity-score',  row.activity_score);
  set('stress-score',    row.stress_high);

  const metaEl = document.getElementById('kpi-meta');
  if (metaEl) metaEl.textContent = `Данные за ${formatDateRu(row.date)}`;

  renderTrend('readiness-trend', delta(row.readiness_score, prev?.readiness_score));
  renderTrend('sleep-trend',     delta(row.sleep_score,     prev?.sleep_score));
  renderTrend('activity-trend',  delta(row.activity_score,  prev?.activity_score));
  renderTrend('stress-trend',    delta(row.stress_high,     prev?.stress_high));
}

// ─────────────────────────────────────────────────────────────
// RENDER: KPI cards (показывает последний день)
// ─────────────────────────────────────────────────────────────
function renderKPI(logs) {
  if (!logs.length) return;
  const select = document.getElementById('date-filter');
  const date = select?.value || logs[logs.length - 1].date;
  renderKPIForDate(logs, date);
}

// ─────────────────────────────────────────────────────────────
// CHARTS
// ─────────────────────────────────────────────────────────────
const CHART_CONFIGS = [
  { canvas: 'readiness-canvas', field: 'readiness_score', color: '#6fb6d8', maxY: 100 },
  { canvas: 'sleep-canvas',     field: 'sleep_score',     color: '#7d9fd4', maxY: 100 },
  { canvas: 'activity-canvas',  field: 'activity_score',  color: '#5cbf8a', maxY: 100 },
  { canvas: 'stress-canvas',    field: 'stress_high',     color: '#e57070', maxY: null },
];

const chartInstances = {};

function buildChartOptions(color, maxY) {
  const rgba = (hex, a) => {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return `rgba(${r},${g},${b},${a})`;
  };

  return {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: color,
        backgroundColor: rgba(color, 0.09),
        borderWidth: 2,
        pointRadius: 2.5,
        pointHoverRadius: 6,
        pointBackgroundColor: color,
        pointBorderColor: 'rgba(20,21,22,0)',
        tension: 0.35,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(20,21,22,0.92)',
          titleColor: '#f4f4f4',
          bodyColor: '#9aa0a6',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            title: (ctx) => {
              const raw = ctx[0].label;
              return raw;
            },
            label: (ctx) => `${ctx.parsed.y}`,
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#666b70', font: { size: 11, family: "'DM Mono', monospace" }, maxTicksLimit: 10 },
        },
        y: {
          min: 0,
          ...(maxY ? { max: maxY } : {}),
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#666b70', font: { size: 11, family: "'DM Mono', monospace" } },
        }
      },
      interaction: { intersect: false, mode: 'index' }
    }
  };
}

function renderCharts(logs, days) {
  const slice = days === 0 ? logs : logs.slice(-days);
  const labels = slice.map(r => {
    const d = new Date(r.date);
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
  });

  CHART_CONFIGS.forEach(({ canvas, field, color, maxY }) => {
    const data = slice.map(r => r[field]);
    const existing = chartInstances[canvas];

    if (existing) {
      existing.data.labels = labels;
      existing.data.datasets[0].data = data;
      existing.update('active');
    } else {
      const ctx = document.getElementById(canvas);
      if (!ctx) return;
      const config = buildChartOptions(color, maxY);
      config.data.labels = labels;
      config.data.datasets[0].data = data;
      chartInstances[canvas] = new Chart(ctx, config);
    }
  });
}

// ─────────────────────────────────────────────────────────────
// RANGE FILTER
// ─────────────────────────────────────────────────────────────
function initRangeFilter(logs) {
  document.querySelectorAll('.range-filters .chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.range-filters .chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderCharts(logs, parseInt(btn.dataset.days));
    });
  });
}

// ─────────────────────────────────────────────────────────────
// LOGOUT
// ─────────────────────────────────────────────────────────────
const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('oura_jwt');
    localStorage.removeItem('oura_user');
    window.location.href = 'login.html';
  });
}

// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────
async function init() {
  renderHeader(userMeta || { name: '' });

  const [logs, recap] = await Promise.all([fetchLogs(), fetchRecap()]);

  if (!logs.length) {
    document.getElementById('kpi-meta').textContent = 'Нет данных';
    document.getElementById('recap-text').textContent = 'Данные появятся после первой синхронизации.';
    return;
  }

  renderRecap(recap);
  populateDateFilter(logs);
  renderKPI(logs);
  renderCharts(logs, 30);
  initRangeFilter(logs);

  const dateSelect = document.getElementById('date-filter');
  if (dateSelect) {
    dateSelect.addEventListener('change', () => {
      renderKPIForDate(logs, dateSelect.value);
    });
  }
}

init();
