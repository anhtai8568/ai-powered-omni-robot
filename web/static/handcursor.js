// Điều khiển giao diện bằng tay thuận.
//
// Server gửi tin {type:'cursor', pose, x, y, ax, ay} 30 lần/giây. (x, y) là đầu ngón trỏ trong khung
// camera (0..1); hooks.toScreen đổi sang tọa độ cửa sổ, nên con trỏ nằm đúng đầu ngón tay trên hình.
// (ax, ay) là điểm tác động: giống (x, y) khi chỉ trỏ, còn khi bấm thì là chỗ ngón trỏ đứng trước lúc
// duỗi ngón giữa, để bấm trúng nút dù đầu ngón trỏ xê dịch. Thiếu thì dùng (x, y).
// Tư thế pose:
//   none   không thấy tay
//   idle   tay không ở tư thế trỏ: con trỏ ẩn, không bấm được (đặt tay nghỉ không click nhầm)
//   point  ngón trỏ duỗi: di con trỏ; giữ yên trên nút một lúc thì click (dwell)
//   click  duỗi thêm ngón giữa: bấm; giữ rồi di chuyển là kéo
//
// Phần tử dùng được bằng tay là phần tử có thuộc tính data-hand:
//   button  click khi giữ yên hoặc khi bấm ngón giữa
//   slider  <input type=range>: giữ yên để nắm rồi di ngón tay (tăng giảm theo, không nhảy), hoặc bấm giữ rồi kéo
//   pad     cần lái: bấm giữ rồi kéo
//   hold    nút giữ để chạy (xoay): bấm giữ, nhả thì thôi
//   info    chỉ rê để xem thông số
// Rê con trỏ lên bất kỳ phần tử nào ở trên khoảng 0.5 giây thì hiện thẻ thông số.
window.HandCursor = (() => {
  const cfg = { dwellOn: true, dwellMs: 800, twoFinger: true };
  const DWELL_RADIUS = 30;  // px: con trỏ lệch quá mức này thì giữ yên phải tính lại từ đầu
  const INFO_MS = 500;      // giây rê lâu thì hiện thẻ thông số
  const GRAB_MOVED = 12;    // px: ngón tay đi quá mức này kể từ lúc nắm thanh thì tính là đã bắt đầu kéo
  const GRAB_STILL = 10;    // px: đang nắm thanh, ngón tay lệch quá mức này thì tính là chưa đứng yên
  const GRAB_IDLE_MS = 3000;  // nắm thanh mà không di chuyển lần nào thì tự nhả sau chừng này
  const RING = 2 * Math.PI * 14;

  // dashboard.js gắn các hàm này vào
  const hooks = {
    padPoint() {}, padRelease() {}, holdStart() {}, holdEnd() {},
    info: () => '',
    toScreen: (u, v) => [u * innerWidth, v * innerHeight],  // (khung camera 0..1) -> pixel cửa sổ
  };

  let cursorEl = null, ringEl = null, infoEl = null;
  let hoverEl = null, hoverSince = 0;
  let dwell = null;     // {el, x, y, t0, fired}
  let pressed = null;   // {el}: phần tử đang bị bấm giữ
  let px = 0, py = 0;   // điểm tác động (dùng để chọn nút, kéo)

  function loadCfg() {
    try {
      Object.assign(cfg, JSON.parse(localStorage.getItem('handcursor') || '{}'));
    } catch (_) { /* không có localStorage: dùng mặc định */ }
  }
  function saveCfg() {
    try { localStorage.setItem('handcursor', JSON.stringify(cfg)); } catch (_) { /* bỏ qua */ }
  }

  function ensureDom() {
    if (cursorEl) return;
    cursorEl = document.createElement('div');
    cursorEl.className = 'hand-cursor';
    cursorEl.hidden = true;
    cursorEl.style.cssText = 'position:fixed;left:0;top:0;pointer-events:none;z-index:1000';
    cursorEl.innerHTML =
      '<svg width="40" height="40" viewBox="-20 -20 40 40" aria-hidden="true">' +
      '<circle class="hc-dot" r="4"/><circle class="hc-track" r="14"/>' +
      `<circle class="hc-ring" r="14" stroke-dasharray="${RING}" stroke-dashoffset="${RING}" transform="rotate(-90)"/></svg>`;
    ringEl = cursorEl.querySelector('.hc-ring');
    infoEl = document.createElement('div');
    infoEl.className = 'info-card';
    infoEl.hidden = true;
    infoEl.style.cssText = 'position:fixed;pointer-events:none;z-index:1001';
    document.body.append(cursorEl, infoEl);
  }

  function elementAt(x, y) {
    const e = document.elementFromPoint(x, y);
    return e ? e.closest('[data-hand]') : null;
  }

  function setRing(p) {
    ringEl.setAttribute('stroke-dashoffset', String(RING * (1 - p)));
  }

  function flash() {
    cursorEl.classList.remove('flash');
    void cursorEl.offsetWidth;  // khởi động lại hiệu ứng
    cursorEl.classList.add('flash');
  }

  // ---------- rê: viền nổi bật + thẻ thông số ----------
  function showInfo(el) {
    const text = hooks.info(el) || el.dataset.info || '';
    if (!text) { infoEl.hidden = true; return; }
    infoEl.textContent = text;
    infoEl.hidden = false;
    const r = el.getBoundingClientRect();
    const w = infoEl.offsetWidth, h = infoEl.offsetHeight;
    const below = r.bottom + 10 + h < innerHeight;
    infoEl.style.top = `${below ? r.bottom + 10 : Math.max(8, r.top - 10 - h)}px`;
    infoEl.style.left = `${Math.min(Math.max(8, r.left + r.width / 2 - w / 2), innerWidth - w - 8)}px`;
  }

  function setHover(el, now) {
    if (el !== hoverEl) {
      if (hoverEl) hoverEl.classList.remove('hand-hover');
      hoverEl = el;
      hoverSince = now;
      if (el) el.classList.add('hand-hover');
      infoEl.hidden = true;
    }
    if (el && now - hoverSince >= INFO_MS) showInfo(el);
  }

  // ---------- thanh trượt: kéo TƯƠNG ĐỐI theo ngón tay ----------
  // Nắm thanh thì giá trị KHÔNG nhảy tới chỗ ngón tay đang đứng; ngón tay đi một đoạn thì giá trị đổi
  // đúng một đoạn như thế (đi hết chiều dài thanh = đi hết thang giá trị).
  //   how = 'dwell': nắm bằng cách giữ yên. Nhả bằng cách dừng yên lần nữa, hạ tay, hoặc bấm ngón giữa.
  //   how = 'press': nắm bằng ngón giữa, nhả ngón giữa là xong.
  let grab = null;  // {el, how, x0, y0, v0, moved, still:{x,y,t0}}

  function startGrab(el, how, now) {
    grab = { el, how, x0: px, y0: py, v0: Number(el.value), moved: how === 'press', still: { x: px, y: py, t0: now } };
    el.classList.add('hand-grab');
    flash();
  }

  function endGrab(now = 0) {
    if (!grab) return;
    grab.el.classList.remove('hand-grab');
    // Phải di chuyển ra khỏi chỗ này rồi mới nắm lại được (không nắm lại ngay khi vừa nhả)
    dwell = { el: grab.el, x: px, y: py, t0: now, fired: true };
    setRing(0);
    if (grab.how === 'dwell') flash();
    grab = null;
  }

  function drag() {
    const el = grab.el;
    const r = el.getBoundingClientRect();
    const min = Number(el.min), max = Number(el.max), step = Number(el.step) || 1;
    const raw = grab.v0 + (px - grab.x0) / r.width * (max - min);
    const v = Math.min(max, Math.max(min, Math.round((raw - min) / step) * step + min));
    if (Number(el.value) !== v) {
      el.value = v;
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  function dwellGrabStep(now) {  // đang nắm bằng giữ yên: bám theo ngón tay, dừng yên thì nhả
    drag();
    if (!grab.moved && Math.hypot(px - grab.x0, py - grab.y0) > GRAB_MOVED) grab.moved = true;
    if (Math.hypot(px - grab.still.x, py - grab.still.y) > GRAB_STILL) grab.still = { x: px, y: py, t0: now };
    // Đã di chuyển rồi dừng lại: nhả sau dwellMs. Chưa di chuyển lần nào: đợi lâu hơn (GRAB_IDLE_MS)
    const p = Math.min(1, (now - grab.still.t0) / (grab.moved ? cfg.dwellMs : GRAB_IDLE_MS));
    setRing(p);
    if (p >= 1) endGrab(now);
  }

  // ---------- thao tác lên phần tử ----------
  function activate(el, now) {  // click do giữ yên
    const type = el.dataset.hand;
    if (type === 'button') el.click();
    else if (type === 'slider') startGrab(el, 'dwell', now);
  }

  function press(el, now) {  // pose click
    if (!pressed) {
      pressed = { el };
      if (!el) return;
      flash();
      const type = el.dataset.hand;
      if (type === 'button') el.click();
      else if (type === 'slider') startGrab(el, 'press', now);
      else if (type === 'pad') hooks.padPoint(px, py);
      else if (type === 'hold') hooks.holdStart(el.id);
      return;
    }
    const held = pressed.el;  // đang giữ: kéo theo phần tử đã bấm, dù con trỏ ra ngoài nó
    if (!held) return;
    const type = held.dataset.hand;
    if (type === 'slider' && grab && grab.how === 'press') drag();
    else if (type === 'pad') hooks.padPoint(px, py);
  }

  function release(now = 0) {
    if (!pressed) return;
    const el = pressed.el;
    pressed = null;
    if (!el) return;
    const type = el.dataset.hand;
    if (type === 'slider' && grab && grab.how === 'press') endGrab(now);
    else if (type === 'pad') hooks.padRelease();
    else if (type === 'hold') hooks.holdEnd(el.id);
  }

  // ---------- giữ yên để click ----------
  function resetDwell() {
    dwell = null;
    if (ringEl) setRing(0);
  }

  function dwellStep(el, now) {
    const type = el && el.dataset.hand;
    if (!cfg.dwellOn || (type !== 'button' && type !== 'slider')) { resetDwell(); return; }
    if (!dwell || dwell.el !== el || Math.hypot(px - dwell.x, py - dwell.y) > DWELL_RADIUS) {
      dwell = { el, x: px, y: py, t0: now, fired: false };
    }
    if (dwell.fired) return;  // đã click: phải di chuyển ra khỏi vùng mới click tiếp (không lặp liên tục)
    const p = Math.min(1, (now - dwell.t0) / cfg.dwellMs);
    setRing(p);
    if (p >= 1) {
      dwell.fired = true;
      setRing(0);
      flash();
      activate(el, now);
    }
  }

  // ---------- nhận tin từ server ----------
  function update(msg, now = performance.now()) {
    ensureDom();
    const clampX = (v) => Math.min(innerWidth, Math.max(0, v));
    const clampY = (v) => Math.min(innerHeight, Math.max(0, v));
    const [cx, cy] = hooks.toScreen(msg.x, msg.y);
    const [ax, ay] = hooks.toScreen(msg.ax ?? msg.x, msg.ay ?? msg.y);
    px = clampX(ax);
    py = clampY(ay);
    if (msg.pose !== 'point' && msg.pose !== 'click') {  // none hoặc idle
      release(now);
      endGrab(now);
      setHover(null, now);
      resetDwell();
      cursorEl.hidden = true;
      return;
    }
    cursorEl.hidden = false;
    cursorEl.style.transform = `translate(${clampX(cx) - 20}px, ${clampY(cy) - 20}px)`;
    const pressing = msg.pose === 'click' && cfg.twoFinger;
    cursorEl.classList.toggle('pressing', pressing);

    if (grab && grab.how === 'dwell') {
      if (!pressing) {  // đang nắm thanh trượt: chỉ bám theo ngón tay
        setHover(grab.el, now);
        dwellGrabStep(now);
        return;
      }
      endGrab(now);     // bấm ngón giữa = xác nhận, nhả thanh, rồi xử lý như một lần bấm bình thường
    }

    const el = elementAt(px, py);
    setHover(el, now);
    if (pressing) {
      resetDwell();
      press(el, now);
    } else {
      release(now);
      dwellStep(el, now);
    }
  }

  loadCfg();
  return {
    cfg, hooks, update, saveCfg,
    busyEl: () => (grab && grab.el) || (pressed && pressed.el) || null,  // phần tử đang bị kéo: đừng ghi đè giá trị của nó
  };
})();
