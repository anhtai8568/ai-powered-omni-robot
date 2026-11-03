// Nhận lệnh (vx, vy, w) từ laptop qua WiFi.
//
// ESP32 tự phát WiFi (SoftAP), laptop bắt vào, không cần mạng bên ngoài.
// Giao thức UDP, gói tin dạng chữ để dễ đọc khi gỡ lỗi:
//   laptop -> ESP32:  "C <seq> <vx> <vy> <w>"   vd "C 12 0.500 -0.200 0.100"
//   ESP32 -> laptop:  "A <seq>"                  để laptop biết robot còn sống và đo độ trễ
// Dùng UDP thay vì TCP: chỉ lệnh mới nhất có giá trị, mất gói thì gói sau 50 ms thay thế,
// không phải chờ gửi lại như TCP.
//
// Chỉ một máy được điều khiển: máy gửi lệnh đầu tiên thành "chủ", lệnh từ máy khác bị bỏ
// qua (không trả lời, nên bên đó thấy "chưa kết nối"). Chủ im lặng quá timeout_ms thì
// robot dừng và máy khác mới được giành quyền.
#pragma once

#include <WiFi.h>
#include <WiFiUdp.h>

struct Command {
  float vx = 0, vy = 0, w = 0;
};

class CommandLink {
 public:
  CommandLink(const char* ssid, const char* password, uint16_t port, uint32_t timeout_ms)
      : ssid_(ssid), password_(password), port_(port), timeout_ms_(timeout_ms) {}

  void begin() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(ssid_, password_);
    WiFi.setSleep(false);  // tắt tiết kiệm điện WiFi để giảm độ trễ
    udp_.begin(port_);
  }

  // Gọi liên tục trong loop(). Trả về true nếu vừa nhận được lệnh mới.
  bool poll() {
    bool got = false;
    int len;
    while ((len = udp_.parsePacket()) > 0) {  // đọc hết, chỉ giữ gói mới nhất
      char buf[64];
      len = udp_.read(buf, sizeof(buf) - 1);
      if (len <= 0) continue;
      buf[len] = '\0';
      unsigned long seq;
      Command c;
      if (sscanf(buf, "C %lu %f %f %f", &seq, &c.vx, &c.vy, &c.w) == 4) {
        IPAddress ip = udp_.remoteIP();
        uint16_t port = udp_.remotePort();
        if (alive() && (ip != owner_ip_ || port != owner_port_)) continue;  // không phải chủ
        owner_ip_ = ip;
        owner_port_ = port;
        cmd_ = c;
        last_ms_ = millis();
        packets_++;
        got = true;
        udp_.beginPacket(ip, port);
        udp_.printf("A %lu", seq);
        udp_.endPacket();
      }
    }
    return got;
  }

  // Có lệnh mới trong timeout_ms gần đây không. Không có -> phải dừng robot.
  bool alive() const { return last_ms_ != 0 && millis() - last_ms_ < timeout_ms_; }

  // Lệnh hiện tại; trả về 0 hết nếu đã mất liên lạc (an toàn).
  Command command() const { return alive() ? cmd_ : Command{}; }

  uint32_t packets() const { return packets_; }
  int clients() const { return WiFi.softAPgetStationNum(); }

 private:
  const char* ssid_;
  const char* password_;
  uint16_t port_;
  uint32_t timeout_ms_;
  WiFiUDP udp_;
  Command cmd_;
  IPAddress owner_ip_;
  uint16_t owner_port_ = 0;
  uint32_t last_ms_ = 0;
  uint32_t packets_ = 0;
};
