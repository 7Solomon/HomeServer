(function () {
  const qs = (s, el = document) => el.querySelector(s);
  const cardsEl = qs('#cards');
  const alertBox = qs('#alertBox');
  const limitInput = qs('#limitInput');   // may be null
  const tokenInput = qs('#tokenInput');   // may be null
  const refreshBtn = qs('#refreshBtn');   // may be null

  // Persist token between visits (only if input exists)
  if (tokenInput) {
    tokenInput.value = localStorage.getItem('ADMIN_TOKEN') || '';
    tokenInput.addEventListener('input', () => {
      localStorage.setItem('ADMIN_TOKEN', tokenInput.value.trim());
    });
  }

  refreshBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    loadItems();
  });

  function setAlert(msg) {
    if (!msg) { alertBox.hidden = true; alertBox.textContent = ''; return; }
    alertBox.hidden = false; alertBox.textContent = msg;
  }

  function skeleton(count = 6) {
    cardsEl.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const div = document.createElement('div');
      div.className = 'pu-card';
      div.innerHTML = `
        <div class="row1">
          <div class="icon"><i class="fab fa-youtube"></i></div>
          <div>
            <h4 style="opacity:.6">Lade…</h4>
            <div class="meta"><span class="status-pill" style="opacity:.5">—</span><span>—</span></div>
            <div class="small">—</div>
          </div>
        </div>
      `;
      cardsEl.appendChild(div);
    }
  }

  function render(items) {
    cardsEl.innerHTML = '';
    if (!items || !items.length) {
      cardsEl.innerHTML = '<div class="pu-alert">Keine Einträge gefunden.</div>';
      return;
    }

    for (const it of items) {
      const onServer = !!it.on_server;
      const thumb = it.thumbnail_url || it.thumbnail || it.thumb || null;

      const durSec = toSeconds(it.duration_seconds ?? it.duration ?? it.duration_string ?? null);
      const durText = durSec != null ? formatDuration(durSec) : '—';
      const isCut = durSec != null ? durSec < 3600 : null;

      const statusServerHtml = `
        <span class="status-pill ${onServer ? 'ok' : 'missing'}">
          ${onServer ? 'Auf Server' : 'Nicht auf Server'}
        </span>`;

      const statusCutHtml =
        isCut === null
          ? `<span class="chip neutral">Dauer unbekannt</span>`
          : isCut
            ? `<span class="chip ok">schon geschnitten</span>`
            : `<span class="chip bad">noch nicht geschnitten</span>`;

      const thumbHtml = thumb
        ? `<img class="thumb" src="${escapeHtml(thumb)}" alt="Thumbnail">`
        : `<div class="icon"><i class="fab fa-youtube"></i></div>`;

      const card = document.createElement('div');
      card.className = 'pu-card';
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.dataset.id = it.id || '';
      card.dataset.href = `/admin/predigt_upload/item/${encodeURIComponent(it.id || '')}`;

      card.innerHTML = `
        <div class="row1">
          ${thumbHtml}
          <div class="content">
            <h4 title="${escapeHtml(it.title || '')}">${escapeHtml(it.title || '(ohne Titel)')}</h4>
            <div class="meta">
              ${statusServerHtml}
              <span><i class="far fa-calendar"></i> ${escapeHtml(it.date || '—')}</span>
              <span><i class="far fa-clock"></i> ${durText}</span>
            </div>
            <div class="chips">
              ${statusCutHtml}
            </div>
            <div class="small">ID: ${escapeHtml(it.id || '')}</div>
          </div>
        </div>
      `;

      const go = () => { const href = card.dataset.href || '#'; if (href !== '#') window.location.href = href; };
      card.addEventListener('click', go);
      card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });

      cardsEl.appendChild(card);
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;'}[c]));
  }

  async function loadItems() {
    try {
      setAlert('');
      skeleton(4);
      const limit = parseInt(limitInput?.value || '7', 10) || 7;
      const token = (tokenInput?.value || '').trim();
      const url = `/api/predigt_upload/action/${limit}`;

      const headers = { 'Accept': 'application/json' };
      if (token) {
        headers['X-Admin-Token'] = token;
        headers['Authorization'] = `Bearer ${token}`;
      }

      const resp = await fetch(url, { method: 'GET', headers, credentials: 'same-origin' });
      if (!resp.ok) {
        const text = await resp.text().catch(()=>'');
        throw new Error(`HTTP ${resp.status} ${resp.statusText} ${text}`.trim());
      }

      const data = await resp.json();
      if (data.warnings?.length) setAlert(data.warnings.join(' • '));
      if (data.status !== 'success') throw new Error(data.message || 'Unbekannter Fehler');

      render(data.items || []);
    } catch (e) {
      setAlert(`Fehler beim Laden: ${e.message || e}`);
      cardsEl.innerHTML = '';
    }
  }

  function toSeconds(v) {
    if (v == null) return null;
    if (typeof v === 'number' && Number.isFinite(v)) return Math.max(0, Math.floor(v));
    const s = String(v).trim();
    if (/^\d+$/.test(s)) return parseInt(s, 10);
    if (/^\d{1,2}:\d{2}(:\d{2})?$/.test(s)) {
      const parts = s.split(':').map(n => parseInt(n, 10));
      return parts.length === 3 ? parts[0]*3600 + parts[1]*60 + parts[2] : parts[0]*60 + parts[1];
    }
    if (/^P(T.*)?$/i.test(s)) {
      const m = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/i.exec(s);
      if (m) { return (parseInt(m[1]||'0',10)*3600)+(parseInt(m[2]||'0',10)*60)+parseInt(m[3]||'0',10); }
    }
    return null;
  }

  function formatDuration(sec) {
    sec = Math.max(0, Math.floor(sec));
    const h = Math.floor(sec/3600), m = Math.floor((sec%3600)/60), s = sec%60;
    return h > 0 ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${m}:${String(s).padStart(2,'0')}`;
  }

  loadItems();
})();