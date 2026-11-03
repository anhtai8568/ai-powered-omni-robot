"""
Gửi lệnh (vx, vy, w) từ laptop tới ESP32 qua UDP.

ESP32 tự phát WiFi "omni-robot" (IP cố định 192.168.4.1); laptop bắt vào WiFi đó.
Giao thức (xem firmware/src/command_link.h):
  laptop -> ESP32:  "C <seq> <vx> <vy> <w>"
  ESP32 -> laptop:  "A <seq>"   -> biết robot còn sống + đo độ trễ khứ hồi (RTT)

server.py tự dùng class RobotLink, không cần chạy file này.
Chạy trực tiếp chỉ để thử đường truyền khi KHÔNG chạy server (server đang giữ quyền điều
khiển thì ESP32 bỏ qua lệnh thử):  python communication/robot_link.py
"""
import asyncio
import os
import time

ROBOT_HOST = os.environ.get("ROBOT_HOST", "192.168.4.1")
ROBOT_PORT = int(os.environ.get("ROBOT_PORT", "4210"))
ALIVE_TIMEOUT = 1.0   # giây không nhận được trả lời -> coi như mất kết nối


class RobotLink(asyncio.DatagramProtocol):
    def __init__(self, host=ROBOT_HOST, port=ROBOT_PORT):
        self.addr = (host, port)
        self.rtt_ms = None
        self._transport = None
        self._seq = 0
        self._sent = {}          # seq -> thời điểm gửi, để tính RTT
        self._last_ack = 0.0

    async def start(self):
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 0))
        return self

    def close(self):
        if self._transport:
            self._transport.close()

    @property
    def connected(self) -> bool:
        return time.monotonic() - self._last_ack < ALIVE_TIMEOUT

    async def send(self, cmd: dict):
        self._seq += 1
        self._sent[self._seq] = time.monotonic()
        self._sent.pop(self._seq - 50, None)   # chỉ giữ 50 gói gần nhất
        msg = f"C {self._seq} {cmd['vx']:.3f} {cmd['vy']:.3f} {cmd['w']:.3f}"
        try:
            self._transport.sendto(msg.encode(), self.addr)
        except OSError:
            pass  # chưa bắt WiFi robot: bỏ qua, gói sau gửi lại

    # ---------- asyncio gọi các hàm dưới ----------
    def connection_made(self, transport):
        self._transport = transport

    def datagram_received(self, data, addr):
        parts = data.decode(errors="ignore").split()
        if len(parts) == 2 and parts[0] == "A" and parts[1].isdigit():
            sent = self._sent.pop(int(parts[1]), None)
            if sent is not None:
                self._last_ack = time.monotonic()
                self.rtt_ms = (self._last_ack - sent) * 1000

    def error_received(self, exc):
        pass  # vd ICMP "không tới được": coi như mất gói


if __name__ == "__main__":
    async def demo():
        link = await RobotLink().start()
        print(f"Gửi lệnh thử tới {link.addr[0]}:{link.addr[1]} (Ctrl+C để dừng)")
        t0 = time.monotonic()
        while True:
            vx = 0.3 if int(time.monotonic() - t0) % 4 < 2 else -0.3   # tiến 2 s, lùi 2 s
            await link.send({"vx": vx, "vy": 0.0, "w": 0.0})
            if link._seq % 20 == 0:
                state = f"kết nối, RTT {link.rtt_ms:.1f} ms" if link.connected else "chưa kết nối"
                print(f"vx={vx:+.1f}  {state}")
            await asyncio.sleep(0.05)

    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        pass
