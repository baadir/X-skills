/* TwitterYoldas — Tweet Preview App */

const API = '/api';
let currentThread = null;

/* ── State ───────────────────────────────────────────────── */
let tweetComments = {}; // idx → comment string

/* ── Bootstrap ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadThread();
  loadSavedComments();
  // Poll her 5 saniyede bir (Creator yeni thread yazarsa otomatik yeniler)
  setInterval(loadThread, 5000);
  // Feedback kategori butonları
  document.querySelectorAll('.fb-cat').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.fb-cat').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});

async function loadThread() {
  try {
    const res = await fetch(`${API}/thread`);
    if (!res.ok) { showEmpty(); return; }
    const data = await res.json();
    if (JSON.stringify(data) === JSON.stringify(currentThread)) return; // değişmediyse render etme
    currentThread = data;
    renderThread(data);
    renderAnalysis(data.analysis || {});
    updateHeader(data);
  } catch (e) {
    console.warn('Thread yüklenemedi:', e);
  }
}

/* ── Header ──────────────────────────────────────────────── */
function updateHeader(data) {
  const el = document.getElementById('header-meta');
  const ts = data.generated_at ? new Date(data.generated_at).toLocaleString('tr-TR') : '';
  el.textContent = `${data.thread_title || 'Thread'} · ${ts}`;
}

/* ── Thread Render ───────────────────────────────────────── */
function renderThread(data) {
  const container = document.getElementById('thread-container');
  const countEl   = document.getElementById('tweet-count');
  const tweets    = data.tweets || [];

  countEl.textContent = `${tweets.length} tweet`;
  container.innerHTML = '';

  // "Tüm Thread'i Kopyala" butonu
  const copyAllWrap = document.createElement('div');
  copyAllWrap.innerHTML = `<button class="copy-all-btn" onclick="copyAllTweets(this)">📋 Tüm Thread'i Kopyala (${tweets.length} tweet)</button>`;
  container.appendChild(copyAllWrap);

  tweets.forEach((tweet, idx) => {
    const isLast = idx === tweets.length - 1;
    const wrapper = document.createElement('div');
    wrapper.className = 'tweet-wrapper';

    const chars = (tweet.text || '').length;
    const charClass = chars > 280 ? 'over' : chars > 260 ? 'warn' : '';

    // Mevcut kayıtlı yorum varsa göster
    const savedComment = tweetComments[idx] || '';

    wrapper.innerHTML = `
      <div class="tweet-thread-line">
        <div class="tweet-avatar" title="@ciftcibahadir">BC</div>
        ${!isLast ? '<div class="thread-connector"></div>' : ''}
      </div>
      <div class="tweet-body" style="position:relative">
        <button class="tweet-copy-btn" onclick="copyTweet(${idx}, this)" title="Tweet'i kopyala">
          📋 Kopyala
        </button>
        <div class="tweet-meta">
          <span class="tweet-name">${data.author?.name || 'Bahadır Çiftçi'}</span>
          <span class="tweet-handle">${data.author?.handle || '@ciftcibahadir'}</span>
          <span class="tweet-num">${idx + 1}/${tweets.length}</span>
        </div>
        <div class="tweet-text">${formatTweetText(tweet.text || '')}</div>
        ${renderVisual(tweet, idx)}
        <div class="tweet-char ${charClass}">${chars}/280</div>
        <div class="tweet-actions">
          <div class="tweet-action reply"  title="Reply">  <span>💬</span> 0 </div>
          <div class="tweet-action rt"     title="Retweet"><span>🔁</span> 0 </div>
          <div class="tweet-action like"   title="Like">   <span>🤍</span> 0 </div>
          <div class="tweet-action bkm"    title="Bookmark"><span>🔖</span> 0 </div>
        </div>
        ${tweet.visual_suggestion ? `
          <div class="tweet-visual-placeholder" onclick="showVisualModal(${idx})">
            <div class="visual-icon">🖼️</div>
            <div>
              <div style="font-size:12px;color:var(--accent2);font-weight:600;">Görsel Önerisi</div>
              <div class="visual-label">${tweet.visual_suggestion}</div>
            </div>
          </div>` : ''}

        <!-- Per-tweet inline comment -->
        <button class="tweet-comment-toggle ${savedComment ? 'has-comment' : ''}"
                id="toggle-${idx}"
                onclick="toggleComment(${idx})">
          ✏️ ${savedComment ? 'Yorum var — düzenle' : 'Yorum ekle'}
        </button>
        <div class="tweet-comment-box ${savedComment ? 'open' : ''}" id="comment-box-${idx}">
          <textarea
            class="tweet-comment-input"
            id="comment-input-${idx}"
            placeholder="Bu tweet için notunuz... (örn: 'kanca daha güçlü olabilir', 'çok uzun kısalt')"
          >${savedComment}</textarea>
          <div class="tweet-comment-actions">
            <button class="tweet-comment-save" onclick="saveComment(${idx})">Kaydet</button>
            <button class="tweet-comment-clear" onclick="clearComment(${idx})">Temizle</button>
          </div>
        </div>
      </div>
    `;
    container.appendChild(wrapper);
  });
}

function renderVisual(tweet, idx) {
  if (tweet.visual_local || tweet.visual_url) {
    const src = tweet.visual_local
      ? `/visuals/${tweet.visual_local.split(/[\\/]/).pop()}`
      : tweet.visual_url;
    return `<div class="tweet-visual" onclick="showImageModal('${src}')">
               <img src="${src}" alt="Tweet görseli" loading="lazy" />
             </div>`;
  }
  return '';
}

function formatTweetText(text) {
  // → işaretleri renklendirme
  text = text.replace(/→/g, '<span class="arrow">→</span>');
  // Kod blokları
  text = text.replace(/```([\s\S]*?)```/g, (_, code) =>
    `<code class="code-block">${escHtml(code.trim())}</code>`);
  // Link renklendirme
  text = text.replace(/(https?:\/\/[^\s]+)/g, '<span style="color:var(--blue)">$1</span>');
  // Hashtag
  text = text.replace(/#(\w+)/g, '<span style="color:var(--accent2)">#$1</span>');
  // Mention
  text = text.replace(/@(\w+)/g, '<span style="color:var(--blue)">@$1</span>');
  return text;
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ── Analysis Render ─────────────────────────────────────── */
function renderAnalysis(a) {
  const container = document.getElementById('analysis-container');
  if (!a || Object.keys(a).length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">📈</div><div class="empty-text">Analiz verisi yok</div></div>`;
    return;
  }

  const scoreClass = scoreToClass(a.x_score);
  const dnaClass   = scoreToClass(a.mirror_dna_match);

  container.innerHTML = `
    <div class="analysis-container">

      <!-- Mode + Score -->
      <div class="analysis-section">
        <div class="analysis-section-header">🎯 Creator Modu & Algoritma Skoru</div>
        <div class="analysis-section-body">
          <div class="mode-badge">${a.mode || 'MOD 2 — THREAD'}</div>
          <div class="signal-row">
            <span class="signal-label">X Skoru</span>
            <span class="signal-value">
              <span class="score-badge ${scoreClass}">${scoreIcon(a.x_score)} ${a.x_score || '—'}</span>
            </span>
          </div>
          ${a.x_score_reason ? `<div class="why-box" style="margin-top:10px"><p>${a.x_score_reason}</p></div>` : ''}
        </div>
      </div>

      <!-- Engagement Profile -->
      <div class="analysis-section">
        <div class="analysis-section-header">📡 Engagement Profili</div>
        <div class="analysis-section-body">
          ${renderEngagement(a.engagement_profile)}
        </div>
      </div>

      <!-- Lab Pattern -->
      <div class="analysis-section">
        <div class="analysis-section-header">🧪 Lab Pattern Bağlantısı</div>
        <div class="analysis-section-body">
          ${renderLabPattern(a.lab_pattern)}
        </div>
      </div>

      <!-- Mirror DNA -->
      <div class="analysis-section">
        <div class="analysis-section-header">🪞 Mirror DNA Uyumu</div>
        <div class="analysis-section-body">
          <div class="compat-bar-wrap">
            <div class="compat-label">Uyum: <strong>${a.mirror_dna_match || '—'}</strong></div>
            <div class="compat-bar"><div class="compat-fill ${dnaClass}"></div></div>
          </div>
          ${a.mirror_dna_notes ? `<div class="why-box" style="margin-top:10px"><p>${a.mirror_dna_notes}</p></div>` : ''}
        </div>
      </div>

      <!-- Why this tweet -->
      ${a.why_this_tweet ? `
      <div class="analysis-section">
        <div class="analysis-section-header">💡 Neden Bu Tweet?</div>
        <div class="analysis-section-body">
          <div class="why-box">${a.why_this_tweet.split('\n').map(l => `<p>${l}</p>`).join('')}</div>
        </div>
      </div>` : ''}

      <!-- Publish time -->
      <div class="analysis-section">
        <div class="analysis-section-header">⏰ Optimal Yayın Zamanı</div>
        <div class="analysis-section-body">
          <div class="publish-time">
            <span class="publish-icon">📅</span>
            <span>${a.publish_time || '—'}</span>
          </div>
        </div>
      </div>

    </div>
  `;
}

function renderEngagement(ep) {
  if (!ep) return '<div class="empty-sub">Veri yok</div>';
  const rows = [
    ['Dominant', ep.dominant_signal, 'green'],
    ['İkincil',  ep.secondary_signal, 'purple'],
    ['Üçüncül',  ep.tertiary_signal, 'yellow'],
    ['Risk',     ep.risk_signal, 'low'],
  ].filter(r => r[1]);
  return rows.map(([label, val, cls]) => `
    <div class="signal-row">
      <span class="signal-label">${label}</span>
      <span class="signal-value"><span class="signal-tag ${cls}">${val}</span></span>
    </div>`).join('');
}

function renderLabPattern(lp) {
  if (!lp) return '<div class="empty-sub">Veri yok</div>';
  return [
    ['Kanca Tipi', lp.kanca_tipi],
    ['Psikolojik', lp.psikolojik_tetikleyici],
    ['Format',     lp.format],
  ].filter(r => r[1]).map(([label, val]) => `
    <div class="signal-row">
      <span class="signal-label">${label}</span>
      <span class="signal-value">${val}</span>
    </div>`).join('');
}

function scoreToClass(score) {
  if (!score) return 'medium';
  const s = score.toLowerCase();
  if (s.includes('yüksek') || s.includes('high')) return 'high';
  if (s.includes('düşük') || s.includes('low'))   return 'low';
  return 'medium';
}

function scoreIcon(score) {
  const cls = scoreToClass(score);
  return cls === 'high' ? '🟢' : cls === 'low' ? '🔴' : '🟡';
}

/* ── Per-Tweet Inline Comments ───────────────────────────── */
function loadSavedComments() {
  try {
    const saved = JSON.parse(localStorage.getItem('tweetComments') || '{}');
    tweetComments = saved;
  } catch(e) { tweetComments = {}; }
}

function toggleComment(idx) {
  const box    = document.getElementById(`comment-box-${idx}`);
  const toggle = document.getElementById(`toggle-${idx}`);
  const isOpen = box.classList.contains('open');
  box.classList.toggle('open', !isOpen);
  if (!isOpen) document.getElementById(`comment-input-${idx}`)?.focus();
}

function saveComment(idx) {
  const input = document.getElementById(`comment-input-${idx}`);
  const val   = (input?.value || '').trim();
  tweetComments[idx] = val;
  localStorage.setItem('tweetComments', JSON.stringify(tweetComments));

  const toggle = document.getElementById(`toggle-${idx}`);
  if (toggle) {
    toggle.classList.toggle('has-comment', !!val);
    toggle.textContent = val ? '✏️ Yorum var — düzenle' : '✏️ Yorum ekle';
  }
  // Kaydet sonrası kapat
  document.getElementById(`comment-box-${idx}`)?.classList.remove('open');
  updateFeedbackBadge();
}

function clearComment(idx) {
  const input = document.getElementById(`comment-input-${idx}`);
  if (input) input.value = '';
  delete tweetComments[idx];
  localStorage.setItem('tweetComments', JSON.stringify(tweetComments));
  const toggle = document.getElementById(`toggle-${idx}`);
  if (toggle) {
    toggle.classList.remove('has-comment');
    toggle.textContent = '✏️ Yorum ekle';
  }
  updateFeedbackBadge();
}

function updateFeedbackBadge() {
  const count  = Object.values(tweetComments).filter(v => v).length;
  const badge  = document.getElementById('feedback-badge');
  const label  = document.getElementById('fab-label');
  if (count > 0) {
    badge.textContent = count;
    badge.style.display = 'inline';
    if (label) label.textContent = `${count} yorum`;
  } else {
    badge.style.display = 'none';
    if (label) label.textContent = 'Feedback';
  }
}

/* ── Feedback Panel (Genel + Gönder) ────────────────────── */
function toggleFeedback() {
  document.getElementById('feedback-panel').classList.toggle('open');
  // Tweet select'i güncelle
  const tweets = currentThread?.tweets || [];
  const sel = document.getElementById('fb-tweet-num');
  if (sel) {
    sel.innerHTML = '<option value="0">Tüm thread</option>' +
      tweets.map((_, i) => `<option value="${i+1}">Tweet ${i+1}</option>`).join('');
  }
}

function addFeedbackItem() {
  const comment  = document.getElementById('fb-comment')?.value?.trim();
  const tweetNum = document.getElementById('fb-tweet-num')?.value;
  const category = document.querySelector('.fb-cat.active')?.dataset?.cat || 'genel';
  if (!comment) return;

  const tweetTotal = currentThread?.tweets?.length || 0;
  const item = {
    tweet_num: tweetNum === '0' ? 'genel' : parseInt(tweetNum),
    tweet_total: tweetTotal,
    category,
    comment,
    timestamp: new Date().toLocaleTimeString('tr-TR')
  };

  // Var olan feedback.json'a ekle (server API üzerinden)
  fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'add', item })
  }).then(() => {
    document.getElementById('fb-comment').value = '';
    renderFeedbackList();
    document.getElementById('fb-hint').style.display = 'block';
    setTimeout(() => document.getElementById('fb-hint').style.display = 'none', 4000);
  });
}

function sendFeedback() {
  // Inline tweet yorumlarını da ekle
  const tweets = currentThread?.tweets || [];
  const inlineItems = Object.entries(tweetComments)
    .filter(([, v]) => v)
    .map(([idx, comment]) => ({
      tweet_num: parseInt(idx) + 1,
      tweet_total: tweets.length,
      category: 'yorum',
      comment,
      timestamp: new Date().toLocaleTimeString('tr-TR')
    }));

  fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'send_all', inline_items: inlineItems })
  }).then(r => r.json()).then(() => {
    const btn = document.getElementById('fb-send-btn');
    btn.textContent = '✅ Gönderildi!';
    btn.classList.add('sent');
    setTimeout(() => {
      btn.textContent = 'Claude\'a Gönder ↗';
      btn.classList.remove('sent');
    }, 3000);
    // Inline yorumları temizle
    tweetComments = {};
    localStorage.setItem('tweetComments', JSON.stringify(tweetComments));
    updateFeedbackBadge();
    renderFeedbackList();
    document.getElementById('fb-hint').style.display = 'block';
  });
}

function clearFeedback() {
  fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'clear' })
  }).then(() => renderFeedbackList());
}

function renderFeedbackList() {
  fetch('/api/feedback').then(r => r.json()).then(data => {
    const list = document.getElementById('fb-list');
    if (!list) return;
    const items = data.items || [];
    if (!items.length) { list.innerHTML = ''; return; }
    list.innerHTML = items.map((item, i) => `
      <div class="fb-item">
        <span class="fb-item-tag">Tweet ${item.tweet_num} · ${item.category}</span>
        <span class="fb-item-text">${item.comment}</span>
        <button class="fb-item-del" onclick="deleteFeedbackItem(${i})">✕</button>
      </div>
    `).join('');
  });
}

function deleteFeedbackItem(idx) {
  fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'delete', idx })
  }).then(() => renderFeedbackList());
}

/* ── Copy Functions ──────────────────────────────────────── */
function copyTweet(idx, btn) {
  const tweet = currentThread?.tweets?.[idx];
  if (!tweet) return;
  navigator.clipboard.writeText(tweet.text || '').then(() => {
    btn.textContent = '✓ Kopyalandı';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.innerHTML = '📋 Kopyala';
      btn.classList.remove('copied');
    }, 2000);
  });
}

function copyAllTweets(btn) {
  if (!currentThread?.tweets?.length) return;
  const allText = currentThread.tweets
    .map((t, i) => `${i + 1}/\n${t.text}`)
    .join('\n\n---\n\n');
  navigator.clipboard.writeText(allText).then(() => {
    btn.textContent = '✓ Tüm Thread Kopyalandı!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.innerHTML = '📋 Tüm Thread\'i Kopyala';
      btn.classList.remove('copied');
    }, 2500);
  });
}

/* ── Modals ──────────────────────────────────────────────── */
function showVisualModal(tweetIdx) {
  const tweet = currentThread?.tweets?.[tweetIdx];
  if (!tweet) return;
  document.getElementById('modal-content').innerHTML = `
    <h3 style="margin-bottom:12px;font-size:16px;">🖼️ Görsel Önerisi — Tweet ${tweetIdx + 1}</h3>
    <div class="why-box"><p>${tweet.visual_suggestion || ''}</p></div>
    ${tweet.wiro_prompt ? `<div style="margin-top:12px"><div style="font-size:11px;color:var(--text2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.6px;">Wiro.ai Prompt</div><div class="why-box" style="font-family:'JetBrains Mono',monospace;font-size:12px;">${tweet.wiro_prompt}</div></div>` : ''}
  `;
  document.getElementById('modal-overlay').classList.add('open');
}

function showImageModal(src) {
  document.getElementById('img-lightbox-src').src = src;
  document.getElementById('img-lightbox').classList.add('open');
  document.addEventListener('keydown', _lightboxEsc);
}

function closeImageLightbox() {
  document.getElementById('img-lightbox').classList.remove('open');
  document.getElementById('img-lightbox-src').src = '';
  document.removeEventListener('keydown', _lightboxEsc);
}

function _lightboxEsc(e) {
  if (e.key === 'Escape') closeImageLightbox();
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

/* ── Empty State ─────────────────────────────────────────── */
function showEmpty() {
  document.getElementById('thread-container').innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⏳</div>
      <div class="empty-text">Creator skill çıktısı bekleniyor...</div>
      <div class="empty-sub">Thread üretildikten sonra otomatik görünür.</div>
    </div>`;
  document.getElementById('analysis-container').innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">📈</div>
      <div class="empty-text">Analiz bekleniyor...</div>
    </div>`;
  document.getElementById('header-meta').textContent = 'Henüz thread yok';
}
