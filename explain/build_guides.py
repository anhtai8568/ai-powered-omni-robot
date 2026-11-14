"""Build the two .docx reading guides (VI + simple EN) for reports/research_paper.

Run from the repo root:  python explain/build_guides.py   (needs python-docx)
Figures are taken from reports/figures/, so rerun after reports/make_figures.py.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

REPO = Path(__file__).resolve().parent.parent
FIG = REPO / "reports" / "figures"
OUT = REPO / "explain"

BLUE = RGBColor(0x1F, 0x3A, 0x5F)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def add_rich(par, text, size=None):
    """**bold** markup inside text."""
    for i, part in enumerate(re.split(r"\*\*", text)):
        if not part:
            continue
        r = par.add_run(part)
        r.bold = i % 2 == 1
        if size:
            r.font.size = Pt(size)


class Builder:
    def __init__(self):
        self.d = Document()
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        for side in ("left_margin", "right_margin"):
            setattr(sec, side, Cm(2.2))
        sec.top_margin = sec.bottom_margin = Cm(2)
        st = self.d.styles
        normal = st["Normal"]
        normal.font.name = "Arial"
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        normal.font.size = Pt(11)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.2
        for name, size, before in (("Title", 22, 0), ("Heading 1", 16, 18),
                                   ("Heading 2", 13, 12), ("Heading 3", 11.5, 10)):
            s = st[name]
            s.font.name = "Arial"
            rpr = s.element.get_or_add_rPr()
            rf = rpr.find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts")
                rpr.append(rf)
            for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                rf.set(qn(a), "Arial")
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                if rf.get(qn(a)) is not None:
                    del rf.attrib[qn(a)]
            s.font.size = Pt(size)
            s.font.bold = True
            s.font.color.rgb = BLUE
            s.paragraph_format.space_before = Pt(before)
            s.paragraph_format.space_after = Pt(6)
            s.paragraph_format.keep_with_next = True

    def title(self, t, sub):
        p = self.d.add_paragraph(style="Title")
        p.add_run(t)
        p = self.d.add_paragraph()
        r = p.add_run(sub)
        r.italic = True
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    def h1(self, t):
        self.d.add_heading(t, level=1)

    def h2(self, t):
        self.d.add_heading(t, level=2)

    def h3(self, t):
        self.d.add_heading(t, level=3)

    def p(self, t):
        add_rich(self.d.add_paragraph(), t)

    def bullets(self, items):
        for it in items:
            add_rich(self.d.add_paragraph(style="List Bullet"), it)

    def steps(self, items):
        for it in items:
            add_rich(self.d.add_paragraph(style="List Number"), it)
        # restart numbering for the next list: python-docx shares one list, so
        # prefix numbers manually instead
    def nsteps(self, items):
        for i, it in enumerate(items, 1):
            par = self.d.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.8)
            par.paragraph_format.first_line_indent = Cm(-0.6)
            add_rich(par, f"**{i}.** " + it)

    def box(self, head, text, fill="EAF2FB"):
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.cell(0, 0)
        shade(c, fill)
        c.width = Cm(16.6)
        p0 = c.paragraphs[0]
        r = p0.add_run(head)
        r.bold = True
        r.font.color.rgb = BLUE
        for line in text if isinstance(text, list) else [text]:
            add_rich(c.add_paragraph(), line)
        self.d.add_paragraph()

    def fig(self, name, caption, width=15.5):
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.add_run().add_picture(str(FIG / name), width=Cm(width))
        cp = self.d.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(caption)
        r.italic = True
        r.font.size = Pt(9.5)

    def table(self, headers, rows, widths=None):
        t = self.d.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            shade(c, "1F3A5F")
            r = c.paragraphs[0].add_run(h)
            r.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
                add_rich(cells[i].paragraphs[0], v, size=9.5)
        if widths:
            t.autofit = False
            grid = t._tbl.tblGrid.findall(qn("w:gridCol"))
            for g, w in zip(grid, widths):
                g.set(qn("w:w"), str(int(w * 567)))
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        self.d.add_paragraph()

    def pagebreak(self):
        self.d.add_page_break()

    def save(self, path):
        OUT.mkdir(exist_ok=True)
        self.d.save(path)
        print("wrote", path)


# ---------------------------------------------------------------------------
def build_vi():
    b = Builder()
    b.title("Đọc hiểu bài báo nghiên cứu",
            "Giải thích bằng tiếng Việt cho bài: “A Vision-Based Dual-Mode Hand Gesture "
            "Interface … Four-Wheel Omnidirectional Mobile Robot” (reports/research_paper/paper_vi.pdf "
            "và paper_en.pdf). Hai bản vi và en có cùng nội dung, cùng hình, cùng số liệu.")

    b.box("Cách dùng tài liệu này", [
        "Mở bài báo (PDF) bên cạnh tài liệu này. Đọc theo thứ tự: **Phần 1** (bài báo nói gì) → "
        "**Phần 2** (kỹ năng đọc biểu đồ, dùng cho mọi hình) → **Phần 3** (đi lần lượt từng mục và "
        "từng hình của bài báo) → **Phần 4** (các con số cần nhớ và câu hỏi tự kiểm tra).",
        "Mỗi hình đều được giải thích theo 3 bước: **Hình này là gì** → **Đọc từng bước** → "
        "**Rút ra điều gì**.",
        "**Đánh số mục và bảng:** bản tiếng Anh dùng mẫu tạp chí **Elsevier** nên đánh số mục 1, 2.1, 4.2… và "
        "Bảng 1–4; bản tiếng Việt vẫn dùng mẫu **IEEE** nên đánh số mục I, II-A, IV-B… và Bảng I–IV. Tài liệu "
        "này ghi số mới trước, số kiểu IEEE trong ngoặc, ví dụ “Mục 2.1 (II-A)”; Bảng 1 = Bảng I, Bảng 2 = Bảng II… "
        "Số hình (Hình 1–6) giống nhau ở cả hai bản.",
    ])

    # ---------------- Part 1
    b.h1("Phần 1. Bài báo nói về điều gì? (đọc trong 2 phút)")
    b.p("**Vấn đề.** Khi điều khiển robot bằng cử chỉ tay, người ta thường chỉ dùng tay để ra lệnh "
        "“đi tới, đi lùi, rẽ…”. Muốn đổi chế độ, chỉnh tốc độ hay bấm dừng khẩn cấp thì vẫn phải quay "
        "lại dùng chuột hoặc bàn phím.")
    b.p("**Ý tưởng của bài.** Chỉ dùng **một webcam của laptop** cho cả hai việc cùng lúc:")
    b.bullets([
        "**Tay thuận** (tay phải) điều khiển **con trỏ chuột ảo** trên trang web dashboard: bấm nút, kéo thanh trượt.",
        "**Tay không thuận** (tay trái) **lái robot**: chỉ ngón trỏ theo 8 hướng, hai ngón để xoay, nắm tay để dừng.",
    ])
    b.p("Robot có **4 bánh omni xếp hình chữ X**, nên đi được mọi hướng (tới, ngang, chéo) và xoay tại chỗ. "
        "Laptop gửi lệnh qua Wi-Fi tới **ESP32** trên robot. ESP32 điều khiển tốc độ từng bánh 100 lần mỗi giây.")
    b.p("**Ba đóng góp chính** (mục 1 của bài):")
    b.nsteps([
        "Giao diện hai tay, có bộ **tự sửa nhãn tay trái/phải** (vì ảnh camera bị lật như gương).",
        "Kiến trúc **laptop ↔ ESP32 qua UDP** trên Wi-Fi riêng của robot, có khóa một người điều khiển, "
        "watchdog hai phía (mất tín hiệu thì dừng) và giới hạn gia tốc.",
        "Bộ điều khiển tốc độ từng bánh: **feedforward + PI** có chống bão hòa tích phân, tham số đo từ chính các động cơ.",
    ])
    b.p("**Kết quả chính** (từ 13.080 chu kỳ điều khiển ghi lại, khoảng 34 phút chạy thật):")
    b.table(["Đại lượng", "Kết quả", "Ý nghĩa đơn giản"], [
        ["Tốc độ camera + AI (không có tay)", "29,9 khung/giây; AI 18,5 ms/khung", "Gần đủ 30 fps của camera"],
        ["Có tay thật trong khung (phiên 2)", "18–25,5 fps; AI 45–56 ms", "Có tay thì AI chậm hơn rõ"],
        ["Độ trễ mạng khứ hồi (UDP)", "trung vị 6,6–8,1 ms", "Mạng rất nhanh, không phải điểm nghẽn"],
        ["Sai số tốc độ bánh", "trung bình 1,5–3,2 % tốc độ tối đa", "Bánh quay gần đúng tốc độ được ra lệnh"],
        ["Chuyển động thân robot (từ encoder)", "lệch 0,1–2,5 % so với lệnh", "Robot đi đúng hướng được ra lệnh"],
        ["Trễ từ khung camera → bánh đạt 50 % tốc độ", "427 ms (trung vị, 15 lần)", "Đây mới là phần chậm nhất"],
        ["Bộ lọc con trỏ và “neo điểm bấm” trên tay thật", "gần như không có lợi", "Kết quả âm, được báo cáo trung thực"],
    ], widths=[5.6, 5.2, 5.8])
    b.box("Điểm cần nhớ", "Bài báo chứng minh **phần robot và mạng hoạt động tốt** (số liệu mạnh). "
          "Phần **con trỏ trên tay thật** không tốt như mô phỏng, và bài nói thẳng điều đó. "
          "Tất cả chỉ từ **1 robot, 1 người điều khiển**, **chưa có khảo sát người dùng**.")

    # ---------------- Part 2
    b.pagebreak()
    b.h1("Phần 2. Kỹ năng nền: cách đọc biểu đồ và số liệu thống kê")
    b.p("Bài báo dùng một số khái niệm và kiểu biểu đồ lặp đi lặp lại. Hiểu phần này trước thì đọc hình nào cũng dễ.")

    b.h2("2.1. Quy tắc chung khi gặp bất kỳ biểu đồ nào")
    b.nsteps([
        "**Đọc tiêu đề và chú thích (caption)** dưới hình: hình đang so sánh cái gì?",
        "**Đọc trục ngang (x)** và **trục đứng (y)**: mỗi trục là đại lượng gì, **đơn vị** gì (ms, px, %, s)?",
        "**Đọc chú giải (legend)**: mỗi màu / kiểu đường là gì?",
        "**Tìm đường tham chiếu** (đường đứt, đường y = x, mốc 5 %…): đó là “ranh giới tốt/xấu”.",
        "Chỉ sau đó mới nhìn dữ liệu: cao hay thấp, trùng hay lệch, tập trung hay phân tán?",
    ])

    b.h2("2.2. Các con số thống kê hay gặp")
    b.table(["Thuật ngữ", "Nghĩa", "Ví dụ trong bài"], [
        ["**Trung bình (mean)**", "Cộng tất cả rồi chia cho số mẫu. Dễ bị kéo lệch bởi vài giá trị rất lớn.",
         "Sai số bánh trung bình 2,5 %"],
        ["**Trung vị (median)**", "Xếp các giá trị từ nhỏ đến lớn, lấy giá trị **ở giữa**. 50 % mẫu nhỏ hơn, 50 % lớn hơn. "
         "Không bị ảnh hưởng bởi vài giá trị bất thường.", "RTT trung vị 6,6 ms"],
        ["**Phân vị 95 (P95)**", "95 % mẫu nhỏ hơn giá trị này. Cho biết “trường hợp xấu nhưng vẫn thường gặp”.",
         "RTT P95 = 16,1 ms"],
        ["**Lớn nhất (max)**", "Giá trị tệ nhất xuất hiện **một lần**.", "RTT max = 909 ms"],
        ["**Đơn vị chuẩn hóa**", "Quy về thang 0 → 1. Với tốc độ bánh: **1,0 = 4300 xung encoder/giây** = tốc độ tối đa.",
         "Lệnh đi tới 0,472 = 47 % tốc độ tối đa"],
        ["**% của tốc độ tối đa (full scale)**", "Sai số chia cho tốc độ tối đa, không phải chia cho tốc độ đang chạy.",
         "Sai số 0,025 = 2,5 %"],
        ["**ms, px, fps**", "mili-giây (1/1000 s); điểm ảnh; số khung hình mỗi giây.", "30 fps → 33 ms/khung"],
    ], widths=[3.8, 7.7, 5.1])
    b.box("Vì sao bài hay dùng trung vị thay vì trung bình?",
          "Độ trễ mạng có lúc rất lớn (909 ms) nhưng chỉ xảy ra một lần. Nếu lấy trung bình, một giá trị đó kéo "
          "cả kết quả lên, trông như mạng chậm. **Trung vị** cho biết **trường hợp điển hình**, còn **P95 và max** "
          "cho biết **trường hợp xấu**. Bài luôn báo cả ba: trung vị / P95 / max.")

    b.h2("2.3. Các kiểu biểu đồ trong bài")
    b.h3("a) Sơ đồ khối (Hình 1)")
    b.p("Không có trục, không có số liệu đo. Mỗi hộp là một khối chức năng, mũi tên là dữ liệu đi từ khối này sang khối kia.")
    b.h3("b) Đồ thị theo thời gian (Hình 5a, 5b)")
    b.p("Trục x là thời gian. Thường có **2 đường**: **giá trị đặt** (cái mình muốn, đường đứt) và **giá trị đo** "
        "(cái thực tế xảy ra, đường liền). **Hai đường càng trùng nhau thì bộ điều khiển càng tốt.**")
    b.h3("c) Histogram – biểu đồ phân bố (Hình 4a, 6b)")
    b.p("Chia trục x thành nhiều **ô (bin)**, ví dụ 0–2 ms, 2–4 ms… Chiều cao mỗi cột = **có bao nhiêu mẫu rơi vào ô đó** "
        "(hoặc bao nhiêu phần trăm). Chỗ cột cao nhất là giá trị hay gặp nhất. Phần “đuôi” kéo dài sang phải là các "
        "trường hợp hiếm nhưng chậm.")
    b.p("**Thang log** (Hình 4a): trên trục y, mỗi vạch lớn **gấp 10 lần** vạch dưới: 10⁻³ = 0,1 %, 10⁻² = 1 %, "
        "10⁻¹ = 10 %. Dùng thang log để nhìn thấy cả cột rất cao (60 %) lẫn cột rất thấp (0,1 %) trên cùng một hình.")
    b.h3("d) Biểu đồ hộp – box plot (Hình 5d, 6a)")
    b.p("Tóm tắt cả một nhóm số liệu bằng một hình hộp:")
    b.bullets([
        "**Vạch ngang trong hộp** = trung vị.",
        "**Đáy và nắp hộp** = phân vị 25 và 75. Một nửa số mẫu nằm trong hộp. Hộp càng cao thì số liệu càng phân tán.",
        "**Râu** (đường kẻ trên và dưới) = khoảng mà hầu hết mẫu nằm trong. Trong Hình 5d râu là phân vị 5 → 95.",
        "**Hình thoi** (Hình 5d) = giá trị trung bình.",
    ])
    b.h3("e) Biểu đồ điểm có đường y = x (Hình 3)")
    b.p("Mỗi chấm là một lần thử. Đường chéo **y = x** là nơi hai đại lượng bằng nhau. Chấm **nằm trên** đường "
        "→ giá trị trục y lớn hơn; chấm **nằm dưới** → giá trị trục y nhỏ hơn.")
    b.h3("f) Biểu đồ cột đôi (Hình 4b)")
    b.p("Mỗi nhóm có 2 cột cạnh nhau để so sánh trực tiếp: **lệnh** và **kết quả đo**. Hai cột cao bằng nhau là tốt.")
    b.h3("g) Đường thẳng y = a + b·x (Hình 5c)")
    b.p("**a** = chỗ đường cắt trục đứng (giá trị khi x = 0). **b** = độ dốc (x tăng 1 thì y tăng bao nhiêu).")

    # ---------------- Part 3
    b.pagebreak()
    b.h1("Phần 3. Đọc bài báo từng mục, từng hình")

    b.h2("Tóm tắt (Abstract) và Từ khóa")
    b.p("Đoạn tóm tắt gói toàn bộ bài vào một đoạn văn: vấn đề → giải pháp → con số kết quả → giới hạn. Các con số "
        "trong tóm tắt chính là bảng ở Phần 1 của tài liệu này. Câu cuối “All results come from one robot and one "
        "operator, and no user study was performed” là **lời nói trung thực về giới hạn**: người đọc biết ngay độ tin "
        "cậy của kết quả.")

    b.h2("Mục 1 (I). Introduction (Giới thiệu)")
    b.bullets([
        "**Robot omni** đi được 3 chiều độc lập: **vₓ** (tới/lùi), **v_y** (sang trái/phải), **ω** (xoay). Điều khiển "
        "cả 3 cùng lúc khó hơn xe thường.",
        "**MediaPipe Hands** là mô hình AI tìm **21 điểm mốc** trên bàn tay (khớp ngón, đầu ngón, cổ tay).",
        "Vấn đề phần cứng: mạch L298N + động cơ rẻ có **vùng chết** (phải cấp đủ PWM thì bánh mới bắt đầu quay). "
        "Ngưỡng này khác nhau giữa các bánh tới **2,7 lần** (5,5 % đến 14,8 % PWM). Nếu cấp cùng PWM cho 4 bánh, "
        "robot sẽ đi lệch, tự xoay.",
    ])

    b.h2("Mục 2.1 (II-A). Kiến trúc Host–Edge — Hình 1")
    b.fig("fig_arch_vi.png", "Hình 1 trong bài – kiến trúc hệ thống.")
    b.h3("Hình này là gì?")
    b.p("Sơ đồ khối của toàn hệ thống. **Khung trái (HOST)** là laptop, **khung phải (EDGE)** là ESP32 trên robot.")
    b.h3("Đọc từng bước")
    b.nsteps([
        "**Bên laptop, đi từ trên xuống:** Camera (MJPG 1280×720, 30 fps, ảnh lật như gương, 2 bộ đệm) → MediaPipe tìm 21 điểm mốc "
        "của tối đa 2 tay trên **bản thu nhỏ rộng 640 px** (ảnh nét để hiển thị, ảnh nhỏ để AI chạy nhanh) → **RoleAssigner** quyết định tay nào là tay UI, tay nào là tay lái.",
        "Tách thành hai nhánh: **hộp vàng** = tay thuận điều khiển GUI (lọc One-Euro, neo điểm bấm FREEZE_BACK 0,2 s); "
        "**hộp xanh** = tay không thuận lái robot (8 hướng; GestureFilter 4/6 nghĩa là cần 4 khung liên tiếp để bắt đầu, 6 khung để dừng).",
        "Tay UI → **Web dashboard** (FastAPI + WebSocket). Tay lái → **control_loop 20 Hz** (gửi lệnh 20 lần/giây, "
        "tăng tốc tối đa 2,0/s, giảm tốc 4,0/s, ghi log CSV).",
        "**Mũi tên đỏ liền** ở trên cùng: lệnh UDP “C seq vx vy w” gửi sang robot 20 lần/giây.",
        "**Bên robot, đi từ trên xuống:** Wi-Fi phát riêng “omni-robot”, cổng UDP 4210, watchdog 300 ms (mất lệnh "
        "300 ms → dừng), chỉ nhận lệnh từ một máy → **động học ngược** (đổi vₓ, v_y, ω thành tốc độ 4 bánh) → "
        "**4 bộ điều khiển tốc độ, 100 Hz** → mạch L298N cấp điện cho động cơ; **encoder** đếm xung đo tốc độ thật, "
        "đưa ngược lên bộ điều khiển (mũi tên đi lên).",
        "**Mũi tên xanh đứt** ở dưới: robot trả lời “A seq” + 12 giá trị (mỗi bánh: tốc độ đặt, tốc độ đo, PWM).",
    ])
    b.h3("Rút ra điều gì?")
    b.p("Laptop lo phần **nặng** (AI, giao diện); ESP32 lo phần **nhanh và an toàn** (điều khiển bánh 100 Hz, tự dừng "
        "khi mất mạng). Có **2 lớp an toàn**: ESP32 dừng nếu 300 ms không có lệnh; laptop thay lệnh cũ hơn 0,4 s bằng 0.")

    b.h2("Mục 2.2 (II-B). Mô hình động học — Hình 2 và công thức (1), (2)")
    b.fig("fig_kin_vi.png", "Hình 2 trong bài – hình học cấu hình chữ X.", width=9)
    b.h3("Hình này là gì?")
    b.p("Nhìn robot **từ trên xuống**. Hình vuông là thân robot, 4 thanh đen nghiêng 45° là 4 bánh: "
        "**FL** (trước trái), **FR** (trước phải), **RL** (sau trái), **RR** (sau phải).")
    b.h3("Đọc từng bước")
    b.nsteps([
        "**Trục X_R** hướng lên = **phía trước** robot. **Trục Y_R** hướng sang trái = **bên trái**. Mũi tên cong: "
        "**ω > 0 là xoay ngược chiều kim đồng hồ** (CCW). Đây là quy ước chuẩn của ROS.",
        "**Mũi tên màu ở mỗi bánh** = hướng bánh đó **đẩy** robot khi quay dương. Vì bánh nghiêng 45°, mỗi bánh đẩy chéo.",
        "Ví dụ **đi thẳng tới**: cả 4 bánh quay dương. Các thành phần ngang triệt tiêu nhau, chỉ còn lực đẩy tới.",
        "Ví dụ **đi ngang sang trái**: FL và RR quay âm, FR và RL quay dương (hàng v_y trong ma trận: −1, +1, +1, −1). "
        "Các thành phần tới/lùi triệt tiêu, chỉ còn lực sang trái.",
    ])
    b.h3("Công thức nói gì (bằng lời)")
    b.bullets([
        "**(1) Động học ngược:** từ lệnh (vₓ, v_y, ω) nhân với ma trận 4×3 ra tốc độ 4 bánh. Nếu có bánh vượt quá 1,0 thì "
        "**chia cả 4 bánh cho cùng một số**, để robot vẫn đi **đúng hướng**, chỉ chậm lại. (Nếu cắt từng bánh riêng thì hướng đi bị méo.)",
        "**(2) Động học thuận:** làm ngược lại, từ tốc độ **đo được** của 4 bánh tính ra robot đang thực sự đi thế nào. "
        "Ma trận rất đơn giản: lấy chuyển vị rồi chia 4. Công thức này dùng để tạo **Bảng 3** và **Hình 4b**.",
        "Encoder: **8112 xung mỗi vòng bánh**; phần cứng PCNT của ESP32 đếm xung, có lọc nhiễu 12,5 µs.",
    ])

    b.h2("Mục 3 (III). Giao diện cử chỉ và điều khiển bánh")
    b.h3("3.1 (III-A). Ngón nào đang duỗi — công thức (3)")
    b.p("Một ngón được coi là **duỗi** nếu khoảng cách từ **cổ tay → đầu ngón** lớn hơn 1,15 lần khoảng cách "
        "**cổ tay → khớp giữa ngón**. Dùng **tỉ lệ** nên không phụ thuộc tay ở gần hay xa camera. Chỉ có ngón trỏ duỗi → "
        "đo góc chỉ, chia thành **8 hướng, mỗi hướng 45°**. Ngón trỏ + ngón giữa chỉ trái/phải → xoay. Nắm tay hoặc xòe tay → dừng.")
    b.h3("3.2 (III-B). Phân vai hai tay")
    b.p("Ảnh bị lật gương nên MediaPipe gọi nhầm tay trái thành tay phải. Bộ phân vai: có 2 tay thì dựa vào **vị trí cổ tay "
        "trái/phải trên ảnh**, đồng thời tự học xem nhãn có bị đảo không (điểm tin cậy cₖ, đổi quy ước khi cₖ < −0,6). Có 1 tay "
        "thì **bỏ phiếu trong 10 khung**. Một tay vừa biến mất mà tay còn lại di chuyển ít hơn 150 px → giữ nguyên vai cũ.")
    b.h3("3.3 (III-C). Con trỏ, neo điểm bấm, kéo thanh trượt, mép khung")
    b.bullets([
        "**Bộ lọc One-Euro:** tay đứng yên → lọc mạnh (con trỏ đỡ rung); tay di chuyển nhanh → lọc nhẹ (con trỏ không bị trễ).",
        "**Các tư thế tay UI:** chỉ ngón trỏ = di chuyển con trỏ (giữ yên 0,8 s = bấm); ngón trỏ + ngón giữa = bấm/kéo.",
        "**Neo điểm bấm (công thức 4):** khi giơ ngón giữa lên để bấm, đầu ngón trỏ có thể bị kéo lệch. Hệ thống lấy vị trí "
        "**0,2 s trước đó** làm điểm bấm. (Kết quả trên tay thật: cách này **không giúp được**, xem Hình 3.)",
        "**Ánh xạ gần mép khung:** khi tay sát mép ảnh, AI mất dấu tay. Vì vậy ở vùng giữa con trỏ đi đúng theo ngón tay, "
        "càng ra gần mép con trỏ càng đi **nhanh hơn ngón tay** (tối đa 1,35 lần), để chạm mép màn hình khi ngón tay còn cách "
        "mép ảnh 6 %. Bản đầu tiên tăng đột ngột (1,67 lần) làm con trỏ “chạy trước” ngón tay, nên đã được thay.",
    ])
    b.h3("3.4 (III-D). Điều khiển tốc độ từng bánh — công thức (5) và Bảng 1")
    b.p("Mỗi 10 ms, mỗi bánh tính PWM theo **3 phần cộng lại**:")
    b.bullets([
        "**Feedforward** uᶠᶠ = a + b·|r|: “đoán trước” cần bao nhiêu PWM cho tốc độ r. **a** = PWM tối thiểu để bánh bắt đầu "
        "quay (vùng chết), **b** = PWM thêm cho mỗi đơn vị tốc độ.",
        "**P** = Kp × sai số (Kp = 0,8): sửa ngay theo sai số hiện tại.",
        "**I** = tích lũy sai số (Ki = 6,0): sửa sai số nhỏ còn kéo dài. **Chống bão hòa:** không tích lũy khi đang tăng tốc "
        "hoặc khi PWM đã chạm trần, tránh vọt lố.",
    ])
    b.p("**Bảng 1** liệt kê a, b của từng bánh (đo khi nhấc bánh lên khỏi sàn) và sai số trung bình khi chạy trên sàn:")
    b.table(["Bánh", "a (PWM khởi động)", "b (độ dốc)", "Sai số v1 cử chỉ", "Sai số v2 hai tay"], [
        ["FL trước trái", "0,076", "0,470", "1,9 %", "2,5 %"],
        ["**FR trước phải**", "**0,148**", "**0,594**", "2,5 %", "2,6 %"],
        ["RL sau trái", "0,055", "0,453", "1,6 %", "2,3 %"],
        ["RR sau phải", "0,060", "0,464", "1,7 %", "2,5 %"],
    ], widths=[3.2, 3.4, 2.6, 3.6, 3.6])
    b.p("**Cách đọc:** bánh FR “cứng” nhất: cần tới 14,8 % PWM mới bắt đầu quay, gấp 2,7 lần bánh RL (5,5 %). Nhờ mỗi bánh "
        "có a, b riêng nên dù 4 bánh khác nhau, sai số vẫn đều quanh 2–2,6 %.")

    b.h2("Mục 4.1 (IV-A). Thiết lập thí nghiệm — Bảng 2")
    b.table(["Lần chạy", "Số dòng log", "Thời gian (s)", "RTT: trung vị / P95 / max (ms)"], [
        ["Thủ công (v1)", "3240", "1512", "7,8 / 22,5 / 97"],
        ["Cử chỉ (v1)", "4820", "247", "8,1 / 26,1 / 101"],
        ["Hai tay (v2)", "5020", "266", "6,6 / 16,1 / **909**"],
        ["Tổng", "13080", "2026", "–"],
    ], widths=[3.6, 3, 3, 7])
    b.p("**Cách đọc:** có 3 lần chạy thật trên sàn, log 20 dòng/giây. **RTT** (round-trip time) = thời gian từ lúc laptop gửi "
        "lệnh đến lúc nhận được phản hồi của robot. Hãy đọc từng cột: trung vị chỉ khoảng 7–8 ms (rất nhanh); 95 % gói tin "
        "dưới 16–26 ms; nhưng có **một lần tệ nhất 909 ms** ở lần chạy v2. Giá trị này lớn hơn watchdog 300 ms, nên lúc đó "
        "robot đã tự dừng: cơ chế an toàn hoạt động đúng.")
    b.p("Lần chạy thủ công dài hơn nhiều (1512 s) nhưng ít dòng hơn, vì log chủ yếu ghi khi đang lái.")

    b.h2("Mục 4.2 (IV-B). Thị giác máy và kết quả âm của con trỏ — Hình 3")
    b.p("**Tốc độ:** đo 359 khung liên tiếp, không có tay: **29,9 fps**, AI mất trung bình **18,5 ms** mỗi khung "
        "(P95 = 27,1 ms). Khi để driver chỉ giữ 1 bộ đệm thay vì 2, tốc độ tụt từ 28,9 xuống còn 14,5 fps.")
    b.p("**Kiểm thử:** 55 bài kiểm tra tự động với tay giả lập + 49 bài kiểm tra con trỏ trong trình duyệt. Tất cả đều đạt.")
    b.p("**Độ ổn định cử chỉ:** khoảng 94 % các đoạn cử chỉ kéo dài trên 0,3 s. Chỉ khoảng 6 % là đoạn rất ngắn, "
        "có thể là nhận nhầm, nhưng bài không kiểm chứng điều này.")
    b.p("**Kết quả âm:** trên tay **giả lập**, bộ lọc giảm rung 65,5 % và neo điểm bấm giảm độ lệch 83,6 %. Trên tay **thật** thì không như vậy:")
    b.bullets([
        "Rung: tay đứng yên 8 giây, đầu ngón thô dao động 2,26 px, con trỏ sau lọc 2,14 px, **chỉ giảm 5 %**.",
        "Bấm: đầu ngón chỉ dịch **1,65 px** khi giơ ngón giữa (giả lập giả định 29,2 px). Vậy là gần như không có gì để sửa.",
    ])
    b.fig("fig_real_vi.png", "Hình 3 trong bài – tay thật, 12 lần bấm.", width=9.5)
    b.h3("Hình này là gì?")
    b.p("Biểu đồ điểm. Mỗi chấm xanh là **một lần bấm thử** (tổng 12 lần).")
    b.h3("Đọc từng bước")
    b.nsteps([
        "**Trục ngang:** đầu ngón trỏ dịch bao nhiêu pixel khi giơ ngón giữa (nếu không có neo thì điểm bấm lệch đúng chừng này).",
        "**Trục đứng:** điểm bấm thực tế (có neo) dịch bao nhiêu pixel.",
        "**Đường đứt y = x:** nơi hai giá trị bằng nhau. Chấm **dưới** đường → neo **giúp** giảm lệch. Chấm **trên** đường → neo **làm lệch nhiều hơn**.",
        "Đếm: **11 trên 12 chấm nằm trên đường**, chỉ 1 chấm (x ≈ 3,5; y ≈ 2,7) nằm dưới.",
        "Nhìn độ lớn: mọi giá trị đều chỉ vài pixel (1–12 px). Vòng giữ để bấm có bán kính 30 px, nên trong thực tế ảnh hưởng tới việc bấm có lẽ nhỏ.",
    ])
    b.h3("Rút ra điều gì?")
    b.p("Trên tay thật, neo điểm bấm **không giúp mà còn làm lệch thêm khoảng 2,5 px**: nhìn lùi 0,2 s lại lấy phải vị trí "
        "khi ngón tay vẫn đang trôi nhẹ. Bài báo ghi rõ đây là **kết quả âm** (negative result). Viết vậy là trung thực "
        "và được đánh giá cao, nhưng chỉ có 12 lần bấm từ 1 người nên mới mang tính tham khảo.")

    b.h2("Mục 4.3 (IV-C). Độ trễ đường truyền — Hình 4")
    b.fig("fig_rtt_odo_vi.png", "Hình 4 trong bài – (a) phân bố RTT; (b) lệnh so với vận tốc tính từ encoder.")
    b.h3("Hình 4a – Histogram độ trễ khứ hồi UDP")
    b.nsteps([
        "**Trục ngang:** RTT tính bằng ms, từ 0 đến 60. Mọi gói chậm hơn 60 ms được dồn vào **cột cuối cùng** ở mốc 60.",
        "**Trục đứng (thang log):** tỉ lệ gói tin. 10⁻¹ = 10 %, 10⁻² = 1 %, 10⁻³ = 0,1 %.",
        "**Ba đường màu** = ba lần chạy (xám: thủ công v1, xanh dương: cử chỉ v1, xanh lá: hai tay v2).",
        "**Đỉnh nhọn ở khoảng 6–8 ms**, cao gần 10⁰ (≈ 40–60 % số gói): phần lớn gói tin về rất nhanh.",
        "**Đuôi** đi xuống dần sang phải: ở 30 ms chỉ còn khoảng 0,5 % số gói; ở 50 ms khoảng 0,1–0,3 %.",
        "**Cột ở 60 ms** nhô lên một chút: đó là các gói chậm hơn 60 ms được gom lại (khoảng 0,2 %).",
        "Đường **xanh lá (v2) nằm thấp nhất ở phần đuôi**, tức là ít gói chậm nhất, dù gói tệ nhất 909 ms lại thuộc lần chạy này.",
    ])
    b.p("**Rút ra:** mạng Wi-Fi riêng của robot **rất nhanh** (vài ms) và hiếm khi chậm. **Mạng không phải điểm nghẽn.** "
        "Lưu ý: RTT chỉ đo phần mạng, chưa tính thời gian camera, AI và bộ lọc cử chỉ.")
    b.h3("Hình 4b – Lệnh so với vận tốc tính từ encoder")
    b.nsteps([
        "**Trục ngang:** 6 chuyển động cơ bản (tới, lùi, trái, phải, xoay trái, xoay phải).",
        "**Trục đứng:** độ lớn vận tốc, đơn vị chuẩn hóa (1,0 = tối đa).",
        "Mỗi nhóm có **cột xanh dương = lệnh** và **cột xanh lá = robot thực sự đi** (tính từ encoder bằng công thức 2).",
        "Hai cột gần như cao bằng nhau. Riêng hai cột xoay thì cột xanh lá **cao hơn một chút** (xoay nhanh hơn lệnh khoảng 2,5 %).",
    ])
    b.p("**Rút ra:** robot đi đúng lệnh. Lưu ý: số liệu tính từ **encoder bánh**, nên nếu bánh trượt trên sàn thì không "
        "thấy được. Đây **không phải** sai số vị trí thật đo bằng camera ngoài.")
    b.h3("Bảng 3 – số chi tiết cho Hình 4b")
    b.table(["Chuyển động", "Lệnh (vₓ, v_y, ω)", "Từ encoder", "Sai số trục chính", "Trục khác lớn nhất"], [
        ["Tới", "(+0,472; 0; 0)", "(+0,474; +0,001; +0,002)", "+0,6 %", "0,002"],
        ["Lùi", "(−0,510; 0; 0)", "(−0,510; −0,001; −0,001)", "−0,1 %", "0,001"],
        ["Trái", "(0; +0,480; 0)", "(+0,004; +0,482; +0,002)", "+0,4 %", "0,004"],
        ["Phải", "(0; −0,480; 0)", "(−0,003; −0,479; 0)", "−0,2 %", "0,003"],
        ["Xoay trái", "(0; 0; +0,435)", "(+0,003; +0,001; +0,446)", "+2,5 %", "0,003"],
        ["Xoay phải", "(0; 0; −0,442)", "(−0,001; 0; −0,453)", "+2,4 %", "0,001"],
    ], widths=[2.4, 3.6, 4.6, 3, 3])
    b.p("**Cách đọc một dòng:** “Tới” được lệnh vₓ = 0,472. Encoder cho thấy robot đi 0,474, lệch +0,6 %. Robot bị trôi "
        "sang ngang (v_y) và bị xoay (ω) chỉ 0,001–0,002, gần như bằng 0. Nghĩa là **đi thẳng, không lệch, không tự xoay**. "
        "Hai dòng đi chéo (v2) không tính sai số trục chính vì không có một trục chính duy nhất.")
    b.p("**Độ trễ phản ứng:** từ lúc ghi nhận cử chỉ đến khi bánh chịu tải nhiều nhất đạt 50 % tốc độ mới mất **khoảng "
        "257–260 ms** (trung vị). Phần lớn thời gian này là do **cố ý giới hạn gia tốc**. Con số này chưa tính 4 khung "
        "(≈133 ms) cần để xác nhận cử chỉ.")

    b.h2("Mục 4.4 (IV-D). Bám tốc độ bánh — Hình 5")
    b.fig("fig_wheel_vi.png", "Hình 5 trong bài – điều khiển tốc độ bánh ở lần chạy hai tay.")
    b.h3("Hình 5a, 5b – tốc độ theo thời gian của bánh FL và FR")
    b.nsteps([
        "**Trục ngang:** thời gian 0–50 giây. **Trục đứng:** tốc độ bánh (1,0 = 4300 xung/s = tối đa; số âm = quay ngược).",
        "**Đường đen đứt** = giá trị đặt (bộ điều khiển muốn). **Đường màu liền** = giá trị đo (thực tế).",
        "Hai đường **gần như trùng khít** trong suốt 50 s, cả khi đổi chiều từ +1 xuống −1 (khoảng giây 17–27).",
        "Ở mỗi lần đổi lệnh, đường màu **trễ một chút** sau đường đứt và có vài gợn nhỏ. Đó là quán tính của động cơ.",
        "Khoảng giây 28–35 có vài **gai đứt ngắn** mà đường màu không theo kịp hết: lệnh quá ngắn, bánh chưa kịp tăng tốc.",
    ])
    b.h3("Hình 5c – đường feedforward của 4 bánh")
    b.nsteps([
        "**Trục ngang:** tốc độ muốn đạt |r|. **Trục đứng:** PWM cần cấp (0–1).",
        "**Chỗ đường cắt trục đứng** (|r| = 0) = **a** = PWM tối thiểu để bánh bắt đầu quay. Đường đỏ (FR) cắt ở 0,148; ba đường còn lại cắt ở khoảng 0,06–0,08.",
        "**Độ dốc:** đường đỏ dốc nhất. Ở tốc độ tối đa, FR cần khoảng 0,74 PWM, trong khi các bánh khác chỉ cần khoảng 0,51–0,55.",
    ])
    b.p("**Rút ra:** bánh FR khó quay hơn hẳn: ma sát lớn hơn hoặc động cơ yếu hơn. Nếu dùng chung một đường cho cả 4 bánh, FR "
        "sẽ luôn chậm hơn và robot sẽ đi lệch. Mỗi bánh cần đường riêng.")
    b.h3("Hình 5d – box plot sai số bám")
    b.nsteps([
        "**Trục đứng:** |sai số| tính theo phần của tốc độ tối đa. 0,02 = 2 %. Chỉ tính khi lệnh đã ổn định ít nhất 0,3 s.",
        "**Vạch đen trong hộp** (trung vị) khoảng 0,017–0,019, tức là một nửa thời gian sai số dưới khoảng 1,8 %.",
        "**Hình thoi** (trung bình) khoảng 0,023–0,026, nằm cao hơn trung vị: có một số lúc sai số lớn kéo trung bình lên.",
        "**Nắp hộp** khoảng 0,03–0,037: 75 % thời gian sai số dưới khoảng 3–3,7 %.",
        "**Râu trên** (P95) khoảng 0,061–0,074, **vượt đường đỏ 5 %**: 5 % thời gian xấu nhất có sai số 6–7,4 %.",
        "Hộp FR cao nhất một chút, đúng với việc FR là bánh khó điều khiển nhất.",
    ])
    b.h3("Rút ra điều gì?")
    b.p("Sai số **trung bình đạt mục tiêu < 5 %**, nhưng **phần đuôi (P95) thì không** ở lần chạy v2. Bài báo cũng thừa nhận "
        "chưa so sánh với PID thường hay điều khiển vòng hở, nên **chưa chứng minh được bộ điều khiển này tốt hơn** các cách đó.")

    b.h2("Mục 4.5 (IV-E). Phiên thứ hai: có tay thật, độ trễ đầu-cuối, con trỏ ở mép — Bảng 4 và Hình 6")
    b.p("Sau các lần chạy trên, có thêm **4 phiên A, B, C, D**, mỗi khung camera được ghi một dòng log. A, B dùng camera "
        "640×480 và con trỏ đi 1:1 theo ngón tay. C, D dùng 1280×720 và con trỏ được “kéo giãn” ở mép (C: kiểu gấp khúc, "
        "D: kiểu mượt). A, B có kết nối robot; C, D chỉ thử con trỏ.")
    b.table(["Phiên", "Camera", "Con trỏ", "Thời gian (s)", "fps", "AI 0 tay (ms)", "AI 1 tay", "AI 2 tay"], [
        ["A", "640×480", "1:1", "186", "25,5", "27,7", "45,5", "43,3"],
        ["B", "640×480", "1:1", "76", "21,9", "31,3", "50,1", "47,5"],
        ["C", "1280×720", "gấp khúc", "363", "18,0", "30,7", "55,5", "48,3"],
        ["D", "1280×720", "mượt", "214", "21,9", "28,9", "52,4", "47,2"],
    ], widths=[1.3, 2.2, 2, 2, 1.4, 2.6, 2.4, 2.4])
    b.p("**Cách đọc:** so sánh theo cột. Không có tay thì AI mất khoảng 28–31 ms; **có tay thì 43–56 ms**, gần gấp đôi. "
        "fps cả phiên chỉ 18–25,5, thấp hơn 29,9 fps ở mục 4.2, vì server còn phải mã hóa và truyền ảnh lên web. Bốn phiên "
        "khác nhau về thao tác và thời gian, nên **không phải so sánh có kiểm soát**.")
    b.fig("fig_sess2_vi.png", "Hình 6 trong bài – (a) thời gian AI theo phiên và số tay; (b) độ trễ đầu-cuối phiên A.")
    b.h3("Hình 6a – box plot thời gian suy luận AI")
    b.nsteps([
        "**Trục ngang:** 4 phiên, mỗi phiên có **3 hộp**: xanh dương = không tay, cam = 1 tay, xanh lá = 2 tay.",
        "**Trục đứng:** thời gian AI xử lý một khung (ms). Vạch cam trong hộp là trung vị.",
        "Ở **cả 4 phiên**, hộp xanh dương thấp nhất (khoảng 27–29 ms), hộp cam cao nhất.",
        "**Điều bất ngờ:** 1 tay (cam) **chậm hơn** 2 tay (xanh lá). Bài đoán lý do là AI cứ tiếp tục đi tìm bàn tay thứ hai, nhưng chưa kiểm chứng.",
        "Phiên C có hộp cam **cao và rộng nhất** (râu lên tới khoảng 88 ms): biến động lớn.",
        "Tăng độ phân giải lên 1280×720 (C, D) **không làm thay đổi** thời gian khi không có tay, vì AI vẫn chạy trên ảnh thu nhỏ rộng 640 px.",
    ])
    b.h3("Hình 6b – histogram độ trễ đầu-cuối (phiên A)")
    b.nsteps([
        "**Trục ngang:** thời gian từ **khung camera xác nhận cử chỉ** đến khi **bánh đạt 50 % tốc độ mới** (ms).",
        "**Trục đứng:** số lần cử chỉ rơi vào mỗi ô. Tổng cộng 15 lần.",
        "**Đường đỏ đứt** = trung vị **427 ms**. Ô cao nhất (5 lần) nằm ngay ở khoảng 425–440 ms.",
        "Các giá trị trải từ khoảng 320 đến 496 ms.",
    ])
    b.p("**Rút ra:** từ lúc ra cử chỉ đến khi robot chạy rõ mất khoảng **0,4–0,5 giây**. Trong đó: lệnh rời laptop sau "
        "khoảng 37 ms; **khoảng 0,2 s là do cố ý tăng tốc từ từ** (giới hạn gia tốc 2,0/s, mục tiêu trung bình 0,81 tốc độ tối đa); "
        "chưa tính thêm khoảng 120–140 ms để bộ lọc đủ 4 khung. Con số này lớn hơn 257–260 ms ở mục 4.3 vì mốc bắt đầu tính "
        "sớm hơn (khung camera thay vì dòng log) và độ lớn tốc độ mục tiêu khác nhau. **Mạng thì nhanh, phần chậm là camera + AI + bộ lọc + tăng tốc.**")
    b.h3("Hai ý còn lại của mục 4.5")
    b.bullets([
        "**Bám bánh:** sai số trung bình 0,9–1,5 %. Ở phiên A, PWM chạm trần 0,95 trong 4–8 % số mẫu: ở tốc độ cao, pin "
        "12 V không còn đủ điện áp dư, nên bánh không đạt được tốc độ đặt.",
        "**Con trỏ ở mép:** với cách kéo giãn (C, D), con trỏ tới được mép màn hình nhiều hơn (8,2 % và 4,6 % số khung, so với "
        "2,3 % và 1,4 %). Nhưng ở C, D người điều khiển cũng **cố tình** đưa con trỏ ra góc, nên các số này chỉ chứng minh con "
        "trỏ **tới được mép**, chưa chứng minh giảm mất tay.",
    ])

    b.h2("Mục 5 và 6 (V và VI). Hạn chế và Kết luận")
    b.p("**Hạn chế** (bài tự nêu): chỉ 1 robot, 1 mặt sàn, 1 người; chưa khảo sát người dùng; đo con trỏ trên tay thật chỉ "
        "có 12 lần bấm; chưa so sánh bộ điều khiển với phương án cơ sở; độ trễ đầu-cuối chỉ có 15 lần; **không có cảm biến vật "
        "cản**, người điều khiển là lớp an toàn duy nhất.")
    b.p("**Kết luận:** một webcam + một ESP32 là đủ để vừa lái robot omni vừa dùng dashboard bằng hai tay. Mạng chỉ mất vài ms, "
        "bánh bám tốc độ tốt, robot đi đúng hướng. **Phần cần cải thiện là độ trễ tương tác (khoảng 427 ms)**, không phải mạng. "
        "Việc tiếp theo: khảo sát người dùng, so sánh với bộ điều khiển cơ sở, thêm cảm biến hướng và cảm biến vật cản.")

    # ---------------- Part 4
    b.pagebreak()
    b.h1("Phần 4. Ghi nhớ nhanh và tự kiểm tra")
    b.h2("10 con số quan trọng nhất")
    b.table(["#", "Con số", "Ở đâu", "Nói gì"], [
        ["1", "13.080 chu kỳ, 2026 s", "Bảng 2", "Lượng dữ liệu thật dùng để đánh giá"],
        ["2", "29,9 fps; 18,5 ms", "4.2", "Camera + AI khi không có tay"],
        ["3", "18–25,5 fps; 45–56 ms", "Bảng 4, Hình 6a", "Khi có tay thật, chạy cả hệ thống"],
        ["4", "RTT 6,6–8,1 ms (trung vị)", "Bảng 2, Hình 4a", "Mạng rất nhanh"],
        ["5", "909 ms (max)", "Bảng 2", "Một lần mất kết nối, watchdog đã dừng robot"],
        ["6", "1,5–3,2 % (trung bình)", "Bảng 1, Hình 5d", "Sai số tốc độ bánh"],
        ["7", "P95 6,1–7,4 % (v2)", "Hình 5d", "Phần đuôi vượt mốc 5 %"],
        ["8", "≤ 0,6 % tịnh tiến; 2,5 % xoay", "Bảng 3, Hình 4b", "Robot đi đúng lệnh"],
        ["9", "427 ms", "Hình 6b", "Trễ đầu-cuối, phần cần cải thiện"],
        ["10", "−5 % rung; 11/12 lần bấm tệ hơn", "Hình 3", "Kết quả âm về con trỏ"],
    ], widths=[0.8, 4.6, 3.6, 7.6])
    b.h2("Câu hỏi tự kiểm tra (có thể bị hỏi khi bảo vệ)")
    qa = [
        ("Vì sao báo trung vị RTT mà không báo trung bình?",
         "Vì có vài giá trị rất lớn (909 ms) kéo trung bình lên. Trung vị cho biết trường hợp điển hình, còn P95/max cho biết trường hợp xấu."),
        ("Trong Hình 3, chấm nằm trên đường y = x nghĩa là gì?",
         "Điểm bấm có neo dịch nhiều hơn đầu ngón thô, tức là neo làm tệ hơn. 11/12 chấm như vậy."),
        ("Vì sao FR cần PWM cao nhất?",
         "Vùng chết lớn nhất (a = 0,148) và độ dốc lớn nhất (b = 0,594), nhìn thấy ở đường đỏ trong Hình 5c."),
        ("Sai số bánh có đạt mục tiêu 5 % không?",
         "Trung bình thì đạt (1,5–3,2 %). P95 ở lần chạy v2 thì không (6,1–7,4 %), như râu vượt đường đỏ trong Hình 5d."),
        ("Bảng 3 có phải là sai số vị trí thật của robot không?",
         "Không. Nó tính từ encoder bánh, nên không thấy trượt bánh. Muốn có sai số thật cần camera ngoài hoặc cảm biến khác."),
        ("Vì sao độ trễ 427 ms lớn hơn 257–260 ms?",
         "Mốc bắt đầu khác nhau (khung camera sớm hơn dòng log khoảng 37 ms), độ lớn mục tiêu khác nhau, và phần lớn là do cố ý giới hạn gia tốc."),
        ("Điểm yếu lớn nhất của bài?",
         "1 robot, 1 người, chưa khảo sát người dùng, chưa so sánh bộ điều khiển với phương án cơ sở, không có cảm biến vật cản."),
    ]
    for q, a in qa:
        par = b.d.add_paragraph()
        add_rich(par, f"**Hỏi:** {q}")
        par.paragraph_format.space_after = Pt(0)
        par = b.d.add_paragraph()
        par.paragraph_format.left_indent = Cm(0.6)
        add_rich(par, f"**Đáp:** {a}")
    b.save(OUT / "Giai_thich_paper_VI.docx")


# ---------------------------------------------------------------------------
def build_en():
    b = Builder()
    b.title("Reading the Research Paper: A Simple Guide",
            "Plain-English guide to “A Vision-Based Dual-Mode Hand Gesture Interface … Four-Wheel "
            "Omnidirectional Mobile Robot” (reports/research_paper/paper_en.pdf, Elsevier journal layout). "
            "The Vietnamese paper has the same content, figures and numbers, but uses the IEEE layout, "
            "so its sections are numbered I, II-A… and its tables I–IV.")

    b.box("How to use this guide", [
        "Open the paper (PDF) next to this guide. Read in this order: **Part 1** (what the paper says) → "
        "**Part 2** (how to read charts, used for every figure) → **Part 3** (each section and figure of the paper) → "
        "**Part 4** (key numbers and self-test questions).",
        "Every figure is explained in 3 steps: **What is it?** → **Read it step by step** → **What does it tell us?**",
    ])

    b.h1("Part 1. What is the paper about? (2-minute read)")
    b.p("**The problem.** When people control a robot with hand gestures, the hand usually only gives move commands "
        "(go, back, turn). To change mode, set speed or press emergency stop, the user still needs a mouse or keyboard.")
    b.p("**The idea.** Use **one laptop webcam** for both jobs at the same time:")
    b.bullets([
        "The **main hand** (right hand) moves a **virtual mouse cursor** on a web dashboard: it clicks buttons and drags sliders.",
        "The **other hand** (left hand) **drives the robot**: point in 8 directions, two fingers to turn, fist to stop.",
    ])
    b.p("The robot has **4 omni wheels in an X shape**, so it can move in any direction (forward, sideways, diagonal) and "
        "turn in place. The laptop sends commands over Wi-Fi to an **ESP32** on the robot. The ESP32 controls each wheel's "
        "speed 100 times per second.")
    b.p("**Three main contributions** (Section 1):")
    b.nsteps([
        "A two-hand interface, with a part that **fixes the left/right hand label by itself** (the camera image is mirrored).",
        "A **laptop ↔ ESP32 link over UDP** on the robot's own Wi-Fi, with a one-driver lock, safety timers on both sides "
        "(no signal → stop) and acceleration limits.",
        "A speed controller for each wheel: **feed-forward + PI**, with protection against integrator wind-up. Its settings "
        "were measured on the real motors.",
    ])
    b.p("**Main results** (from 13,080 logged control cycles, about 34 minutes of real driving):")
    b.table(["Quantity", "Result", "In simple words"], [
        ["Camera + AI speed (no hand)", "29.9 frames/s; AI 18.5 ms/frame", "Almost the full 30 fps of the camera"],
        ["With real hands (session 2)", "18–25.5 fps; AI 45–56 ms", "AI is clearly slower when a hand is seen"],
        ["Network round trip (UDP)", "median 6.6–8.1 ms", "Network is very fast, not the bottleneck"],
        ["Wheel speed error", "mean 1.5–3.2 % of top speed", "Wheels spin at almost the commanded speed"],
        ["Robot body motion (from encoders)", "0.1–2.5 % off the command", "Robot goes where it is told"],
        ["Camera frame → wheel at 50 % speed", "427 ms (median of 15)", "This is the slowest part"],
        ["Cursor filter and “click anchor” on a real hand", "almost no benefit", "Negative result, reported honestly"],
    ], widths=[5.6, 5.2, 5.8])
    b.box("Key point", "The paper shows that **the robot and network work well** (strong data). The **cursor on a real "
          "hand** is not as good as the simulation said, and the paper says so openly. Everything comes from **one robot "
          "and one user**, with **no user study**.")

    b.pagebreak()
    b.h1("Part 2. Basic skills: how to read charts and statistics")
    b.p("The paper uses a few ideas and chart types again and again. Learn them first, and every figure becomes easy.")
    b.h2("2.1. General rules for any chart")
    b.nsteps([
        "**Read the title and caption** under the figure: what is being compared?",
        "**Read the horizontal axis (x)** and **vertical axis (y)**: what quantity, and what **unit** (ms, px, %, s)?",
        "**Read the legend**: what does each color or line style mean?",
        "**Find the reference line** (dashed line, y = x line, 5 % mark…). It is the “good / bad” border.",
        "Only then look at the data: high or low, same or different, close together or spread out?",
    ])
    b.h2("2.2. Common statistics words")
    b.table(["Word", "Meaning", "Example in the paper"], [
        ["**Mean (average)**", "Add all values and divide by how many. A few very big values can pull it up.", "Mean wheel error 2.5 %"],
        ["**Median**", "Sort the values and take the **middle** one. Half are smaller, half are bigger. "
         "A few strange values do not change it much.", "Median RTT 6.6 ms"],
        ["**95th percentile (P95)**", "95 % of values are below this. It shows the “bad but still common” case.", "RTT P95 = 16.1 ms"],
        ["**Maximum (max)**", "The single worst value seen.", "RTT max = 909 ms"],
        ["**Normalized units**", "Scaled to 0 → 1. For wheel speed, **1.0 = 4300 encoder counts per second** = top speed.",
         "Forward command 0.472 = 47 % of top speed"],
        ["**% of full scale**", "Error divided by top speed (not by the current speed).", "Error 0.025 = 2.5 %"],
        ["**ms, px, fps**", "milliseconds (1/1000 s); pixels; frames per second.", "30 fps → 33 ms per frame"],
    ], widths=[3.8, 7.7, 5.1])
    b.box("Why does the paper use the median and not the mean?",
          "Network delay is sometimes huge (909 ms), but only once. That one value would pull the mean up and make the "
          "network look slow. The **median** shows the **typical case**; **P95 and max** show the **bad cases**. The paper "
          "always gives all three: median / P95 / max.")
    b.h2("2.3. The chart types in the paper")
    b.h3("a) Block diagram (Figure 1)")
    b.p("No axes and no measured numbers. Each box is a part of the system; each arrow shows data moving from one part to another.")
    b.h3("b) Time plot (Figure 5a, 5b)")
    b.p("The x axis is time. There are usually **2 lines**: the **set-point** (what we want, dashed) and the **measured** "
        "value (what really happens, solid). **The closer the two lines, the better the controller.**")
    b.h3("c) Histogram (Figure 4a, 6b)")
    b.p("The x axis is cut into **bins**, for example 0–2 ms, 2–4 ms… The height of each bar = **how many samples fall "
        "in that bin** (or what share). The tallest bar is the most common value. The long “tail” on the right shows rare, slow cases.")
    b.p("**Log scale** (Figure 4a): on the y axis, each big step is **10 times** the one below: 10⁻³ = 0.1 %, 10⁻² = 1 %, "
        "10⁻¹ = 10 %. It lets us see a very tall bar (60 %) and a very small one (0.1 %) in the same picture.")
    b.h3("d) Box plot (Figure 5d, 6a)")
    b.p("One box sums up a whole group of numbers:")
    b.bullets([
        "**Line inside the box** = median.",
        "**Bottom and top of the box** = 25th and 75th percentile. Half of all samples are inside the box. A taller box means more spread.",
        "**Whiskers** (the lines above and below) = the range where most samples are. In Figure 5d they go from P5 to P95.",
        "**Diamond** (Figure 5d) = mean.",
    ])
    b.h3("e) Scatter plot with a y = x line (Figure 3)")
    b.p("Each dot is one trial. The diagonal **y = x** line is where both values are equal. A dot **above** the line → "
        "the y value is bigger; a dot **below** → the y value is smaller.")
    b.h3("f) Paired bar chart (Figure 4b)")
    b.p("Each group has 2 bars side by side: **command** and **measured result**. Equal height is good.")
    b.h3("g) Straight line y = a + b·x (Figure 5c)")
    b.p("**a** = where the line meets the vertical axis (the value at x = 0). **b** = the slope (how much y grows when x grows by 1).")

    b.pagebreak()
    b.h1("Part 3. The paper, section by section and figure by figure")
    b.h2("Abstract and keywords")
    b.p("The abstract puts the whole paper into one paragraph: problem → solution → result numbers → limits. The numbers "
        "are the same as in the table in Part 1. The last sentence, “All results come from one robot and one operator, and "
        "no user study was performed”, is an **honest statement of limits**: the reader knows right away how far to trust the results.")

    b.h2("Section 1. Introduction")
    b.bullets([
        "An **omni robot** has 3 independent motions: **vₓ** (forward/back), **v_y** (left/right), **ω** (turn). "
        "Controlling all three at once is harder than driving a normal car.",
        "**MediaPipe Hands** is an AI model that finds **21 landmarks** on a hand (finger joints, fingertips, wrist).",
        "Hardware problem: cheap L298N drivers and motors have a **dead zone**: a wheel does not move until the PWM is high "
        "enough. This threshold differs between wheels by **2.7 times** (5.5 % to 14.8 % PWM). With the same PWM on all "
        "4 wheels, the robot drifts and turns by itself.",
    ])

    b.h2("Section 2.1. Host–edge architecture — Figure 1")
    b.fig("fig_arch_en.png", "Figure 1 in the paper – system architecture.")
    b.h3("What is it?")
    b.p("A block diagram of the whole system. **Left box (HOST)** = laptop. **Right box (EDGE)** = ESP32 on the robot.")
    b.h3("Read it step by step")
    b.nsteps([
        "**Laptop side, top to bottom:** Camera (MJPG 1280×720, 30 fps, mirrored image, 2 buffers) → MediaPipe finds 21 landmarks for up to "
        "2 hands on a **smaller 640-px-wide copy** (sharp image for the screen, small image so the AI runs fast) → **RoleAssigner** decides which hand is the UI hand and which is the drive hand.",
        "It splits into two branches. **Yellow box** = main hand controls the GUI (One-Euro filter, click anchor FREEZE_BACK 0.2 s). "
        "**Green box** = other hand drives the robot (8 directions; GestureFilter 4/6 means 4 frames in a row to start, 6 to stop).",
        "UI hand → **Web dashboard** (FastAPI + WebSocket). Drive hand → **control_loop at 20 Hz** (sends a command 20 times "
        "per second, speeds up at most 2.0/s, slows down 4.0/s, writes a CSV log).",
        "**Solid red arrow** at the top: the UDP command “C seq vx vy w” goes to the robot 20 times per second.",
        "**Robot side, top to bottom:** its own Wi-Fi “omni-robot”, UDP port 4210, 300 ms watchdog (no command for 300 ms "
        "→ stop), commands accepted from one laptop only → **inverse kinematics** (turns vₓ, v_y, ω into 4 wheel speeds) → "
        "**4 speed controllers at 100 Hz** → L298N drivers power the motors; **encoders** count pulses to measure the real "
        "speed and send it back up to the controller (upward arrow).",
        "**Dashed green arrow** at the bottom: the robot replies “A seq” + 12 values (for each wheel: target speed, measured speed, PWM).",
    ])
    b.h3("What does it tell us?")
    b.p("The laptop does the **heavy** work (AI, interface). The ESP32 does the **fast and safe** work (wheel control at "
        "100 Hz, stop by itself if the network is lost). There are **2 safety layers**: the ESP32 stops after 300 ms with no "
        "command, and the laptop replaces any command older than 0.4 s with zero.")

    b.h2("Section 2.2. Kinematic model — Figure 2 and equations (1), (2)")
    b.fig("fig_kin_en.png", "Figure 2 in the paper – X-configuration geometry.", width=9)
    b.h3("What is it?")
    b.p("The robot **seen from above**. The square is the body. The 4 black bars at 45° are the wheels: "
        "**FL** (front-left), **FR** (front-right), **RL** (rear-left), **RR** (rear-right).")
    b.h3("Read it step by step")
    b.nsteps([
        "**X_R axis** points up = robot's **front**. **Y_R axis** points left = robot's **left**. The curved arrow: "
        "**ω > 0 means turning counter-clockwise** (CCW). This is the standard ROS rule.",
        "**The colored arrow on each wheel** = the direction that wheel **pushes** the robot when it spins forward. The wheels sit at 45°, so each one pushes diagonally.",
        "Example **go straight forward**: all 4 wheels spin forward. The sideways parts cancel out; only forward push remains.",
        "Example **go sideways to the left**: FL and RR spin backward, FR and RL spin forward (the v_y column in the matrix: −1, +1, +1, −1). "
        "The forward/back parts cancel; only a push to the left remains.",
    ])
    b.h3("What the equations say (in words)")
    b.bullets([
        "**(1) Inverse kinematics:** multiply the command (vₓ, v_y, ω) by a 4×3 matrix to get the 4 wheel speeds. If any "
        "wheel would go above 1.0, **all 4 wheels are divided by the same number**. The robot keeps the **same direction** "
        "and just goes slower. (Cutting each wheel on its own would bend the path.)",
        "**(2) Forward kinematics:** the reverse. From the **measured** wheel speeds, work out how the robot is really moving. "
        "The matrix is simple: the transpose divided by 4. This gives **Table 3** and **Figure 4b**.",
        "Encoder: **8112 counts per wheel turn**. The ESP32's PCNT hardware counts the pulses, with a 12.5 µs noise filter.",
    ])

    b.h2("Section 3. Gesture interface and wheel control")
    b.h3("3.1. Which finger is straight — equation (3)")
    b.p("A finger counts as **straight** if the distance **wrist → fingertip** is more than 1.15 times the distance "
        "**wrist → middle finger joint**. Because it is a **ratio**, it works whether the hand is near or far from the camera. "
        "Only the index finger straight → measure the pointing angle and round it to **8 directions, 45° each**. Index + "
        "middle finger pointing left/right → turn. Fist or open palm → stop.")
    b.h3("3.2. Hand roles")
    b.p("The image is mirrored, so MediaPipe calls the left hand “right”. The role assigner works like this. With 2 hands, "
        "it uses the **left/right position of the wrists in the image**, and learns by itself whether the labels are flipped "
        "(a trust score cₖ; it switches when cₖ < −0.6). With 1 hand, it takes a **vote over 10 frames**. If one hand just "
        "disappeared and the other moved less than 150 px, the old role is kept.")
    b.h3("3.3. Cursor, click anchor, slider grab, frame edge")
    b.bullets([
        "**One-Euro filter:** hand still → strong smoothing (less shaking); hand moving fast → light smoothing (no lag).",
        "**UI hand poses:** index only = move the cursor (hold still 0.8 s = click); index + middle = click or drag.",
        "**Click anchor (equation 4):** raising the middle finger may pull the index fingertip away. So the system uses the "
        "position from **0.2 s earlier** as the click point. (On a real hand this **did not help**; see Figure 3.)",
        "**Mapping near the frame edge:** when the hand is close to the image border, the AI loses it. So in the middle the "
        "cursor follows the finger exactly, and near the edge the cursor moves **faster than the finger** (up to 1.35×). "
        "It reaches the screen edge while the finger is still 6 % away from the image border. A first version jumped to "
        "1.67× suddenly and made the cursor “run ahead”, so it was replaced.",
    ])
    b.h3("3.4. Speed control for each wheel — equation (5) and Table 1")
    b.p("Every 10 ms, each wheel's PWM is the **sum of 3 parts**:")
    b.bullets([
        "**Feed-forward** uᶠᶠ = a + b·|r|: a “first guess” of the PWM needed for speed r. **a** = the smallest PWM that "
        "starts the wheel (dead zone); **b** = extra PWM for each unit of speed.",
        "**P** = Kp × error (Kp = 0.8): corrects the error right now.",
        "**I** = sum of past errors (Ki = 6.0): removes small errors that last. **Anti-windup:** it stops summing while the "
        "robot is speeding up or the PWM is at its limit, so the wheel does not overshoot.",
    ])
    b.p("**Table 1** gives a and b for each wheel (measured with the wheels lifted off the floor) and the mean error on the floor:")
    b.table(["Wheel", "a (start PWM)", "b (slope)", "Error v1 gesture", "Error v2 two-hand"], [
        ["FL front-left", "0.076", "0.470", "1.9 %", "2.5 %"],
        ["**FR front-right**", "**0.148**", "**0.594**", "2.5 %", "2.6 %"],
        ["RL rear-left", "0.055", "0.453", "1.6 %", "2.3 %"],
        ["RR rear-right", "0.060", "0.464", "1.7 %", "2.5 %"],
    ], widths=[3.2, 3.4, 2.6, 3.6, 3.6])
    b.p("**How to read it:** FR is the “stiffest” wheel. It needs 14.8 % PWM just to start, 2.7 times more than RL (5.5 %). "
        "Because each wheel has its own a and b, the errors stay similar (about 2–2.6 %) even though the wheels are different.")

    b.h2("Section 4.1. Experimental setup — Table 2")
    b.table(["Run", "Log rows", "Time (s)", "RTT: median / P95 / max (ms)"], [
        ["Manual (v1)", "3240", "1512", "7.8 / 22.5 / 97"],
        ["Gesture (v1)", "4820", "247", "8.1 / 26.1 / 101"],
        ["Two-hand (v2)", "5020", "266", "6.6 / 16.1 / **909**"],
        ["Total", "13080", "2026", "–"],
    ], widths=[3.6, 3, 3, 7])
    b.p("**How to read it:** 3 real runs on the floor, logged 20 rows per second. **RTT** (round-trip time) = time from the "
        "laptop sending a command to getting the robot's reply. Read the columns: the median is only about 7–8 ms (very fast); "
        "95 % of packets are under 16–26 ms; but there is **one worst case of 909 ms** in the v2 run. That is longer than the "
        "300 ms watchdog, so the robot stopped by itself at that moment. The safety system worked.")
    b.p("The manual run is much longer (1512 s) but has fewer rows, because the log is written mostly while driving.")

    b.h2("Section 4.2. Vision and the cursor negative result — Figure 3")
    b.p("**Speed:** over 359 frames in a row with no hand: **29.9 fps**, AI takes **18.5 ms** per frame on average (P95 = 27.1 ms). "
        "With only 1 driver buffer instead of 2, the speed fell from 28.9 to 14.5 fps.")
    b.p("**Tests:** 55 automatic checks with simulated hands + 49 cursor checks in a browser. All passed.")
    b.p("**Gesture stability:** about 94 % of gesture segments lasted more than 0.3 s. Only about 6 % were very short "
        "(maybe wrong detections, but this was not checked).")
    b.p("**Negative result:** on a **simulated** hand, the filter cut shaking by 65.5 % and the anchor cut the click shift by "
        "83.6 %. On a **real** hand that did not happen:")
    b.bullets([
        "Shaking: hand still for 8 s, raw fingertip moved 2.26 px, filtered cursor 2.14 px, **only 5 % less**.",
        "Clicking: the fingertip moved only **1.65 px** when raising the middle finger (the simulation assumed 29.2 px). So there was almost nothing to fix.",
    ])
    b.fig("fig_real_en.png", "Figure 3 in the paper – real hand, 12 clicks.", width=9.5)
    b.h3("What is it?")
    b.p("A scatter plot. Each green dot is **one click trial** (12 in total).")
    b.h3("Read it step by step")
    b.nsteps([
        "**Horizontal axis:** how many pixels the index fingertip moved when the middle finger went up (without the anchor, the click point would move this much).",
        "**Vertical axis:** how many pixels the real click point (with the anchor) moved.",
        "**Dashed line y = x:** both values equal. Dot **below** → the anchor **helped**. Dot **above** → the anchor **made it worse**.",
        "Count: **11 of 12 dots are above the line**. Only 1 dot (x ≈ 3.5, y ≈ 2.7) is below.",
        "Look at the size: all values are just a few pixels (1–12 px). The dwell-click circle is 30 px, so the real effect on clicking is probably small.",
    ])
    b.h3("What does it tell us?")
    b.p("On a real hand, the anchor **does not help; it adds about 2.5 px of shift**. Looking 0.2 s back picks a moment when "
        "the finger was still drifting a little. The paper calls this a **negative result**. That is honest and good science, "
        "but with only 12 clicks from 1 person it is only an early sign.")

    b.h2("Section 4.3. Link latency — Figure 4")
    b.fig("fig_rtt_odo_en.png", "Figure 4 in the paper – (a) RTT distribution; (b) command vs. encoder-based velocity.")
    b.h3("Figure 4a – histogram of UDP round-trip time")
    b.nsteps([
        "**Horizontal axis:** RTT in ms, from 0 to 60. Every packet slower than 60 ms is put in the **last bar** at 60.",
        "**Vertical axis (log scale):** share of packets. 10⁻¹ = 10 %, 10⁻² = 1 %, 10⁻³ = 0.1 %.",
        "**Three colored lines** = three runs (grey: manual v1; blue: gesture v1; green: two-hand v2).",
        "**Sharp peak at about 6–8 ms**, close to 10⁰ (≈ 40–60 % of packets): most packets come back very fast.",
        "**The tail** goes down to the right: at 30 ms only about 0.5 % of packets; at 50 ms about 0.1–0.3 %.",
        "**The bar at 60 ms** goes up a little: these are all the packets slower than 60 ms put together (about 0.2 %).",
        "The **green line (v2) is lowest in the tail**, so it had the fewest slow packets, even though the single worst packet (909 ms) was in this run.",
    ])
    b.p("**What it tells us:** the robot's own Wi-Fi is **very fast** (a few ms) and rarely slow. **The network is not the "
        "bottleneck.** Note: RTT is only the network part. It does not include camera, AI or gesture filtering time.")
    b.h3("Figure 4b – command vs. velocity from the encoders")
    b.nsteps([
        "**Horizontal axis:** 6 basic motions (forward, backward, left, right, rotate left, rotate right).",
        "**Vertical axis:** speed size in normalized units (1.0 = top speed).",
        "Each group has a **blue bar = command** and a **green bar = how the robot really moved** (from the encoders, equation 2).",
        "The two bars are almost the same height. Only for the two rotations is the green bar **a little taller** (turning about 2.5 % faster than commanded).",
    ])
    b.p("**What it tells us:** the robot does what it is told. Note: these numbers come from the **wheel encoders**, so wheel "
        "slip on the floor is not seen. This is **not** a true position error measured by an outside camera.")
    b.h3("Table 3 – detailed numbers for Figure 4b")
    b.table(["Motion", "Command (vₓ, v_y, ω)", "From encoders", "Main-axis error", "Max other axis"], [
        ["Forward", "(+0.472, 0, 0)", "(+0.474, +0.001, +0.002)", "+0.6 %", "0.002"],
        ["Backward", "(−0.510, 0, 0)", "(−0.510, −0.001, −0.001)", "−0.1 %", "0.001"],
        ["Left", "(0, +0.480, 0)", "(+0.004, +0.482, +0.002)", "+0.4 %", "0.004"],
        ["Right", "(0, −0.480, 0)", "(−0.003, −0.479, 0)", "−0.2 %", "0.003"],
        ["Rotate left", "(0, 0, +0.435)", "(+0.003, +0.001, +0.446)", "+2.5 %", "0.003"],
        ["Rotate right", "(0, 0, −0.442)", "(−0.001, 0, −0.453)", "+2.4 %", "0.001"],
    ], widths=[2.4, 3.6, 4.6, 3, 3])
    b.p("**How to read one row:** “Forward” was commanded vₓ = 0.472. The encoders show 0.474, so +0.6 % off. Sideways drift "
        "(v_y) and turning (ω) are only 0.001–0.002, almost zero. So the robot **goes straight, with no drift and no turning**. "
        "The two diagonal rows (v2) have no main-axis error because there is no single main axis.")
    b.p("**Reaction time:** from the logged gesture to the moment the most loaded wheel reaches 50 % of its new speed takes "
        "**about 257–260 ms** (median). Most of this time comes from the **deliberate acceleration limit**. It does not "
        "include the 4 frames (≈133 ms) needed to confirm the gesture.")

    b.h2("Section 4.4. Wheel tracking — Figure 5")
    b.fig("fig_wheel_en.png", "Figure 5 in the paper – wheel speed control in the two-hand run.")
    b.h3("Figure 5a, 5b – speed over time for wheels FL and FR")
    b.nsteps([
        "**Horizontal axis:** time, 0–50 seconds. **Vertical axis:** wheel speed (1.0 = 4300 counts/s = top speed; negative = spinning backward).",
        "**Black dashed line** = set-point (what the controller wants). **Colored solid line** = measured (what really happens).",
        "The two lines **almost cover each other** for the whole 50 s, even when going from +1 to −1 (around 17–27 s).",
        "At each change, the colored line comes **a little late** after the dashed line, with a few small wiggles. That is motor inertia.",
        "Around 28–35 s there are a few **short dashed spikes** that the colored line does not fully follow: the command was too short for the wheel to speed up.",
    ])
    b.h3("Figure 5c – feed-forward lines of the 4 wheels")
    b.nsteps([
        "**Horizontal axis:** wanted speed |r|. **Vertical axis:** PWM to apply (0–1).",
        "**Where a line meets the vertical axis** (|r| = 0) = **a** = smallest PWM that starts the wheel. Red (FR) meets it at 0.148; the other three at about 0.06–0.08.",
        "**Slope:** the red line is the steepest. At top speed FR needs about 0.74 PWM; the others need only about 0.51–0.55.",
    ])
    b.p("**What it tells us:** the FR wheel is much harder to turn (more friction or a weaker motor). With one shared line "
        "for all 4 wheels, FR would always be slower and the robot would drift. Each wheel needs its own line.")
    b.h3("Figure 5d – box plot of tracking error")
    b.nsteps([
        "**Vertical axis:** |error| as a share of top speed. 0.02 = 2 %. Only counted when the command has been steady for at least 0.3 s.",
        "**Black line in the box** (median) is about 0.017–0.019: half the time the error is under about 1.8 %.",
        "**Diamond** (mean) is about 0.023–0.026, above the median: a few large errors pull the mean up.",
        "**Top of the box** is about 0.03–0.037: 75 % of the time the error is under about 3–3.7 %.",
        "**Top whisker** (P95) is about 0.061–0.074, **above the red 5 % line**: in the worst 5 % of the time the error is 6–7.4 %.",
        "The FR box is a little taller. That matches FR being the hardest wheel to control.",
    ])
    b.h3("What does it tell us?")
    b.p("The **mean error meets the < 5 % goal**, but **the tail (P95) does not** in the v2 run. The paper also admits it did "
        "not compare against a plain PID or open-loop control, so it **has not proved that this controller is better** than those.")

    b.h2("Section 4.5. Second session: real hands, end-to-end delay, cursor at the edge — Table 4 and Figure 6")
    b.p("After the runs above, **4 more sessions A, B, C, D** were logged, one row per camera frame. A and B used a 640×480 "
        "camera and a 1:1 cursor. C and D used 1280×720 and a cursor that is “stretched” near the edge (C: piecewise, "
        "D: smooth). A and B had the robot connected; C and D tested only the cursor.")
    b.table(["Session", "Camera", "Cursor", "Time (s)", "fps", "AI 0 hands (ms)", "AI 1 hand", "AI 2 hands"], [
        ["A", "640×480", "1:1", "186", "25.5", "27.7", "45.5", "43.3"],
        ["B", "640×480", "1:1", "76", "21.9", "31.3", "50.1", "47.5"],
        ["C", "1280×720", "piecewise", "363", "18.0", "30.7", "55.5", "48.3"],
        ["D", "1280×720", "smooth", "214", "21.9", "28.9", "52.4", "47.2"],
    ], widths=[1.5, 2.2, 2.1, 1.9, 1.3, 2.6, 2.3, 2.3])
    b.p("**How to read it:** compare down each column. With no hand, AI takes about 28–31 ms; **with hands, 43–56 ms**, almost "
        "double. The whole-session fps is only 18–25.5, below the 29.9 fps of Section 4.2, because the server also encodes and "
        "streams video to the web page. The 4 sessions differ in what the user did and in length, so this is **not a controlled comparison**.")
    b.fig("fig_sess2_en.png", "Figure 6 in the paper – (a) AI time per session and number of hands; (b) end-to-end delay in session A.")
    b.h3("Figure 6a – box plot of AI inference time")
    b.nsteps([
        "**Horizontal axis:** 4 sessions, each with **3 boxes**: blue = no hand, orange = 1 hand, green = 2 hands.",
        "**Vertical axis:** time for the AI to process one frame (ms). The orange line in each box is the median.",
        "In **all 4 sessions**, the blue box is lowest (about 27–29 ms) and the orange box is highest.",
        "**Surprise:** 1 hand (orange) is **slower** than 2 hands (green). The paper guesses the AI keeps searching for the second hand, but this was not tested.",
        "Session C has the **tallest, widest** orange box (whisker up to about 88 ms): a lot of variation.",
        "Raising the resolution to 1280×720 (C, D) **did not change** the no-hand time, because the AI still runs on a 640-px-wide copy.",
    ])
    b.h3("Figure 6b – histogram of end-to-end delay (session A)")
    b.nsteps([
        "**Horizontal axis:** time from the **camera frame that confirmed a gesture** to the moment the **wheel reached 50 % of its new speed** (ms).",
        "**Vertical axis:** how many gestures fall in each bin. 15 in total.",
        "**Red dashed line** = median **427 ms**. The tallest bar (5 gestures) is right at about 425–440 ms.",
        "Values range from about 320 to 496 ms.",
    ])
    b.p("**What it tells us:** from making a gesture to clear robot motion takes about **0.4–0.5 seconds**. Of that: the "
        "command leaves the laptop after about 37 ms; **about 0.2 s is the deliberate slow speed-up** (acceleration limit 2.0/s, "
        "average target 0.81 of top speed); and about 120–140 ms for the 4-frame filter is not even included. This is larger "
        "than the 257–260 ms in Section 4.3 because the start point is earlier (camera frame, not log row) and the target "
        "speeds are different. **The network is fast; the slow part is camera + AI + filter + speed-up.**")
    b.h3("The other two points of Section 4.5")
    b.bullets([
        "**Wheel tracking:** mean error 0.9–1.5 %. In session A the PWM hit the 0.95 ceiling in 4–8 % of samples: at high "
        "speed the 12 V battery had no spare voltage, so the wheel could not reach the set speed.",
        "**Cursor at the edge:** with the stretched mapping (C, D), the cursor reached the screen edge more often (8.2 % and "
        "4.6 % of frames, against 2.3 % and 1.4 %). But in C and D the user was **trying** to reach the corner, so these "
        "numbers only show the cursor **can reach the edge**, not that hand loss went down.",
    ])

    b.h2("Sections 5 and 6. Limitations and conclusion")
    b.p("**Limitations** (the paper lists them itself): only 1 robot, 1 floor, 1 person; no user study; real-hand cursor tests "
        "had only 12 clicks; no comparison of the controller with a baseline; end-to-end delay from only 15 events; **no "
        "obstacle sensor**, so the human driver is the only safety layer.")
    b.p("**Conclusion:** one webcam and one ESP32 are enough to drive an omni robot and use its dashboard at the same time with "
        "two hands. The network takes a few ms, the wheels track well, and the robot moves in the right direction. **What needs "
        "work is the interaction delay (about 427 ms)**, not the network. Next steps: a user study, comparison with baseline "
        "controllers, a heading sensor and obstacle sensors.")

    b.pagebreak()
    b.h1("Part 4. Quick memory and self-test")
    b.h2("The 10 most important numbers")
    b.table(["#", "Number", "Where", "What it says"], [
        ["1", "13,080 cycles, 2026 s", "Table 2", "Amount of real data used"],
        ["2", "29.9 fps; 18.5 ms", "4.2", "Camera + AI with no hand"],
        ["3", "18–25.5 fps; 45–56 ms", "Table 4, Fig. 6a", "With real hands and the full system running"],
        ["4", "RTT 6.6–8.1 ms (median)", "Table 2, Fig. 4a", "The network is very fast"],
        ["5", "909 ms (max)", "Table 2", "One link drop; the watchdog stopped the robot"],
        ["6", "1.5–3.2 % (mean)", "Table 1, Fig. 5d", "Wheel speed error"],
        ["7", "P95 6.1–7.4 % (v2)", "Fig. 5d", "The tail goes above the 5 % mark"],
        ["8", "≤ 0.6 % moving; 2.5 % turning", "Table 3, Fig. 4b", "The robot follows the command"],
        ["9", "427 ms", "Fig. 6b", "End-to-end delay, the part to improve"],
        ["10", "−5 % shaking; 11/12 clicks worse", "Fig. 3", "Negative cursor result"],
    ], widths=[0.8, 4.6, 3.6, 7.6])
    b.h2("Self-test questions (you may be asked these)")
    qa = [
        ("Why report the median RTT and not the mean?",
         "A few very large values (909 ms) pull the mean up. The median shows the typical case; P95/max show the bad cases."),
        ("In Figure 3, what does a dot above the y = x line mean?",
         "The click point with the anchor moved more than the raw fingertip, so the anchor made it worse. 11 of 12 dots are like that."),
        ("Why does FR need the most PWM?",
         "It has the largest dead zone (a = 0.148) and the steepest slope (b = 0.594). See the red line in Figure 5c."),
        ("Does the wheel error meet the 5 % goal?",
         "The mean does (1.5–3.2 %). The P95 in the v2 run does not (6.1–7.4 %): the whiskers in Figure 5d go above the red line."),
        ("Is Table 3 the true position error of the robot?",
         "No. It comes from the wheel encoders, so wheel slip is not seen. A true error needs an outside camera or another sensor."),
        ("Why is the 427 ms delay bigger than 257–260 ms?",
         "Different start points (the camera frame is about 37 ms earlier than the log row), different target sizes, and most of it is the deliberate acceleration limit."),
        ("What is the biggest weakness of the paper?",
         "1 robot, 1 person, no user study, no controller comparison with a baseline, no obstacle sensor."),
    ]
    for q, a in qa:
        par = b.d.add_paragraph()
        add_rich(par, f"**Q:** {q}")
        par.paragraph_format.space_after = Pt(0)
        par = b.d.add_paragraph()
        par.paragraph_format.left_indent = Cm(0.6)
        add_rich(par, f"**A:** {a}")
    b.save(OUT / "Paper_Explained_EN.docx")


if __name__ == "__main__":
    build_vi()
    build_en()
