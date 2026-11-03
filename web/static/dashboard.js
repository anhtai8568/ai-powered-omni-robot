// Dashboard điều khiển robot.
// Quy ước (chuẩn ROS): vx > 0 tiến, vy > 0 sang trái, w > 0 xoay ngược chiều kim đồng hồ.
//
// Tin từ server:
//   status    (2 lần/giây)  kết nối, camera, fps, chế độ, dừng khẩn cấp
//   telemetry (20 lần/giây) lệnh thật đang gửi cho robot + cử chỉ AI thấy
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
  const ui = { mode: 'manual', estop: false, speed: 0.5, lastFrame: 0, camera: false };
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
    };
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  async function drawFrame(blob) {
    if (decoding) return; // bỏ khung nếu khung trước chưa giải mã xong
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
    setStatus('st-camera', s.camera ? 'Camera' : 'Camera: chưa mở được', s.camera);
    setStatus('st-robot', s.robot ? `Robot ${s.rtt} ms` : 'Robot: chưa kết nối', s.robot);
    setStatus('st-fps', `${s.fps} khung/giây`, s.fps > 0);
    setMode(s.mode, false);
    setEstop(s.estop);
    // Đồng bộ thanh tốc độ với server (trừ lúc đang kéo)
    if (s.speed !== undefined && document.activeElement !== $('speed')) showSpeed(Math.round(s.speed * 100));
  }

  function onTelemetry({ out, gesture }) {
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
  function padMove(e) {
    const r = pad.getBoundingClientRect();
    let dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    let dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    const m = Math.hypot(dx, dy);
    if (m > 1) { dx /= m; dy /= m; }
    input.pad = { x: dx, y: -dy }; // y > 0 là kéo lên
  }
  pad.addEventListener('pointerdown', (e) => { pad.setPointerCapture(e.pointerId); padMove(e); });
  pad.addEventListener('pointermove', (e) => { if (pad.hasPointerCapture(e.pointerId)) padMove(e); });
  const padEnd = () => { input.pad = { x: 0, y: 0 }; };
  pad.addEventListener('pointerup', padEnd);
  pad.addEventListener('pointercancel', padEnd);

  // ---------- Nút xoay (giữ để xoay) ----------
  function holdButton(id, value) {
    const b = $(id);
    b.addEventListener('pointerdown', (e) => { b.setPointerCapture(e.pointerId); input.rot = value; });
    const end = () => { if (input.rot === value) input.rot = 0; };
    b.addEventListener('pointerup', end);
    b.addEventListener('pointercancel', end);
  }
  holdButton('rot-l', 1);   // xoay trái = ngược chiều kim đồng hồ = w dương
  holdButton('rot-r', -1);

  // ---------- Bàn phím ----------
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
      e.preventDefault();
      if (!ui.estop) send({ type: 'estop', on: true }); // Space chỉ để dừng, không mở khóa
      return;
    }
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

  setInterval(() => {
    if (ui.mode === 'manual') {
      showKnob();
      send({ type: 'cmd', ...current() });
    }
    // Gợi ý khi chưa có hình
    const noVideo = performance.now() - ui.lastFrame > 1500;
    const hint = $('hint');
    hint.hidden = !noVideo;
    if (noVideo) {
      hint.textContent = ui.camera
        ? 'Đang chờ khung hình đầu tiên từ camera.'
        : 'Chưa mở được camera laptop. Kiểm tra xem ứng dụng khác có đang dùng camera không, hoặc chạy server với CAMERA_INDEX=1.';
    }
  }, 1000 / SEND_HZ);

  connect();
})();
