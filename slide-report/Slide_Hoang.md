# Nội dung slide — phần Hoàng

Dán vào template Canva có sẵn, **không đổi bố cục/màu**. Mỗi mục dưới đây = 1 trang.
Chữ trên slide để đúng như phần **Slide**; phần **Nói** không đưa lên slide.

Ảnh dùng lại từ repo, khỏi chụp mới:
- ERD: `erd-dictionary/ERD.jpg`
- Kết quả 9 query: `sql/hoang/result-queries/*.png`
- Giao diện chat + trang /admin: ảnh trong `slide-report/Report.docx` (mục 12)

---

## 1. Đặt vấn đề

**Slide**
- Hàng chục nghìn game / năm — nhiều nền tảng, nhà phát hành, khu vực
- Câu hỏi kinh doanh: đầu tư thể loại nào? phát hành nền tảng nào? bán ở đâu?
- Cần CSDL quan hệ chuẩn hoá để trả lời bằng dữ liệu, không bằng cảm tính

**Nói:** dữ liệu doanh số game rời rạc, không có mô hình thì không truy vấn được. Nhóm xây CSDL `Group7` trên SQL Server, cộng thêm một chatbot hỏi đáp bằng tiếng Việt.

---

## 2. Mô hình ER

**Slide**
- Ảnh `ERD.jpg` chiếm ~70% trang
- 6 thực thể: Genre, Game, Publisher, Platform, Region + doanh số
- 2 thực thể trung gian: **Game_Publisher**, **Game_Platform**

**Nói:** ký hiệu Chen. Điểm cần giải thích là vì sao có 2 bảng trung gian — sang slide sau.

---

## 3. Vì sao cần 2 bảng trung gian

**Slide**
- 1 game ↔ nhiều publisher → `Game_Publisher`
- 1 bản phát hành ↔ nhiều nền tảng, khác năm → `Game_Platform`
- Doanh số gắn với **cặp** (Game_Platform, Region), không gắn với game

**Nói:** cùng một game trên PS4 và Wii, do 2 publisher khác nhau, doanh số ở Nhật và Bắc Mỹ khác nhau. Nếu để doanh số ở bảng `game` thì mất hết thông tin đó.

---

## 4. Chuẩn hoá 3NF

**Slide**
- 1NF: mọi thuộc tính nguyên tố
- 2NF: 7/8 bảng khoá đơn; `region_sales` khoá phức hợp nhưng `num_sales` phụ thuộc **đầy đủ** cả 2 cột
- 3NF: không có phụ thuộc bắc cầu
- → **8/8 bảng đạt 3NF, không cần tách thêm**

**Nói:** nhấn vào `region_sales` vì đó là bảng duy nhất có khoá phức hợp, dễ bị hỏi.

---

## 5. Data Dictionary

**Slide**
- Mẫu: Data Element – Description – Data Type – Length – Values
- Ảnh chụp 1 bảng làm ví dụ (`region_sales`)
- Ràng buộc ghi thẳng vào đặc tả, vd `num_sales >= 0`

**Nói:** đặc tả là chỗ chốt kiểu dữ liệu và miền giá trị trước khi code, tránh sửa schema về sau.

---

## 6. Truy vấn — 5 câu bắt buộc

**Slide**
- Inner join · Outer join · Subquery WHERE · Subquery FROM · Group by + aggregate
- Ảnh kết quả 1 câu tiêu biểu (`05-groupby-aggregate.png`)

**Nói:** chạy thật trên 105.362 bản ghi, không phải dữ liệu mẫu.

---

## 7. Truy vấn — 4 câu phân tích

**Slide**
- Xu hướng doanh số theo năm
- Nền tảng bán chạy nhất
- Game bán chạy nhất mỗi nền tảng (`ROW_NUMBER`)
- Doanh số thể loại × khu vực
- Ảnh `07-platform-ban-chay-nhat.png`

**Nói:** 4 câu này vừa trả lời câu hỏi kinh doanh ở slide 1, vừa làm few-shot example cho phần AI.

---

## 8. Ứng dụng AI — NL2SQL Agent

**Slide** (vẽ 1 hàng mũi tên, mỗi bước 2–3 chữ)

> Câu hỏi → Guardrail vào → LLM sinh SQL → Kiểm SQL → DB chỉ đọc → LLM diễn giải → Guardrail ra → Trả lời

- Hỏi tiếng Việt, không cần biết SQL

**Nói:** ví dụ "top 5 game bán chạy nhất ở Nhật năm 2016". Người dùng nghiệp vụ không viết SQL được — đây là cầu nối.

---

## 9. Ba lớp kiểm soát

**Slide**
- **Vào:** chặn prompt injection + lọc câu ngoài chủ đề
- **Giữa:** parse SQL thành AST (`sqlglot`) — chỉ cho SELECT, whitelist 1 view
- **Ra:** grounding check — số liệu phải khớp kết quả SQL thật
- **Tầng DB:** user `nl2sql_readonly`, chỉ `SELECT` trên view

**Nói:** lớp DB là phòng thủ cuối — kể cả 3 lớp trên bị bypass, DB vẫn từ chối vì user không có quyền đọc bảng gốc.

---

## 10. Đo được, sửa được

**Slide** (dạng 3 số to)
- Thiếu index: **8,6 s → 67 ms** (~130×)
- Mở connection mỗi câu: **18–118 s → ổn định**
- Prompt caching: **~90%** chi phí token
- Trang `/admin` log toàn bộ request

**Nói:** 2 lỗi đầu tìm ra nhờ đo latency từng bước ở trang admin, không phải đoán. Đây là phần em tâm đắc nhất.

---

## 11. Web demo

**Slide**
- Ảnh giao diện chat + ảnh `/admin`
- Danh sách game · tìm kiếm · chi tiết · thêm game
- Chat hỏi đáp dữ liệu + trang giám sát

**Nói:** demo trực tiếp 1 câu hỏi nếu còn thời gian.

---

## 12. Kết luận & hướng phát triển

**Slide**
- CSDL 8 bảng 3NF, 105.362 bản ghi, đủ ràng buộc – index – transaction – trigger – procedure
- 9 truy vấn phân tích kiểm chứng
- AI dùng được trực tiếp trên schema quan hệ thiết kế tốt
- Tiếp theo: bảng review/rating · giám sát production

**Nói:** chốt lại thông điệp — thiết kế CSDL tốt là điều kiện để lớp AI phía trên chạy được.
