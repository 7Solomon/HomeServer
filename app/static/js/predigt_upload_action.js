(function () {
  const $ = (id) => document.getElementById(id);
  const pageEl = $('page');

  const tokenInput = $('tokenInput');
  const titelInput = $('titelInput');
  const predigerInput = $('predigerInput');
  const datumInput = $('datumInput');

  const thumbImg = $('thumb');
  const thumbFallback = $('thumbFallback');
  const videoTitleEl = $('videoTitle');
  const videoDateEl = $('videoDate');
  const videoDurationEl = $('videoDuration');
  const videoIdEl = $('videoId');
  const cutBadge = $('cutBadge');

  const form = $('form');
  const processBtn = $('processBtn');
  const cancelBtn = $('cancelBtn');
  const progressBar = $('progressBar');
  const progressText = $('progressText');
  const stepEl = $('step');
  const statusEl = $('status');
  const messageEl = $('message');
  const finalPathEl = $('finalPath');
  const logEl = $('log');

  // persist token like list page
  tokenInput.value = localStorage.getItem('ADMIN_TOKEN') || '';
  tokenInput.addEventListener('input', () => {
    localStorage.setItem('ADMIN_TOKEN', tokenInput.value.trim());
  });

  // Determine video id (from data attr or URL)
  let videoId = (pageEl.dataset.id || '').trim();
  if (!videoId) {
    const m = location.pathname.match(/\/item\/([^\/\?]+)/);
    if (m) videoId = decodeURIComponent(m[1]);
  }

  let controller = null;
  let currentItem = null;

  function log(msg) {
    const time = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.textContent = `[${time}] ${msg}`;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function toSeconds(v) {
    if (v == null) return null;
    if (typeof v === 'number' && Number.isFinite(v)) return Math.max(0, Math.floor(v));
    const s = String(v).trim();
    if (/^\d+$/.test(s)) return parseInt(s, 10);
    if (/^\d{1,2}:\d{2}(:\d{2})?$/.test(s)) {
      const p = s.split(':').map(n => parseInt(n, 10));
      return p.length === 3 ? p[0]*3600 + p[1]*60 + p[2] : p[0]*60 + p[1];
    }
    const m = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/i.exec(s);
    if (m) return (parseInt(m[1]||'0',10)*3600)+(parseInt(m[2]||'0',10)*60)+parseInt(m[3]||'0',10);
    return null;
  }
  function formatDuration(sec) {
    if (sec == null) return '—';
    sec = Math.max(0, Math.floor(sec));
    const h = Math.floor(sec/3600), m = Math.floor((sec%3600)/60), s = sec%60;
    return h > 0 ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${m}:${String(s).padStart(2,'0')}`;
  }

  function setSummary(item) {
    const title = item.title || '';
    const date = item.date || '';
    const thumb = item.thumbnail_url || item.thumbnail || null;
    const durSec = toSeconds(item.duration_seconds ?? item.duration_string ?? null);

    videoTitleEl.textContent = title || '—';
    videoDateEl.textContent = date || '—';
    videoDurationEl.textContent = formatDuration(durSec);
    videoIdEl.textContent = videoId || '—';

    if (thumb) {
      thumbImg.src = thumb;
      thumbImg.style.display = 'block';
      thumbFallback.style.display = 'none';
    } else {
      thumbImg.removeAttribute('src');
      thumbImg.style.display = 'none';
      thumbFallback.style.display = 'grid';
    }

    if (durSec == null) {
      cutBadge.className = 'chip neutral';
      cutBadge.textContent = 'Dauer unbekannt';
    } else if (durSec < 3600) {
      cutBadge.className = 'chip ok';
      cutBadge.textContent = 'schon geschnitten';
    } else {
      cutBadge.className = 'chip bad';
      cutBadge.textContent = 'noch nicht geschnitten';
    }

    // Prefill form from title parts: "Titel | Prediger | dd.mm.yyyy"
    const parts = (title || '').split('|').map(t => t.trim()).filter(Boolean);
    if (parts.length >= 1) titelInput.value = parts[0];
    if (parts.length >= 2) predigerInput.value = parts[1];
    if (parts.length >= 3) {
      const m = /(\d{1,2})\.(\d{1,2})\.(\d{2,4})/.exec(parts[2]);
      if (m) {
        const dd = parseInt(m[1],10), mm = parseInt(m[2],10), yy = parseInt(m[3],10);
        const yyyy = yy < 100 ? yy + 2000 : yy;
        datumInput.value = `${yyyy}-${String(mm).padStart(2,'0')}-${String(dd).padStart(2,'0')}`;
      }
    }
    // fallback to API date
    if (!datumInput.value && date) datumInput.value = date;
    if (!datumInput.value) {
      const d = new Date(), yyyy=d.getFullYear(), mm=String(d.getMonth()+1).padStart(2,'0'), dd=String(d.getDate()).padStart(2,'0');
      datumInput.value = `${yyyy}-${mm}-${dd}`;
    }
  }

  async function loadItem() {
    try {
      if (!videoId) throw new Error('Keine Video-ID in URL gefunden.');
      // fetch a small list and pick the item
      const headers = { 'Accept': 'application/json' };
      const token = (tokenInput.value || '').trim();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
        headers['X-Admin-Token'] = token;
      }
      const resp = await fetch(`/api/predigt_upload/action/12`, { headers, credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      const data = await resp.json();
      const items = data.items || [];
      const found = items.find(x => x.id === videoId) || {};
      currentItem = found;
      setSummary(found);
    } catch (e) {
      log(`Fehler beim Laden: ${e.message || e}`);
    }
  }

  function setRunning(running) {
    processBtn.disabled = running;
    cancelBtn.disabled = !running;
  }

  async function processAndUpload(e) {
    e.preventDefault();
    if (!videoId || !titelInput.value || !predigerInput.value || !datumInput.value) {
      log('Bitte alle Felder ausfüllen.');
      return;
    }

    setRunning(true);
    progressBar.value = 0;
    progressText.textContent = '0%';
    stepEl.textContent = '–';
    statusEl.textContent = '–';
    messageEl.textContent = '–';
    finalPathEl.textContent = '–';
    logEl.textContent = '';

    controller = new AbortController();
    const token = (tokenInput.value || '').trim();
    const headers = { 'Content-Type': 'application/json', 'Accept': 'application/x-ndjson' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
      headers['X-Admin-Token'] = token;
    }

    // Fallback progress if backend omits "progress"
    const mapStepProgress = { download: 15, compress: 60, tags: 80, finalize: 90, complete: 100 };

    try {
      log('Starte Verarbeitung…');
      const resp = await fetch(`/predigt_upload/audio/process`, {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        body: JSON.stringify({
          id: videoId,
          prediger: predigerInput.value.trim(),
          titel: titelInput.value.trim(),
          datum: datumInput.value
        }),
        signal: controller.signal
      });

      // If auth required, Flask may send HTML (redirect/login)
      const ct = (resp.headers.get('content-type') || '').toLowerCase();
      if (!resp.ok) {
        const text = await resp.text().catch(()=>'');
        if (ct.includes('text/html') || text.startsWith('<')) {
          throw new Error('Nicht angemeldet. Bitte einloggen und erneut versuchen.');
        }
        throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      }

      let finalPath = null;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          // Login page guard mid-stream
          if (trimmed.startsWith('<')) {
            throw new Error('Sitzung abgelaufen oder nicht angemeldet.');
          }

          let obj;
          try { obj = JSON.parse(trimmed); }
          catch { log(`RAW: ${trimmed}`); continue; }

          const step = (obj.step || '').toLowerCase();
          const stat = obj.status || 'in_progress';
          const msg = obj.message || '';
          let p = parseInt(obj.progress ?? NaN, 10);
          if (Number.isNaN(p)) p = mapStepProgress[step] ?? 0;

          stepEl.textContent = step || '–';
          statusEl.textContent = stat;
          messageEl.textContent = msg;
          progressBar.value = p;
          progressText.textContent = `${p}%`;

          if (obj.final_path) {
            finalPath = obj.final_path;
            finalPathEl.textContent = finalPath;
          }
          log(`${step || '-'} | ${stat} | ${msg}`);
        }
      }

      // Flush remainder
      const rest = buffer.trim();
      if (rest) {
        if (rest.startsWith('<')) throw new Error('Sitzung abgelaufen oder nicht angemeldet.');
        try {
          const obj = JSON.parse(rest);
          const step = (obj.step || '').toLowerCase();
          const stat = obj.status || 'in_progress';
          const msg = obj.message || '';
          let p = parseInt(obj.progress ?? NaN, 10);
          if (Number.isNaN(p)) p = mapStepProgress[step] ?? 0;
          stepEl.textContent = step || '–';
          statusEl.textContent = stat;
          messageEl.textContent = msg;
          progressBar.value = p;
          progressText.textContent = `${p}%`;
          if (obj.final_path) {
            finalPath = obj.final_path;
            finalPathEl.textContent = finalPath;
          }
          log(`${step || '-'} | ${stat} | ${msg}`);
        } catch {
          log(`RAW: ${rest}`);
        }
      }

      if (!finalPath) throw new Error('Kein Ausgabe-Pfad vom Server erhalten.');

      // Upload to FTP
      log('Lade Datei auf den FTP-Server…');
      const upHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
      if (token) {
        upHeaders['Authorization'] = `Bearer ${token}`;
        upHeaders['X-Admin-Token'] = token;
      }
      const upBody = {
        local_path: finalPath,
        remote_name: finalPath.split(/[\\/]/).pop()
      };
      const upResp = await fetch(`/api/predigt_upload/ftp/upload`, {
        method: 'POST',
        headers: upHeaders,
        credentials: 'same-origin',
        body: JSON.stringify(upBody)
      });
      if (!upResp.ok) throw new Error(`FTP Upload HTTP ${upResp.status} ${upResp.statusText}`);
      const upData = await upResp.json();
      if (upData.status !== 'success') throw new Error(upData.message || 'FTP Upload fehlgeschlagen');
      log('FTP Upload abgeschlossen.');
      stepEl.textContent = 'upload';
      statusEl.textContent = 'completed';
      messageEl.textContent = 'FTP Upload abgeschlossen';
      progressBar.value = 100; progressText.textContent = '100%';
    } catch (err) {
      log(`Fehler: ${err.message || err}`);
      statusEl.textContent = 'failed';
      messageEl.textContent = err.message || String(err);
    } finally {
      setRunning(false);
      controller = null;
    }
  }

  form.addEventListener('submit', processAndUpload);
  cancelBtn.addEventListener('click', () => { if (controller) controller.abort(); });

  // init
  loadItem();
})();