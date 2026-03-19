/* TwitterYoldas — Thread Kütüphanesi */

const API = '/api';
let allDrafts   = [];
let activeFilter = 'all';
let activeDraftId = null;
let searchQuery  = '';

/* ── Bootstrap ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadDrafts();
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeImageLightbox();
    if (e.key === 'ArrowDown') navigateDraft(1);
    if (e.key === 'ArrowUp')   navigateDraft(-1);
  });
});

/* ── Load All Drafts ─────────────────────────────────────── */
async function loadDrafts() {
  try {
    const res = await fetch(`${API}/drafts`);
    if (!res.ok) throw new Error('API hatası');
    const data = await res.json();
    allDrafts = data.drafts || [];
    renderList();
  } catch (e) {
    document.getElementById('draft-list').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <div class="empty-text">Taslaklar yüklenemedi</div>
        <div class="empty-sub">${e.message}</div>
      </div>`;
  }
}

/* ── Filter & Search ─────────────────────────────────────── */
function setFilter(filter, btn) {
  activeFilter = filter;
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderList();
}

function filterDrafts() {
  searchQuery = document.getElementById('search-input').value.toLowerCase();
  renderList();
}

function getFiltered() {
  return allDrafts.filter(d => {
    const matchFilter = activeFilter === 'all' || d.status === activeFilter;
    const matchSearch = !searchQuery ||
      (d.thread_title || '').toLowerCase().includes(searchQuery);
    return matchFilter && matchSearch;
  });
}

/* ── Render Draft List ───────────────────────────────────── */
function renderList() {
  const list = document.getElementById('draft-list');
  const drafts = getFiltered();

  if (!drafts.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-text">${allDrafts.length === 0 ? 'Henüz taslak yok' : 'Eşleşen thread bulunamadı'}</div>
        <div class="empty-sub">${allDrafts.length === 0 ? 'Taslak Kaydet butonuna basarak ilk taslağı ekle.' : 'Farklı bir arama dene.'}</div>
      </div>`;
    return;
  }

  list.innerHTML = drafts.map(d => {
    const date  = d.generated_at ? new Date(d.generated_at).toLocaleDateString('tr-TR', { day:'2-digit', month:'short', year:'numeric' }) : '';
    const tweets = (() => { try { return JSON.parse(d.tweets_json || '[]').length; } catch { return 0; } })();
    const statusClass = `status-${d.status || 'öneri'}`;
    const statusLabel = d.status === 'atılmış' ? '✓ Atıldı' : 'Taslak';
    const isActive = d.id === activeDraftId ? 'active' : '';
    return `
      <div class="draft-card ${isActive}" onclick="selectDraft('${d.id}')" data-id="${d.id}">
        <div class="draft-card-title">${escHtml(d.thread_title || 'Başlıksız')}</div>
        <div class="draft-card-meta">
          <span class="status-badge ${statusClass}">${statusLabel}</span>
          <span class="draft-date">${date}</span>
          <span class="draft-count">${tweets} tweet</span>
        </div>
      </div>`;
  }).join('');
}

/* ── Select Draft ────────────────────────────────────────── */
async function selectDraft(id) {
  activeDraftId = id;
  renderList(); // active class için

  const pane = document.getElementById('preview-pane');
  pane.innerHTML = `<div class="empty-state center"><div class="empty-icon">⏳</div><div class="empty-text">Yükleniyor...</div></div>`;

  try {
    const res = await fetch(`${API}/drafts/${id}`);
    if (!res.ok) throw new Error('Draft bulunamadı');
    const draft = await res.json();
    renderPreview(draft);
  } catch (e) {
    pane.innerHTML = `<div class="empty-state center"><div class="empty-icon">⚠️</div><div class="empty-text">${e.message}</div></div>`;
  }
}

/* ── Keyboard Navigation ─────────────────────────────────── */
function navigateDraft(dir) {
  const filtered = getFiltered();
  if (!filtered.length) return;
  const idx = filtered.findIndex(d => d.id === activeDraftId);
  const next = idx === -1 ? 0 : Math.max(0, Math.min(filtered.length - 1, idx + dir));
  selectDraft(filtered[next].id);
  // Scroll into view
  const card = document.querySelector(`.draft-card[data-id="${filtered[next].id}"]`);
  card?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

/* ── Render Preview ──────────────────────────────────────── */
function renderPreview(draft) {
  const tweets = (() => {
    if (Array.isArray(draft.tweets_json)) return draft.tweets_json;
    try { return JSON.parse(draft.tweets_json || '[]'); } catch { return []; }
  })();

  const date = draft.generated_at
    ? new Date(draft.generated_at).toLocaleString('tr-TR')
    : '';

  const postedBadge = draft.tweet_url
    ? `<a class="posted-badge" href="${draft.tweet_url}" target="_blank">✓ X'te görüntüle</a>`
    : '';

  const pane = document.getElementById('preview-pane');
  pane.innerHTML = `
    <div class="preview-header">
      <div>
        <div class="preview-title">${escHtml(draft.thread_title || 'Başlıksız')}</div>
        <div class="preview-meta">${date} · ${tweets.length} tweet ${postedBadge}</div>
      </div>
      <button class="copy-thread-btn" onclick="copyAll()">📋 Tümünü Kopyala</button>
    </div>
    <div id="tweets-container"></div>`;

  const container = document.getElementById('tweets-container');
  tweets.forEach((tweet, idx) => {
    const isLast = idx === tweets.length - 1;
    const chars = (tweet.text || '').length;
    const charClass = chars > 280 ? 'over' : chars > 260 ? 'warn' : '';
    const visualHtml = renderVisual(tweet);

    const el = document.createElement('div');
    el.className = 'tweet-wrapper';
    el.innerHTML = `
      <div class="tweet-thread-line">
        <div class="tweet-avatar">BC</div>
        ${!isLast ? '<div class="thread-connector"></div>' : ''}
      </div>
      <div class="tweet-body">
        <button class="tweet-copy-btn" onclick="copyTweet(${idx})">📋 Kopyala</button>
        <div class="tweet-meta">
          <span class="tweet-name">${escHtml(draft.author_name || 'Bahadır Çiftçi')}</span>
          <span class="tweet-handle">${escHtml(draft.author_handle || '@ciftcibahadir')}</span>
          <span class="tweet-num">${idx + 1}/${tweets.length}</span>
        </div>
        <div class="tweet-text">${formatText(tweet.text || '')}</div>
        ${visualHtml}
        <div class="tweet-char ${charClass}">${chars}/280</div>
        <div class="tweet-actions">
          <div class="tweet-action"><span>💬</span> 0</div>
          <div class="tweet-action"><span>🔁</span> 0</div>
          <div class="tweet-action"><span>🤍</span> 0</div>
          <div class="tweet-action"><span>🔖</span> 0</div>
        </div>
      </div>`;
    container.appendChild(el);
  });

  // store tweets on pane for copy-all
  pane._tweets = tweets;
}

/* ── Visual ──────────────────────────────────────────────── */
function renderVisual(tweet) {
  if (tweet.visual_local || tweet.visual_url) {
    const src = tweet.visual_local
      ? `/visuals/${tweet.visual_local.split(/[\\/]/).pop()}`
      : tweet.visual_url;
    return `<div class="tweet-visual" onclick="openLightbox('${escAttr(src)}')">
               <img src="${escAttr(src)}" alt="Tweet görseli" loading="lazy" />
             </div>`;
  }
  return '';
}

/* ── Copy ────────────────────────────────────────────────── */
function copyTweet(idx) {
  const pane   = document.getElementById('preview-pane');
  const tweets = pane._tweets || [];
  const text   = tweets[idx]?.text || '';
  navigator.clipboard.writeText(text).then(() => {
    const btns = document.querySelectorAll('.tweet-copy-btn');
    const btn  = btns[idx];
    if (btn) { btn.textContent = '✓ Kopyalandı'; btn.classList.add('copied'); }
    setTimeout(() => { if (btn) { btn.textContent = '📋 Kopyala'; btn.classList.remove('copied'); } }, 2000);
  });
}

function copyAll() {
  const pane   = document.getElementById('preview-pane');
  const tweets = pane._tweets || [];
  const text   = tweets.map(t => t.text || '').join('\n\n---\n\n');
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.copy-thread-btn');
    if (btn) { btn.textContent = '✓ Kopyalandı!'; }
    setTimeout(() => { if (btn) btn.textContent = '📋 Tümünü Kopyala'; }, 2000);
  });
}

/* ── Lightbox ────────────────────────────────────────────── */
function openLightbox(src) {
  document.getElementById('img-lightbox-img').src = src;
  document.getElementById('img-lightbox').classList.add('open');
}
function closeImageLightbox() {
  document.getElementById('img-lightbox').classList.remove('open');
  document.getElementById('img-lightbox-img').src = '';
}

/* ── Helpers ─────────────────────────────────────────────── */
function formatText(text) {
  text = escHtml(text);
  text = text.replace(/→/g, '<span class="arrow">→</span>');
  text = text.replace(/```([\s\S]*?)```/g, (_, c) =>
    `<code class="code-block">${c.trim()}</code>`);
  text = text.replace(/(https?:\/\/[^\s&]+)/g, '<span style="color:#4a9eff">$1</span>');
  text = text.replace(/#(\w+)/g, '<span style="color:#9d78ff">#$1</span>');
  text = text.replace(/@(\w+)/g, '<span style="color:#4a9eff">@$1</span>');
  return text;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
  return String(s).replace(/'/g,"\\'").replace(/"/g,'&quot;');
}
