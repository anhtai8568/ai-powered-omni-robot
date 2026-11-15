// Dashboard điều khiển robot.
// Quy ước (chuẩn ROS): vx > 0 tiến, vy > 0 sang trái, w > 0 xoay ngược chiều kim đồng hồ.
//
// Tin từ server:
//   status    (2 lần/giây)  kết nối, camera, fps, chế độ, dừng khẩn cấp, cài đặt
//   telemetry (20 lần/giây) lệnh thật đang gửi cho robot + cử chỉ AI thấy + tay nào đang thấy
//   cursor    (30 lần/giây) con trỏ của tay thuận, xử lý trong handcursor.js
(() => {
  const $ = (id) => document.getElementById(id);
  const canvas = $('view');
  const ctx = canvas.getContext('2d');
  const pad = $('pad');
  const knob = $('knob');

  const SEND_HZ = 20;
  const t = I18N.t;
  const input = { pad: { x: 0, y: 0 }, rot: 0, keys: new Set() };
  const ui = {
    mode: 'manual', estop: false, speed: 0.5, lastFrame: 0, camera: false,
    video: true, robot: false, rtt: null, fps: 0,
    dominant: 'right', region: 1.0, hands: { ui: false, drive: false },
  };
  const cfg = HandCursor.cfg;
  const side = (h) => t(`side.${h}`);
  let lastStatus = null;
  let ws = null;
  let decoding = false;

  // ---------- Kết nối ----------
  function setStatus(id, text, ok) {
    const el = $(id);
    el.textContent = text;
    el.dataset.ok = String(ok);
  }

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/dashboard`);
    ws.onopen = () => setStatus('st-link', t('st.link'), true);
    ws.onclose = () => {
      setStatus('st-link', t('st.link.retry'), false);
      setTimeout(connect, 1000);
    };
    ws.onmessage = (e) => {
      if (typeof e.data !== 'string') return drawFrame(e.data);
      const msg = JSON.parse(e.data);
      if (msg.type === 'status') onStatus(msg);
      else if (msg.type === 'telemetry') onTelemetry(msg);
      else if (msg.type === 'cursor') HandCursor.update(msg);
    };
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  async function drawFrame(blob) {
    if (decoding || !ui.video) return; // bỏ khung nếu khung trước chưa giải mã xong, hoặc đang ẩn hình
    decoding = true;
    try {
      const bmp = await createImageBitmap(blob);
      if (canvas.width !== bmp.width || canvas.height !== bmp.height) {
        canvas.width = bmp.width;
        canvas.height = bmp.height;
      }
      ctx.drawImage(bmp, 0, 0);
      bmp.close();
      ui.lastFrame = performance.now();
    } catch (_) {
      /* khung hỏng, bỏ qua */
    } finally {
      decoding = false;
    }
  }

  // ---------- Tin từ server ----------
  function onStatus(s) {
    lastStatus = s;
    ui.camera = s.camera;
    ui.robot = s.robot;
    ui.rtt = s.rtt;
    ui.fps = s.fps;
    setStatus('st-camera', s.camera ? t('st.camera') : t('st.camera.fail'), s.camera);
    setStatus('st-robot', s.robot ? t('st.robot.ok', { rtt: s.rtt }) : t('st.robot.fail'), s.robot);
    setStatus('st-fps', t('st.fps', { fps: s.fps }), s.fps > 0);
    setMode(s.mode, false);
    setEstop(s.estop);
    if (s.video !== undefined && s.video !== ui.video) showVideo(s.video);
    if (s.dominant !== undefined) showDominant(s.dominant);
    // Đồng bộ thanh trượt với server (trừ lúc đang kéo bằng chuột hoặc bằng tay)
    const free = (id) => document.activeElement !== $(id) && HandCursor.busyEl() !== $(id);
    if (s.speed !== undefined && free('speed')) showSpeed(Math.round(s.speed * 100));
    if (s.region !== undefined && free('region')) showRegion(Math.round(s.region * 100));
  }

  function renderHands() {
    const other = ui.dominant === 'right' ? 'left' : 'right';
    const manual = ui.mode === 'manual';  // thủ công: chỉ một tay, tay nào cũng điều khiển giao diện
    setStatus('st-hand-ui', manual ? t('hand.ui') : t('hand.ui.side', { side: side(ui.dominant) }), ui.hands.ui);
    setStatus('st-hand-drive', t('hand.drive.side', { side: side(other) }), ui.hands.drive);
  }

  function onTelemetry({ out, gesture, hands }) {
    if (hands) { ui.hands = hands; renderHands(); }
    $('r-vx').textContent = out.vx.toFixed(2);
    $('r-vy').textContent = out.vy.toFixed(2);
    $('r-w').textContent = out.w.toFixed(2);
    drawMotion(out);
    $('gesture-now').textContent = gesture ? t(`gn.${gesture}`) : t('nohand');
    document.querySelectorAll('.gestures li').forEach((li) => {
      li.setAttribute('aria-current', String(!!gesture && li.dataset.g.split(' ').includes(gesture)));
    });
  }

  // Sơ đồ nhìn từ trên xuống, mũi robot hướng lên màn hình.
  // Mũi tên = (vx, vy), cung tròn = w. Độ dài tỉ lệ với tốc độ (1.0 = tối đa).
  function drawMotion({ vx, vy, w }) {
    const vec = $('vec');
    const R = 70;
    vec.setAttribute('x2', -vy * R); // vy > 0 là sang trái
    vec.setAttribute('y2', -vx * R); // vx > 0 là lên trên màn hình
    vec.style.visibility = Math.hypot(vx, vy) > 0.01 ? 'visible' : 'hidden';

    const arc = $('arc');
    if (Math.abs(w) < 0.01) {
      arc.removeAttribute('d');
      return;
    }
    const r = 85;
    const end = Math.PI / 2 + Math.max(-0.95, Math.min(0.95, w)) * Math.PI; // bắt đầu ở đỉnh vòng
    const x = r * Math.cos(end);
    const y = -r * Math.sin(end);
    arc.setAttribute('d', `M 0 ${-r} A ${r} ${r} 0 0 ${w > 0 ? 0 : 1} ${x.toFixed(1)} ${y.toFixed(1)}`);
  }

  function setMode(mode, notify) {
    ui.mode = mode;
    document.body.dataset.mode = mode;
    renderHands();
    $('mode-manual').setAttribute('aria-pressed', String(mode === 'manual'));
    $('mode-gesture').setAttribute('aria-pressed', String(mode === 'gesture'));
    if (notify) send({ type: 'mode', mode });
  }

  function setEstop(on) {
    ui.estop = on;
    const b = $('estop');
    b.setAttribute('aria-pressed', String(on));
    b.textContent = on ? t('estop.on') : t('estop');
  }

  $('mode-manual').onclick = () => setMode('manual', true);
  $('mode-gesture').onclick = () => setMode('gesture', true);
  $('estop').onclick = () => send({ type: 'estop', on: !ui.estop });

  // ---------- Tốc độ ----------
  // Một thanh cho cả 2 chế độ: thủ công thì nhân ngay ở đây, cử chỉ thì server dùng giá trị gửi lên
  function showSpeed(pct) {
    ui.speed = pct / 100;
    $('speed').value = pct;
    $('speed-out').textContent = `${pct}%`;
  }
  $('speed').oninput = (e) => {
    showSpeed(Number(e.target.value));
    send({ type: 'speed', value: ui.speed });
  };

  // ---------- Cần điều khiển (pad) ----------
  // Dùng chung cho chuột (pointer events) và con trỏ tay (HandCursor)
  function padPoint(clientX, clientY) {
    const r = pad.getBoundingClientRect();
    let dx = (clientX - (r.left + r.width / 2)) / (r.width / 2);
    let dy = (clientY - (r.top + r.height / 2)) / (r.height / 2);
    const m = Math.hypot(dx, dy);
    if (m > 1) { dx /= m; dy /= m; }
    input.pad = { x: dx, y: -dy }; // y > 0 là kéo lên
  }
  pad.addEventListener('pointerdown', (e) => { pad.setPointerCapture(e.pointerId); padPoint(e.clientX, e.clientY); });
  pad.addEventListener('pointermove', (e) => { if (pad.hasPointerCapture(e.pointerId)) padPoint(e.clientX, e.clientY); });
  const padEnd = () => { input.pad = { x: 0, y: 0 }; };
  pad.addEventListener('pointerup', padEnd);
  pad.addEventListener('pointercancel', padEnd);

  // ---------- Nút xoay (giữ để xoay) ----------
  const HOLD = { 'rot-l': 1, 'rot-r': -1 };  // xoay trái = ngược chiều kim đồng hồ = w dương
  const holdStart = (id) => { input.rot = HOLD[id]; };
  const holdEnd = (id) => { if (input.rot === HOLD[id]) input.rot = 0; };
  for (const id of Object.keys(HOLD)) {
    const b = $(id);
    b.addEventListener('pointerdown', (e) => { b.setPointerCapture(e.pointerId); holdStart(id); });
    b.addEventListener('pointerup', () => holdEnd(id));
    b.addEventListener('pointercancel', () => holdEnd(id));
  }

  // ---------- Bàn phím ----------
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
      e.preventDefault();
      if (!ui.estop) send({ type: 'estop', on: true }); // Space chỉ để dừng, không mở khóa
      return;
    }
    if (e.key === 'Escape') openSettings(false);
    if (e.key.startsWith('Arrow')) e.preventDefault(); // không để mũi tên cuộn trang
    input.keys.add(e.key.toLowerCase());
  });
  window.addEventListener('keyup', (e) => input.keys.delete(e.key.toLowerCase()));
  window.addEventListener('blur', () => input.keys.clear());

  // ---------- Tính lệnh thủ công và gửi định kỳ ----------
  function current() {
    const k = input.keys;
    const on = (...keys) => (keys.some((key) => k.has(key)) ? 1 : 0);
    const fwd = input.pad.y + on('w', 'arrowup') - on('s', 'arrowdown');
    const left = -input.pad.x + on('a', 'arrowleft') - on('d', 'arrowright');
    const turn = input.rot + (k.has('q') ? 1 : 0) - (k.has('e') ? 1 : 0);
    const c = (v) => Math.max(-1, Math.min(1, v)) * ui.speed;
    return { vx: c(fwd), vy: c(left), w: c(turn) };
  }

  function showKnob() {
    const r = pad.clientWidth / 2 - knob.offsetWidth / 2;
    knob.style.transform =
      `translate(calc(-50% + ${input.pad.x * r}px), calc(-50% + ${-input.pad.y * r}px))`;
  }

  // ---------- Ẩn / hiện hình camera ----------
  // Chỉ ẩn hình trên giao diện; camera vẫn chạy vì còn dùng để nhận tay (tắt hẳn thì không bật lại bằng tay được)
  function showVideo(on) {
    ui.video = on;
    const b = $('toggle-video');
    b.setAttribute('aria-pressed', String(!on));
    b.textContent = on ? t('video.hide') : t('video.show');
    if (!on) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  $('toggle-video').onclick = () => send({ type: 'video', on: !ui.video });

  // ---------- Cài đặt ----------
  const settings = $('settings');
  function openSettings(on) {
    settings.hidden = !on;
    $('open-settings').setAttribute('aria-pressed', String(on));
  }
  $('open-settings').onclick = () => openSettings(settings.hidden);
  $('settings-close').onclick = () => openSettings(false);

  function showDominant(side) {
    ui.dominant = side;
    $('dom-right').setAttribute('aria-pressed', String(side === 'right'));
    $('dom-left').setAttribute('aria-pressed', String(side === 'left'));
    renderHands();
  }
  $('dom-right').onclick = () => send({ type: 'settings', dominant: 'right' });
  $('dom-left').onclick = () => send({ type: 'settings', dominant: 'left' });

  function showToggle(id, on) {
    const b = $(id);
    b.setAttribute('aria-pressed', String(on));
    b.textContent = on ? t('on') : t('off');
  }
  function showDwellMs(ms) {
    $('dwell-ms').value = ms;
    $('dwell-out').textContent = `${(ms / 1000).toFixed(1)} s`;
  }
  function showRegion(pct) {
    ui.region = pct / 100;
    $('region').value = pct;
    $('region-out').textContent = `${pct}%`;
  }
  $('opt-dwell').onclick = () => { cfg.dwellOn = !cfg.dwellOn; showToggle('opt-dwell', cfg.dwellOn); HandCursor.saveCfg(); };
  $('opt-two').onclick = () => { cfg.twoFinger = !cfg.twoFinger; showToggle('opt-two', cfg.twoFinger); HandCursor.saveCfg(); };
  $('dwell-ms').oninput = (e) => { cfg.dwellMs = Number(e.target.value); showDwellMs(cfg.dwellMs); HandCursor.saveCfg(); };
  $('region').oninput = (e) => { showRegion(Number(e.target.value)); send({ type: 'settings', region: ui.region }); };
  showToggle('opt-dwell', cfg.dwellOn);
  showToggle('opt-two', cfg.twoFinger);
  showDwellMs(cfg.dwellMs);

  // ---------- Thẻ thông số khi rê con trỏ ----------
  const INFO = {
    'mode-manual': () => t('i.mode-manual'),
    'mode-gesture': () => t('i.mode-gesture'),
    'toggle-video': () => (ui.video ? t('i.video.hide') : t('i.video.show')),
    'open-settings': () => t('i.open-settings'),
    'lang': () => t('lang.info'),
    'estop': () => t('i.estop'),
    'speed': () => t('i.speed', { pct: Math.round(ui.speed * 100) }),
    'rot-l': () => t('i.rot-l'),
    'rot-r': () => t('i.rot-r'),
    'pad': () => t('i.pad'),
    'st-link': () => t('i.st-link'),
    'st-camera': () => (ui.camera ? t('i.camera.ok') : t('i.camera.fail')),
    'st-robot': () => (ui.robot ? t('i.robot.ok', { rtt: ui.rtt }) : t('i.robot.fail')),
    'st-fps': () => t('i.st-fps', { fps: ui.fps }),
    'st-hand-ui': () => t('i.st-hand-ui', { side: side(ui.dominant) }),
    'st-hand-drive': () => t('i.st-hand-drive', { side: side(ui.dominant === 'right' ? 'left' : 'right') }),
    'dom-right': () => t('i.dom-right'),
    'dom-left': () => t('i.dom-left'),
    'opt-dwell': () => t('i.opt-dwell'),
    'dwell-ms': () => t('i.dwell-ms', { s: (cfg.dwellMs / 1000).toFixed(1) }),
    'opt-two': () => t('i.opt-two'),
    'region': () => t('i.region', { pct: Math.round(ui.region * 100) }),
    'settings-close': () => t('i.settings-close'),
  };

  // ---------- Ngôn ngữ ----------
  // Đổi chữ cố định (I18N.apply) rồi vẽ lại các chữ phụ thuộc trạng thái
  function renderLang() {
    I18N.apply();
    setStatus('st-link', ws && ws.readyState === WebSocket.OPEN ? t('st.link') : t('st.link.retry'),
      !!ws && ws.readyState === WebSocket.OPEN);
    if (lastStatus) onStatus(lastStatus);
    else setStatus('st-fps', t('st.fps', { fps: 0 }), false);
    renderHands();
    setEstop(ui.estop);
    showVideo(ui.video);
    showToggle('opt-dwell', cfg.dwellOn);
    showToggle('opt-two', cfg.twoFinger);
  }
  $('lang').onclick = () => { I18N.set(I18N.lang === 'vi' ? 'en' : 'vi'); renderLang(); };
  // Hình camera phủ cửa sổ theo object-fit (cover trên máy tính): đổi tọa độ khung camera (0..1)
  // sang pixel cửa sổ đúng theo phép đó, để con trỏ trùng đầu ngón tay trên hình.
  function frameToWindow(u, v) {
    const r = canvas.getBoundingClientRect();
    const sx = r.width / canvas.width, sy = r.height / canvas.height;
    const s = getComputedStyle(canvas).objectFit === 'cover' ? Math.max(sx, sy) : Math.min(sx, sy);
    const w = canvas.width * s, h = canvas.height * s;
    return [r.left + (r.width - w) / 2 + u * w, r.top + (r.height - h) / 2 + v * h];
  }

  Object.assign(HandCursor.hooks, {
    toScreen: frameToWindow,
    padPoint, padRelease: padEnd, holdStart, holdEnd,
    info: (el) => (INFO[el.id] ? INFO[el.id]() : ''),
  });

  setInterval(() => {
    if (ui.mode === 'manual') {
      showKnob();
      send({ type: 'cmd', ...current() });
    }
    // Gợi ý khi chưa có hình
    const noVideo = ui.video && performance.now() - ui.lastFrame > 1500;
    const hint = $('hint');
    hint.hidden = ui.video && !noVideo;
    if (!ui.video) {
      hint.textContent = t('hint.hidden');
    } else if (noVideo) {
      hint.textContent = ui.camera ? t('hint.wait') : t('hint.nocam');
    }
  }, 1000 / SEND_HZ);

  renderLang();
  connect();
})();
