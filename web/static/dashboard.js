// Dashboard điều khiển robot.
// Quy ước (chuẩn ROS): vx > 0 tiến, vy > 0 sang trái, w > 0 xoay ngược chiều kim đồng hồ.
(() => {
  const $ = (id) => document.getElementById(id);
  const canvas = $('view');
  const ctx = canvas.getContext('2d');
  const pad = $('pad');
  const knob = $('knob');

  const SEND_HZ = 20;
  const input = { pad: { x: 0, y: 0 }, rot: 0, keys: new Set() };
  const ui = { mode: 'manual', estop: false, speed: 0.5, lastFrame: 0, camera: false };
  let ws = null;
  let seq = 0;
  let decoding = false;

  // ---------- Kết nối ----------
  function setChip(id, text, ok) {
    const el = $(id);
    el.textContent = text;
    el.dataset.ok = String(ok);
  }

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/dashboard`);
    ws.onopen = () => setChip('chip-link', 'Máy chủ: đã kết nối', true);
    ws.onclose = () => {
      setChip('chip-link', 'Máy chủ: mất kết nối, đang nối lại', false);
      setTimeout(connect, 1000);
    };
    ws.onmessage = (e) => {
      if (typeof e.data === 'string') onStatus(JSON.parse(e.data));
      else drawFrame(e.data);
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

  // ---------- Trạng thái từ máy chủ ----------
  function onStatus(s) {
    ui.camera = s.camera;
    setChip('chip-camera', s.camera ? 'Camera: đang chạy' : 'Camera: chưa mở được', s.camera);
    setChip('chip-robot', s.robot ? 'Robot: đã kết nối' : 'Robot: chưa kết nối', s.robot);
    setChip('chip-fps', `${s.fps} khung/giây`, s.fps > 0);
    setMode(s.mode, false);
    setEstop(s.estop);
    if (s.mode === 'gesture') showReadout(s.out.vx, s.out.vy, s.out.w);
  }

  function setMode(mode, notify) {
    ui.mode = mode;
    $('mode-manual').setAttribute('aria-pressed', String(mode === 'manual'));
    $('mode-gesture').setAttribute('aria-pressed', String(mode === 'gesture'));
    pad.dataset.disabled = String(mode !== 'manual');
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
  $('speed').oninput = (e) => {
    ui.speed = e.target.value / 100;
    $('speed-out').textContent = `${e.target.value}%`;
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
    input.keys.add(e.key.toLowerCase());
  });
  window.addEventListener('keyup', (e) => input.keys.delete(e.key.toLowerCase()));
  window.addEventListener('blur', () => input.keys.clear());

  // ---------- Tính lệnh và gửi định kỳ ----------
  function current() {
    const k = input.keys;
    let fwd = input.pad.y + (k.has('w') ? 1 : 0) - (k.has('s') ? 1 : 0);
    let left = -input.pad.x + (k.has('a') ? 1 : 0) - (k.has('d') ? 1 : 0);
    let turn = input.rot + (k.has('q') ? 1 : 0) - (k.has('e') ? 1 : 0);
    const c = (v) => Math.max(-1, Math.min(1, v)) * ui.speed;
    return { vx: c(fwd), vy: c(left), w: c(turn) };
  }

  function showReadout(vx, vy, w) {
    $('r-vx').textContent = vx.toFixed(2);
    $('r-vy').textContent = vy.toFixed(2);
    $('r-w').textContent = w.toFixed(2);
  }

  function showKnob() {
    const r = pad.clientWidth / 2 - knob.offsetWidth / 2;
    knob.style.transform =
      `translate(calc(-50% + ${input.pad.x * r}px), calc(-50% + ${-input.pad.y * r}px))`;
  }

  setInterval(() => {
    showKnob();
    if (ui.mode === 'manual') {
      const c = current();
      showReadout(c.vx, c.vy, c.w);
      send({ type: 'cmd', vx: c.vx, vy: c.vy, w: c.w, seq: ++seq });
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