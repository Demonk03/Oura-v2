# Dashboard Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать папку `dashboard/` с четырьмя файлами — login.html, index.html, dashboard.css, dashboard.js — работающими на моковых данных, без бэкенда и Supabase.

**Architecture:** Статичные файлы на GitHub Pages. На этом этапе данные — hardcoded mock-объект в JS. Auth-логика — заглушка (сразу показываем дашборд). Цель — верифицировать layout перед подключением реальных данных.

**Tech Stack:** HTML5, CSS (переиспользование v1 index.css), vanilla JS, Chart.js CDN

---

### Task 1: Создать login.html

**Files:**
- Create: `dashboard/login.html`

- [ ] Создать файл `dashboard/login.html` со следующим содержимым:

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Войти — Oura Dashboard</title>
  <link rel="stylesheet" href="dashboard.css" />
</head>
<body class="theme-dark">
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">Oura Dashboard</h1>
      <p class="login-subtitle">Войдите через Telegram, чтобы увидеть свои данные</p>

      <div id="telegram-widget-container">
        <!-- Telegram Login Widget подключается здесь -->
        <!-- data-auth-url — эндпоинт Render для верификации -->
        <script
          async
          src="https://telegram.org/js/telegram-widget.js?22"
          data-telegram-login="good_morning_oura_bot"
          data-size="large"
          data-radius="12"
          data-auth-url="https://oura-v2.onrender.com/auth/telegram"
          data-request-access="write">
        </script>
      </div>

      <p class="login-hint">
        Нет аккаунта? Напишите
        <a href="https://t.me/good_morning_oura_bot" target="_blank" rel="noopener">@good_morning_oura_bot</a>
        и выполните команду <code>/register</code>
      </p>
    </div>
  </div>
</body>
</html>
```

- [ ] Открыть файл в браузере (`open dashboard/login.html`) — убедиться что страница отображается без ошибок консоли (виджет может не загрузиться без бота — это ок на этом шаге)

---

### Task 2: Создать dashboard.css

**Files:**
- Create: `dashboard/dashboard.css`

- [ ] Скопировать полностью содержимое `../Oura/index.css` как базу, затем добавить в конец новые компоненты:

```css
/* ========================
   LOGIN PAGE
======================== */

.login-page {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: var(--s-4);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: clamp(24px, 4vw, 40px);
  border-radius: var(--r-lg);
  background: var(--surface);
  box-shadow: var(--shadow-1);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: grid;
  gap: var(--s-3);
  text-align: center;
}

.login-title {
  margin: 0;
  font-size: clamp(22px, 3vw, 28px);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.login-subtitle {
  margin: 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.5;
}

.login-hint {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.login-hint a {
  color: var(--accent);
}

.login-hint code {
  background: rgba(255,255,255,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

/* ========================
   ALERT BANNER
======================== */

.alert-banner {
  border-radius: var(--r-md);
  padding: var(--s-3) var(--s-4);
  background: rgba(255, 180, 50, 0.12);
  border: 1px solid rgba(255, 180, 50, 0.25);
  display: grid;
  gap: var(--s-1);
}

.alert-banner[hidden] {
  display: none;
}

.alert-banner-label {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #f5a623;
}

.alert-banner-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text);
}

/* ========================
   WEEKLY RECAP
======================== */

.recap-card {
  border-radius: var(--r-lg);
  background: var(--surface);
  box-shadow: var(--shadow-1);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: var(--s-4);
  display: grid;
  gap: var(--s-2);
}

.recap-label {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.recap-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text);
}

.recap-date {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

/* ========================
   KPI TREND ARROWS
======================== */

.kpi-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  height: 20px;
}

.kpi-trend--up {
  color: #4caf7d;
}

.kpi-trend--down {
  color: #e05c5c;
}

.kpi-trend--flat {
  color: var(--muted);
}

.kpi-trend-arrow {
  font-size: 16px;
  line-height: 1;
}

/* ========================
   HEADER USER INFO
======================== */

.header-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--s-2);
  margin-top: var(--s-2);
}

.header-user {
  font-size: 14px;
  color: var(--muted);
}

.header-logout {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.08);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 13px;
  transition: color 140ms, border-color 140ms;
}

.header-logout:hover {
  color: var(--text);
  border-color: rgba(255,255,255,0.18);
}

/* ========================
   RANGE FILTER
======================== */

.range-filters {
  display: flex;
  gap: var(--s-1);
  flex-wrap: wrap;
  justify-content: center;
}

.range-chip {
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.08);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 13px;
  transition: all 140ms;
}

.range-chip:hover,
.range-chip.active {
  background: rgba(111, 182, 216, 0.15);
  border-color: rgba(111, 182, 216, 0.3);
  color: var(--text);
}
```

- [ ] Открыть `login.html` в браузере — убедиться что стили применились

---

### Task 3: Создать index.html

**Files:**
- Create: `dashboard/index.html`

- [ ] Создать файл `dashboard/index.html`:

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Oura Dashboard</title>
  <link rel="stylesheet" href="dashboard.css" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="theme-dark">
  <a class="skip-link" href="#main">Перейти к содержимому</a>

  <div class="app">
    <header class="page-header" role="banner">
      <div class="header-card">
        <div class="header-meta">
          <div>
            <h1 class="header-title">Oura Dashboard</h1>
            <p class="header-subtitle" id="current-date">28.03.2026</p>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <span class="header-user" id="user-name">Dmitry</span>
            <button class="header-logout" id="logout-btn" type="button">Выйти</button>
          </div>
        </div>
      </div>
    </header>

    <main id="main" class="page" role="main">

      <!-- Alert banner (скрыт если нет алерта) -->
      <div class="alert-banner" id="alert-banner" hidden>
        <p class="alert-banner-label">Алерт сегодня</p>
        <p class="alert-banner-text" id="alert-text"></p>
      </div>

      <!-- KPI -->
      <section class="kpi" aria-labelledby="kpi-title">
        <header class="section-header">
          <h2 id="kpi-title" class="section-title">Показатели</h2>
          <p class="section-meta" id="kpi-date-label">Последние данные</p>
        </header>

        <ul class="kpi-grid" role="list">
          <li class="kpi-item">
            <article class="kpi-card" aria-label="Readiness">
              <div class="kpi-circle" aria-hidden="true">
                <div class="kpi-ring"></div>
                <div class="kpi-score" id="readiness-score">--</div>
              </div>
              <p class="kpi-label">Readiness</p>
              <div class="kpi-trend kpi-trend--flat" id="readiness-trend">
                <span class="kpi-trend-arrow">→</span>
                <span>--</span>
              </div>
            </article>
          </li>

          <li class="kpi-item">
            <article class="kpi-card" aria-label="Sleep">
              <div class="kpi-circle" aria-hidden="true">
                <div class="kpi-ring"></div>
                <div class="kpi-score" id="sleep-score">--</div>
              </div>
              <p class="kpi-label">Sleep</p>
              <div class="kpi-trend kpi-trend--flat" id="sleep-trend">
                <span class="kpi-trend-arrow">→</span>
                <span>--</span>
              </div>
            </article>
          </li>

          <li class="kpi-item">
            <article class="kpi-card" aria-label="Activity">
              <div class="kpi-circle" aria-hidden="true">
                <div class="kpi-ring"></div>
                <div class="kpi-score" id="activity-score">--</div>
              </div>
              <p class="kpi-label">Activity</p>
              <div class="kpi-trend kpi-trend--flat" id="activity-trend">
                <span class="kpi-trend-arrow">→</span>
                <span>--</span>
              </div>
            </article>
          </li>

          <li class="kpi-item">
            <article class="kpi-card" aria-label="Stress">
              <div class="kpi-circle" aria-hidden="true">
                <div class="kpi-ring"></div>
                <div class="kpi-score" id="stress-score">--</div>
              </div>
              <p class="kpi-label">Stress</p>
              <div class="kpi-trend kpi-trend--flat" id="stress-trend">
                <span class="kpi-trend-arrow">→</span>
                <span>--</span>
              </div>
            </article>
          </li>
        </ul>
      </section>

      <!-- Weekly Recap -->
      <section aria-labelledby="recap-title">
        <header class="section-header">
          <h2 id="recap-title" class="section-title">Итоги недели</h2>
        </header>
        <div class="recap-card" id="recap-card">
          <p class="recap-label">AI-анализ</p>
          <p class="recap-text" id="recap-text">Загрузка...</p>
          <p class="recap-date" id="recap-date"></p>
        </div>
      </section>

      <!-- Range filter + Charts -->
      <section class="charts" aria-labelledby="charts-title">
        <header class="section-header">
          <h2 id="charts-title" class="section-title">Графики</h2>
        </header>

        <div class="range-filters" role="group" aria-label="Диапазон">
          <button class="range-chip" type="button" data-days="7">7 дней</button>
          <button class="range-chip active" type="button" data-days="30">30 дней</button>
          <button class="range-chip" type="button" data-days="0">Всё время</button>
        </div>

        <div class="charts-grid">
          <article class="chart-card" aria-labelledby="readiness-chart-title">
            <header class="chart-header">
              <h3 id="readiness-chart-title" class="chart-title">Readiness</h3>
            </header>
            <div class="chart-area">
              <canvas id="readiness-canvas"></canvas>
            </div>
          </article>

          <article class="chart-card" aria-labelledby="sleep-chart-title">
            <header class="chart-header">
              <h3 id="sleep-chart-title" class="chart-title">Sleep</h3>
            </header>
            <div class="chart-area">
              <canvas id="sleep-canvas"></canvas>
            </div>
          </article>

          <article class="chart-card" aria-labelledby="activity-chart-title">
            <header class="chart-header">
              <h3 id="activity-chart-title" class="chart-title">Activity</h3>
            </header>
            <div class="chart-area">
              <canvas id="activity-canvas"></canvas>
            </div>
          </article>

          <article class="chart-card" aria-labelledby="stress-chart-title">
            <header class="chart-header">
              <h3 id="stress-chart-title" class="chart-title">Stress</h3>
            </header>
            <div class="chart-area">
              <canvas id="stress-canvas"></canvas>
            </div>
          </article>
        </div>
      </section>

    </main>

    <footer class="page-footer" role="contentinfo">
      <p class="footer-text">Oura-v2 Dashboard</p>
    </footer>
  </div>

  <script src="dashboard.js"></script>
</body>
</html>
```

- [ ] Открыть в браузере — убедиться что HTML рендерится без ошибок, видны все секции (KPI, Weekly recap, Charts)

---

### Task 4: Создать dashboard.js с mock-данными

**Files:**
- Create: `dashboard/dashboard.js`

- [ ] Создать файл `dashboard/dashboard.js`:

```javascript
// ── Mock data (заменим на Supabase в следующем шаге) ──────────────────────────
const MOCK_USER = { name: 'Dmitry' };

const MOCK_ALERT = {
  exists: true,
  text: 'HRV ниже нормы третий день подряд. Возможно, накопленная усталость. Рекомендуем снизить нагрузку сегодня.'
};

const MOCK_RECAP = {
  text: 'Неделя прошла нестабильно: сон улучшился к середине недели, но активность оставалась низкой. HRV держится ниже вашей 30-дневной нормы (58 мс vs 64 мс). Рекомендуется приоритизировать восстановление на выходных.',
  week_start: '2026-03-24'
};

// 30 дней моковых данных
const MOCK_LOGS = (() => {
  const logs = [];
  const today = new Date('2026-03-28');
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const date = d.toISOString().slice(0, 10);
    logs.push({
      date,
      readiness_score: 55 + Math.round(Math.random() * 35),
      sleep_score:     52 + Math.round(Math.random() * 38),
      activity_score:  50 + Math.round(Math.random() * 40),
      stress_high:     30 + Math.round(Math.random() * 120),
    });
  }
  return logs;
})();

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDateRu(isoDate) {
  const [y, m, d] = isoDate.split('-');
  return `${d}.${m}.${y}`;
}

function getTrend(current, previous, field) {
  if (previous === undefined || previous === null) return null;
  const curr = current[field];
  const prev = previous[field];
  if (curr === null || prev === null) return null;
  return curr - prev;
}

function renderTrend(elementId, delta) {
  const el = document.getElementById(elementId);
  if (!el || delta === null) return;
  const arrow = el.querySelector('.kpi-trend-arrow');
  const label = el.querySelector('span:last-child');

  el.classList.remove('kpi-trend--up', 'kpi-trend--down', 'kpi-trend--flat');

  if (delta > 2) {
    el.classList.add('kpi-trend--up');
    arrow.textContent = '↑';
    label.textContent = `+${delta}`;
  } else if (delta < -2) {
    el.classList.add('kpi-trend--down');
    arrow.textContent = '↓';
    label.textContent = `${delta}`;
  } else {
    el.classList.add('kpi-trend--flat');
    arrow.textContent = '→';
    label.textContent = `${delta > 0 ? '+' : ''}${delta}`;
  }
}

function makeChartConfig(labels, data, color) {
  return {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: color,
        backgroundColor: color.replace(')', ', 0.08)').replace('rgb', 'rgba'),
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: '#9aa0a6', font: { size: 11 }, maxTicksLimit: 8 },
          grid: { color: 'rgba(255,255,255,0.04)' }
        },
        y: {
          min: 0, max: 100,
          ticks: { color: '#9aa0a6', font: { size: 11 } },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      }
    }
  };
}

// ── Render functions ──────────────────────────────────────────────────────────
function renderHeader(user) {
  document.getElementById('user-name').textContent = user.name;
  const today = new Date();
  document.getElementById('current-date').textContent =
    today.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

function renderAlert(alert) {
  const banner = document.getElementById('alert-banner');
  if (alert && alert.exists) {
    banner.removeAttribute('hidden');
    document.getElementById('alert-text').textContent = alert.text;
  }
}

function renderRecap(recap) {
  if (!recap) return;
  document.getElementById('recap-text').textContent = recap.text;
  if (recap.week_start) {
    document.getElementById('recap-date').textContent =
      `Неделя с ${formatDateRu(recap.week_start)}`;
  }
}

function renderKPI(logs) {
  const last = logs[logs.length - 1];
  const prev = logs[logs.length - 2];
  if (!last) return;

  document.getElementById('readiness-score').textContent = last.readiness_score ?? '--';
  document.getElementById('sleep-score').textContent = last.sleep_score ?? '--';
  document.getElementById('activity-score').textContent = last.activity_score ?? '--';
  document.getElementById('stress-score').textContent = last.stress_high ?? '--';

  document.getElementById('kpi-date-label').textContent =
    `Данные за ${formatDateRu(last.date)}`;

  renderTrend('readiness-trend', getTrend(last, prev, 'readiness_score'));
  renderTrend('sleep-trend',     getTrend(last, prev, 'sleep_score'));
  renderTrend('activity-trend',  getTrend(last, prev, 'activity_score'));
  renderTrend('stress-trend',    getTrend(last, prev, 'stress_high'));
}

function renderCharts(logs, days) {
  const filtered = days === 0 ? logs : logs.slice(-days);
  const labels = filtered.map(r => {
    const d = new Date(r.date);
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
  });

  const charts = [
    { id: 'readiness-canvas', field: 'readiness_score', color: 'rgb(111,182,216)' },
    { id: 'sleep-canvas',     field: 'sleep_score',     color: 'rgb(126,161,216)' },
    { id: 'activity-canvas',  field: 'activity_score',  color: 'rgb(76,175,125)' },
    { id: 'stress-canvas',    field: 'stress_high',     color: 'rgb(224,92,92)',   maxY: null },
  ];

  charts.forEach(({ id, field, color, maxY }) => {
    const data = filtered.map(r => r[field]);
    const ctx = document.getElementById(id).getContext('2d');
    const config = makeChartConfig(labels, data, color);
    if (maxY === null) {
      delete config.options.scales.y.max;
    }
    // Уничтожаем старый инстанс если есть
    const existing = Chart.getChart(id);
    if (existing) existing.destroy();
    new Chart(ctx, config);
  });
}

// ── Range filter buttons ──────────────────────────────────────────────────────
function initRangeFilter(logs) {
  document.querySelectorAll('.range-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.range-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderCharts(logs, parseInt(btn.dataset.days));
    });
  });
}

// ── Logout ────────────────────────────────────────────────────────────────────
document.getElementById('logout-btn').addEventListener('click', () => {
  localStorage.removeItem('oura_jwt');
  window.location.href = 'login.html';
});

// ── Init ──────────────────────────────────────────────────────────────────────
function init() {
  renderHeader(MOCK_USER);
  renderAlert(MOCK_ALERT);
  renderRecap(MOCK_RECAP);
  renderKPI(MOCK_LOGS);
  renderCharts(MOCK_LOGS, 30);
  initRangeFilter(MOCK_LOGS);
}

init();
```

- [ ] Открыть `index.html` в браузере через `python3 -m http.server 8080 --directory dashboard` и перейти на `http://localhost:8080`
- [ ] Проверить: KPI-карточки показывают числа, стрелки отображаются с цветом, 4 графика нарисованы, алерт-баннер виден, weekly recap показывает текст, кнопки 7/30/всё меняют диапазон графиков

---

### Task 5: Commit

- [ ] `git -C "/Users/dkossenkov/Documents/Private files/AI/Oura-v2" add dashboard/`
- [ ] `git -C "/Users/dkossenkov/Documents/Private files/AI/Oura-v2" commit -m "feat: add dashboard scaffold with mock data"`
- [ ] Убедиться что коммит прошёл: `git log --oneline -1`
