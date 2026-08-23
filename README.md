# DBI202 - Assignment Nhóm 7

Đồ án môn Cơ sở dữ liệu (DBI202) - Chủ đề: **Video Game Sales** (database `Group7` với các bảng `platform`, `genre`, `publisher`, `region`, `game`, `game_publisher`, `game_platform`, `region_sales`).

**Deadline: 23:59 24/08/2026**

## Thành viên nhóm

| Tên | Chuyên ngành | Vai trò | Phụ trách chính |
|---|---|---|---|
| Hoàng | AI | Nhóm trưởng | Thiết kế ER/quan hệ, tổng hợp báo cáo & slide, mảng ứng dụng AI, gửi mail assignment (CC cả nhóm) |
| Trung | SE | Thành viên | Cài đặt vật lý CSDL (`createDB.sql`, `insert.sql`, `procedure.sql`) |
| Vi | IS | Thành viên | Ràng buộc dữ liệu, trigger, transaction (`constraints.sql`, `trigger.sql`, `transaction.sql`) |

## Cấu trúc thư mục

```
dbi202-assignment/
├── yeu-cau-assignment/      # Đề bài gốc
│   ├── Assignment1.docx     # Đề bài tiếng Anh (khung yêu cầu chung)
│   ├── Assignment2.docx     # Đề bài tiếng Việt (chi tiết nội dung báo cáo)
│   └── MoTaDeBai.md         # Tóm tắt tiếng Việt nội dung 2 file đề bài trên
├── sql/                     # Các file .sql theo yêu cầu, tách riêng theo từng người phụ trách
│   ├── hoang/
│   │   ├── 04_queries.sql       # Hoàng - các câu query yêu cầu
│   │   └── 08_nl2sql_view.sql   # Hoàng - view vw_game_sales_full cho NL2SQL Agent
│   ├── trung/
│   │   ├── 01_createDB.sql      # Trung - tạo database + bảng
│   │   ├── 03_insert.sql        # Trung - dữ liệu mẫu
│   │   └── 07_procedure.sql     # Trung - stored procedure
│   ├── vi/
│   │   ├── 02_constraints.sql   # Vi - ràng buộc (ALTER TABLE)
│   │   ├── 05_transaction.sql   # Vi - transaction + rollback
│   │   └── 06_trigger.sql       # Vi - trigger
│   └── quantl3/
│       └── G7_Dbscript.sql      # Script gốc (Contributor: quantl3@fpt.edu.vn) - tạo bảng + insert dữ liệu thô, dùng để tham khảo/tách vào sql/trung/
├── slide-report/                # Bản nộp cuối cùng
│   ├── Report.docx          # Báo cáo (đang trống, Hoàng tổng hợp)
│   └── Slide.pptx           # Slide thuyết trình (đang trống, Hoàng tổng hợp)
├── erd-dictionary/          # Tài liệu thiết kế (Hoàng phụ trách)
│   ├── ERD.md               # Sơ đồ ER (ký hiệu Chen) + giải thích quan hệ giữa các entity
│   ├── ERD.svg               # Sơ đồ ER dạng vector (nguồn, chỉnh sửa được)
│   ├── ERD.jpg               # Sơ đồ ER xuất sẵn dạng ảnh (chèn thẳng vào báo cáo)
│   └── DataDictionary.md    # Đặc tả yêu cầu dữ liệu (data dictionary) cho từng thuộc tính
├── ai/                      # Phần mở rộng ứng dụng AI (Hoàng code/dev)
│   ├── recommend.py         # Script gợi ý game tương tự (content-based, dùng genre/publisher/platform)
│   ├── nl2sql/               # NL2SQL Agent - hỏi đáp dữ liệu bằng ngôn ngữ tự nhiên (nội bộ, xem NL2SQL_ARCHITECTURE.md)
│   │   ├── agent.py             # Điều phối pipeline: guardrail -> LLM sinh SQL -> validate -> DB -> trả lời
│   │   ├── schema.py            # Schema-as-context (rút gọn) + few-shot SQL examples
│   │   ├── sql_validator.py     # Validator bằng AST (sqlglot): whitelist SELECT, auto TOP/LIMIT
│   │   ├── guardrails.py        # Guardrail input (injection/domain) + output (grounding check)
│   │   ├── llm_client.py        # Gọi LLM ngoài (Claude/ChatGPT/Gemini, chọn qua .env)
│   │   ├── db.py                # Kết nối SQL Server read-only
│   │   └── config.py            # Đọc cấu hình từ .env
│   ├── NL2SQL_ARCHITECTURE.md   # Kiến trúc đầy đủ NL2SQL Agent (copy vào báo cáo mục Áp dụng AI)
│   ├── .env.example          # Template biến môi trường (API key, DB) - KHÔNG chứa giá trị thật
│   └── requirements.txt     # Thư viện Python cần cài (pyodbc, pandas, scikit-learn, sqlglot, anthropic...)
└── web/                     # Web demo nối AI + SQL lại với nhau (Trung code/dev)
    ├── app.py               # Flask app: trang danh sách game + trang gợi ý (gọi ai/recommend.py)
    ├── templates/           # index.html, recommend.html
    └── requirements.txt     # Thư viện Python cần cài (flask, pyodbc, pandas, scikit-learn)
```

## Yêu cầu đề bài (tổng hợp từ `yeu-cau-assignment/Assignment1.docx` và `yeu-cau-assignment/Assignment2.docx`)

> Xem tóm tắt chi tiết bằng tiếng Việt tại [`yeu-cau-assignment/MoTaDeBai.md`](yeu-cau-assignment/MoTaDeBai.md).

1. Chọn một nghiệp vụ/hệ thống thực tế (nhóm chọn: **thống kê doanh số game theo khu vực/nền tảng/nhà phát hành**).
2. Phát biểu bài toán, mô tả nghiệp vụ, liệt kê từng nghiệp vụ cụ thể.
3. Xây dựng mô hình ER (đúng ký hiệu) cho hệ thống — đã có tại [`erd-dictionary/ERD.md`](erd-dictionary/ERD.md).
4. Chuyển mô hình ER sang mô hình quan hệ, xác định phụ thuộc hàm, chuẩn hoá về **3NF** — xem giải thích trong [`erd-dictionary/ERD.md`](erd-dictionary/ERD.md).
5. Đặc tả yêu cầu dữ liệu (data dictionary) cho từng thuộc tính quan trọng — đã có tại [`erd-dictionary/DataDictionary.md`](erd-dictionary/DataDictionary.md).
6. Liệt kê danh sách các ràng buộc dữ liệu.
7. Cài đặt vật lý trên **SQL Server** (đã dựng sẵn template trong `sql/`, xem cấu trúc phía trên).
8. Kết luận, hướng phát triển.

> `sql/quantl3/G7_Dbscript.sql` (Contributor: quantl3@fpt.edu.vn) hiện chỉ có tạo bảng + insert dữ liệu thô.

## Yêu cầu bên lề (theo ảnh nhóm trưởng gửi)

- File SQL (theo cấu trúc trong `sql/`).
- File `.docx` báo cáo (`slide-report/Report.docx`), **độ dài 8-10 trang**: bìa, mục lục, danh mục hình vẽ, bảng biểu - Đặt vấn đề - Các bước giải quyết vấn đề - Kết luận, hướng phát triển - Tỷ lệ đóng góp mỗi thành viên.
- File PowerPoint thuyết trình (`slide-report/Slide.pptx`).
- Mỗi nhóm có nhóm trưởng; nhóm trưởng đại diện gửi mail assignment, CC các thành viên trong nhóm.

## Áp dụng AI (điểm khuyến khích)

Đề bài khuyến khích áp dụng AI để tăng điểm. Gợi ý cách áp dụng phù hợp với dữ liệu game sales:

- Dùng AI hỗ trợ sinh/tối ưu câu SQL (trigger, procedure, query phức tạp) - ghi rõ trong báo cáo phần nào có AI hỗ trợ.
- Dùng AI phân tích dữ liệu game sales để đề xuất thêm nghiệp vụ/insight (ví dụ: xu hướng doanh số theo thể loại/khu vực), minh hoạ bằng query hoặc biểu đồ trong báo cáo.
- **Đã code sẵn:** [`ai/recommend.py`](ai/recommend.py) — script Python goi y (recommend) game tương tự dựa trên thể loại/nhà phát hành/nền tảng (content-based filtering, dùng `scikit-learn`), kết nối trực tiếp vào database `Group7`. Hoàng phát triển thêm phần này, nêu rõ trong báo cáo đây là phần mở rộng ứng dụng AI.
- **Đã code sẵn:** [`ai/nl2sql/`](ai/nl2sql/) — NL2SQL Agent hỏi đáp dữ liệu bằng ngôn ngữ tự nhiên, dùng LLM API ngoài (Claude/ChatGPT/Gemini, chọn qua `.env`), có guardrail input/output và SQL validator (whitelist SELECT, chặn DML/DDL). **Chỉ phục vụ nội bộ nhóm/lớp, không deploy public.** Xem kiến trúc đầy đủ tại [`ai/NL2SQL_ARCHITECTURE.md`](ai/NL2SQL_ARCHITECTURE.md).

## Phân chia công việc

**Hoàng (AI, nhóm trưởng):**
- Chủ trì thiết kế ER và mô hình quan hệ, chuẩn hoá 3NF, data dictionary — xem [`erd-dictionary/ERD.md`](erd-dictionary/ERD.md) và [`erd-dictionary/DataDictionary.md`](erd-dictionary/DataDictionary.md).
- Viết `sql/hoang/04_queries.sql` (đặc biệt các câu group by/aggregate, subquery phức tạp gắn với insight).
- Code/dev phần ứng dụng AI trong `ai/` (`ai/recommend.py`): hoàn thiện, test thử với dữ liệu thật, có thể mở rộng thêm (collaborative filtering theo doanh số vùng, sinh giải thích gợi ý bằng ngôn ngữ tự nhiên...).
- Phần "Áp dụng AI" trong báo cáo + slide.
- Tổng hợp `slide-report/Report.docx`, làm `slide-report/Slide.pptx`, gửi mail assignment (CC nhóm).

**Trung (SE):**
- Hoàn thiện `sql/trung/01_createDB.sql` và `sql/trung/03_insert.sql` (tách dữ liệu từ `sql/quantl3/G7_Dbscript.sql`).
- Rà soát khoá chính/khoá ngoại, thêm index cần thiết.
- Viết `sql/trung/07_procedure.sql`.
- Code/dev web demo trong `web/` (`web/app.py`): nối CSDL (`sql/`) và phần AI (`ai/recommend.py`) lại với nhau thành 1 demo end-to-end (trang danh sách game + trang gợi ý), có thể bổ sung thêm route CRUD gọi stored procedure.
- Hỗ trợ phần cài đặt vật lý trong báo cáo.

**Vi (IS):**
- Viết `sql/vi/02_constraints.sql` (≥3 ràng buộc: CHECK, UNIQUE, FK...).
- Viết `sql/vi/06_trigger.sql` và `sql/vi/05_transaction.sql` (có ROLLBACK).
- Đề xuất thêm khía cạnh bảo mật (phân quyền GRANT/REVOKE theo vai trò, kiểm tra rủi ro injection trong các câu query) - có thể tính là phần mở rộng cho báo cáo.

**Chung cả nhóm:**
- Thống nhất tỷ lệ đóng góp trước khi nộp để ghi vào báo cáo.
- Review chéo (Lắng nghe & phản biện) trước khi hoàn thiện bản nộp cuối.

## Hướng dẫn setup để dev tiếp

1. Clone repo và cài **SQL Server** (Developer/Express edition) + **SQL Server Management Studio (SSMS)**.
2. Chạy lần lượt các file `.sql` trong `sql/` theo đúng thứ tự phụ thuộc (mở bằng SSMS, kết nối tới instance local, rồi Execute):
   1. `sql/trung/01_createDB.sql` — tạo database `Group7` và các bảng.
   2. `sql/trung/03_insert.sql` — nạp dữ liệu mẫu (khi Trung đã tách xong từ `sql/quantl3/G7_Dbscript.sql`).
   3. `sql/vi/02_constraints.sql` — thêm các ràng buộc.
   4. `sql/vi/05_transaction.sql`, `sql/vi/06_trigger.sql` — transaction và trigger.
   5. `sql/trung/07_procedure.sql` — stored procedure.
   6. `sql/hoang/04_queries.sql` — chạy thử các câu query.
3. Nếu chỉ cần restore nhanh từ dữ liệu gốc: chạy trực tiếp `sql/quantl3/G7_Dbscript.sql` để có database `Group7` đầy đủ dữ liệu, sau đó chạy tiếp `02_constraints.sql` → `06_trigger.sql` → `07_procedure.sql` để bổ sung các phần còn thiếu.
4. Chạy phần AI/web demo (sau khi database đã có dữ liệu):
   ```
   pip install -r ai/requirements.txt
   pip install -r web/requirements.txt
   python ai/recommend.py --game-id 1 --top-n 5   # test nhanh phan AI
   python web/app.py                              # chay web demo tai http://127.0.0.1:5000
   ```
5. Chạy web demo NL2SQL Agent (hỏi đáp dữ liệu bằng ngôn ngữ tự nhiên - nội bộ, không public):
   ```
   pip install -r ai/requirements.txt
   cp ai/.env.example ai/.env
   # Mở ai/.env, điền ANTHROPIC_API_KEY (hoặc OPENAI_API_KEY/GOOGLE_API_KEY tuỳ LLM_PROVIDER)
   # và sửa DB_SERVER cho đúng instance SQL Server đang chạy (vd localhost\SQLEXPRESS01)
   sqlcmd -S "<DB_SERVER>" -E -C -i sql/hoang/08_nl2sql_view.sql   # tạo view vw_game_sales_full
   python -m ai.nl2sql.webapp     # chay web demo tai http://127.0.0.1:5050
   ```
   Hoặc chạy thẳng qua CLI không cần mở web: `python -m ai.nl2sql.agent --question "Top 5 game bán chạy nhất ở Nhật năm 2016"`. Xem kiến trúc đầy đủ tại [`ai/NL2SQL_ARCHITECTURE.md`](ai/NL2SQL_ARCHITECTURE.md).
   Nếu SQL Server không chạy ở `localhost` mặc định, sửa `CONNECTION_STRING` trong `ai/recommend.py` cho đúng.
5. Mỗi người khi sửa file trong thư mục phụ trách của mình thì tạo nhánh riêng (`git checkout -b <ten>/<mo-ta-ngan>`), commit, rồi tạo Pull Request để cả nhóm review trước khi merge vào `main`.
6. Trước khi nộp bài, kiểm tra lại toàn bộ script chạy được từ đầu trên một database rỗng (drop và tạo lại `Group7` rồi chạy lại toàn bộ theo thứ tự ở bước 2).

## Nộp bài

Đóng gói theo tên `DBI202Project_CC_NNN_RN.zip` (CC = lớp, NNN = họ tên đầy đủ, RN = mã số/roll number — theo nguyên văn đề bài: *"CC is your class, NNN is your fullname and RN is your roll number"*), gồm:
- Báo cáo `.docx`/`.pdf` (từ `slide-report/Report.docx`).
- Toàn bộ file `.sql` trong `sql/`.
