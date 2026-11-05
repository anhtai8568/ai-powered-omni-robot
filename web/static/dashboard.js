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
  const GESTURE_NAMES = {
    fist: 'Nắm tay: dừng', palm: 'Xòe tay: dừng',
    point_up: 'Chỉ lên: tiến', point_down: 'Chỉ xuống: lùi',
    point_left: 'Chỉ trái: sang trái', point_right: 'Chỉ phải: sang phải',
    point_up_left: 'Chỉ chéo trên trái: tiến chéo trái',
    point_up_right: 'Chỉ chéo trên phải: tiến chéo phải',
    point_down_left: 'Chỉ chéo dưới trái: lùi chéo trái',
    point_down_right: 'Chỉ chéo dưới phải: lùi chéo phải',
    v_left: 'Chữ V trái: xoay trái', v_right: 'Chữ V phải: xoay phải',
  };
  const input = { pad: { x: 0, y: 0 }, rot: 0, keys: new Set() };
  const ui = {
    mode: 'manual', estop: false, speed: 0.5, lastFrame: 0, camera: false,
    video: true, robot: false, rtt: null, fps: 0,
    dominant: 'right', region: 1.0, hands: { ui: false, drive: false },
  };
  const cfg = HandCursor.cfg;
  const SIDE = { right: 'phải', left: 'trái' };
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
    ws.onopen = () => setStatus('st-link', 'Máy chủ', true);
    ws.onclose = () => {
      setStatus('st-link', 'Máy chủ: đang nối lại', false);
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
    ui.camera = s.camera;
    ui.robot = s.robot;
    ui.rtt = s.rtt;
    ui.fps = s.fps;
    setStatus('st-camera', s.camera ? 'Camera' : 'Camera: chưa mở được', s.camera);
    setStatus('st-robot', s.robot ? `Robot ${s.rtt} ms` : 'Robot: chưa kết nối', s.robot);
    setStatus('st-fps', `${s.fps} khung/giây`, s.fps > 0);
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
    setStatus('st-hand-ui', manual ? 'Tay giao diện' : `Tay giao diện (${SIDE[ui.dominant]})`, ui.hands.ui);
    setStatus('st-hand-drive', `Tay lái (${SIDE[other]})`, ui.hands.drive);
  }

  function onTelemetry({ out, gesture, hands }) {
    if (hands) { ui.hands = hands; renderHands(); }
    $('r-vx').textContent = out.vx.toFixed(2);
    $('r-vy').textContent = out.vy.toFixed(2);
    $('r-w').textContent = out.w.toFixed(2);
    drawMotion(out);
    $('gesture-now').textContent = GESTURE_NAMES[gesture] || 'Không thấy tay';
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
    b.textContent = on ? 'Đã dừng. Bấm để mở khóa' : 'Dừng khẩn cấp';
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
    b.textContent = on ? 'Ẩn hình' : 'Hiện hình';
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
    b.textContent = on ? 'Bật' : 'Tắt';
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
    'mode-manual': () => 'Thủ công: chỉ cần một tay (tay nào cũng điều khiển giao diện), kéo cần lái hoặc dùng phím mũi tên, W A S D.',
    'mode-gesture': () => 'Cử chỉ tay: tay không thuận lái robot (ngón trỏ 8 hướng, chữ V xoay, nắm hoặc xòe tay là dừng).',
    'toggle-video': () => ui.video ? 'Ẩn hình camera trên giao diện. Camera vẫn chạy để nhận tay.' : 'Hiện lại hình camera.',
    'open-settings': () => 'Mở bảng cài đặt: tay thuận, cách click, vùng tay hoạt động.',
    'estop': () => 'Dừng khẩn cấp: ngắt lệnh ngay lập tức. Cũng có phím Space, hoặc nắm / xòe tay lái.',
    'speed': () => `Tốc độ tối đa ${Math.round(ui.speed * 100)}%. Giữ yên để nắm thanh rồi di ngón tay (tăng giảm theo), dừng yên để nhả. Hoặc bấm ngón giữa rồi kéo.`,
    'rot-l': () => 'Giữ để xoay trái (ngược chiều kim đồng hồ).',
    'rot-r': () => 'Giữ để xoay phải (cùng chiều kim đồng hồ).',
    'pad': () => 'Cần lái: kéo lên để tiến, sang ngang để đi ngang. Bấm ngón giữa rồi kéo.',
    'st-link': () => 'Kết nối WebSocket giữa trình duyệt và server.',
    'st-camera': () => ui.camera ? 'Camera laptop đang chạy.' : 'Chưa mở được camera. Kiểm tra ứng dụng khác đang dùng camera, hoặc CAMERA_INDEX=1.',
    'st-robot': () => ui.robot ? `Kết nối WiFi tới ESP32. Độ trễ khứ hồi ${ui.rtt} ms.` : 'Chưa kết nối ESP32. Nối WiFi omni-robot rồi chạy lại.',
    'st-fps': () => `Tốc độ khung hình camera sau khi chạy AI: ${ui.fps} khung/giây.`,
    'st-hand-ui': () => `Tay ${SIDE[ui.dominant]} điều khiển giao diện: ngón trỏ di con trỏ, giữ yên hoặc duỗi thêm ngón giữa để click.`,
    'st-hand-drive': () => `Tay ${SIDE[ui.dominant === 'right' ? 'left' : 'right']} lái robot trong chế độ Cử chỉ tay.`,
    'dom-right': () => 'Tay phải điều khiển giao diện, tay trái lái robot.',
    'dom-left': () => 'Tay trái điều khiển giao diện, tay phải lái robot.',
    'opt-dwell': () => 'Giữ yên con trỏ trên nút một lúc thì tự click, vòng tròn đầy dần.',
    'dwell-ms': () => `Giữ yên ${(cfg.dwellMs / 1000).toFixed(1)} giây thì click. Giữ yên để nắm thanh rồi di ngón tay.`,
    'opt-two': () => 'Duỗi thêm ngón giữa (cùng ngón trỏ) để click nhanh hoặc kéo.',
    'region': () => `Vùng tay hoạt động ${Math.round(ui.region * 100)}% khung camera. 100% là con trỏ đúng đầu ngón tay. Giữ yên để nắm thanh rồi di ngón tay.`,
    'settings-close': () => 'Đóng bảng cài đặt.',
  };
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
      hint.textContent = 'Hình camera đang ẩn. Camera vẫn chạy để nhận cử chỉ tay.';
    } else if (noVideo) {
      hint.textContent = ui.camera
        ? 'Đang chờ khung hình đầu tiên từ camera.'
        : 'Chưa mở được camera laptop. Kiểm tra xem ứng dụng khác có đang dùng camera không, hoặc chạy server với CAMERA_INDEX=1.';
    }
  }, 1000 / SEND_HZ);

  connect();
})();
