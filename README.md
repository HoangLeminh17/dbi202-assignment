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
├── sql/                     # File .sql, tách theo từng người phụ trách
│   ├── hoang/
│   │   ├── 04_queries.sql       # Các câu query yêu cầu + query insight
│   │   └── 08_nl2sql_view.sql   # View vw_game_sales_full cho NL2SQL Agent
│   ├── trung/
│   │   ├── 01_createDB.sql      # Tạo database + bảng
│   │   ├── 03_insert.sql        # Dữ liệu mẫu
│   │   └── 07_procedure.sql     # Stored procedure
│   ├── vi/
│   │   ├── 02_constraints.sql   # Ràng buộc (ALTER TABLE)
│   │   ├── 05_transaction.sql   # Transaction + rollback
│   │   └── 06_trigger.sql       # Trigger
│   └── quantl3/
│       └── G7_Dbscript.sql      # Script gốc (Contributor: quantl3@fpt.edu.vn) - tạo bảng + insert dữ liệu thô
├── slide-report/            # Bản nộp cuối cùng
│   ├── Report.docx          # Báo cáo
│   └── Slide.pptx           # Slide thuyết trình
├── erd-dictionary/          # Tài liệu thiết kế (Hoàng phụ trách)
│   ├── ERD.md                # Sơ đồ ER + giải thích quan hệ, phụ thuộc hàm, chuẩn hoá 3NF
│   ├── ERD.svg / ERD.jpg     # Sơ đồ ER (nguồn vector / ảnh chèn báo cáo)
│   └── DataDictionary.md     # Đặc tả yêu cầu dữ liệu (data dictionary)
└── ai/                       # Ứng dụng AI: NL2SQL Agent (Hoàng phụ trách)
    ├── nl2sql/                   # Hỏi đáp dữ liệu bằng ngôn ngữ tự nhiên - nội bộ, không public
    │   ├── agent.py                  # Điều phối pipeline: guardrail -> LLM sinh SQL -> validate -> DB -> trả lời
    │   ├── webapp.py                 # Web demo (Flask): trang chat + trang /admin xem log
    │   ├── logging_store.py          # Ghi log mọi request vào SQLite (ai/nl2sql/logs.db)
    │   ├── schema.py                 # Schema-as-context + few-shot SQL examples
    │   ├── sql_validator.py          # Validator bằng AST (sqlglot): whitelist SELECT, auto TOP/LIMIT
    │   ├── guardrails.py             # Chặn prompt injection + grounding check output
    │   ├── llm_client.py             # Gọi LLM ngoài (Claude/ChatGPT/Gemini, chọn qua .env)
    │   ├── db.py                     # Kết nối SQL Server read-only (tái sử dụng connection)
    │   └── config.py                 # Đọc cấu hình từ .env
    ├── NL2SQL_ARCHITECTURE.md    # Kiến trúc đầy đủ (copy vào báo cáo mục Áp dụng AI)
    ├── .env.example               # Template biến môi trường (API key, DB) - KHÔNG chứa giá trị thật
    └── requirements.txt          # Thư viện Python cần cài
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

**NL2SQL Agent** (`ai/nl2sql/`) — chatbot hỏi đáp dữ liệu doanh số game bằng ngôn ngữ tự nhiên (tiếng Việt/Anh), truy vấn trực tiếp từ database `Group7`:

- Dùng LLM API ngoài (Claude/ChatGPT/Gemini, chọn qua `.env`) để sinh SQL từ câu hỏi, chạy trên view `vw_game_sales_full`, rồi diễn giải kết quả thành câu trả lời tự nhiên.
- Có guardrail chặn prompt injection, SQL validator (whitelist SELECT, chặn DML/DDL, tự giới hạn số dòng), và grounding check chống LLM bịa số liệu.
- Trang **`/admin`** (Basic Auth) xem log toàn bộ request: câu hỏi, SQL sinh ra, có bị chặn không, thời gian xử lý từng bước.
- **Chỉ phục vụ nội bộ nhóm/lớp, không deploy public.**
- Kiến trúc đầy đủ: [`ai/NL2SQL_ARCHITECTURE.md`](ai/NL2SQL_ARCHITECTURE.md) (copy vào báo cáo mục này).
- Cách chạy: xem mục "Hướng dẫn setup để dev tiếp" bên dưới.

## Phân chia công việc

**Hoàng (AI, nhóm trưởng):**
- Chủ trì thiết kế ER và mô hình quan hệ, chuẩn hoá 3NF, data dictionary — xem [`erd-dictionary/ERD.md`](erd-dictionary/ERD.md) và [`erd-dictionary/DataDictionary.md`](erd-dictionary/DataDictionary.md).
- Viết `sql/hoang/04_queries.sql` (đặc biệt các câu group by/aggregate, subquery phức tạp gắn với insight).
- Code/dev NL2SQL Agent (`ai/nl2sql/`): hoàn thiện, test thử với dữ liệu thật.
- Phần "Áp dụng AI" trong báo cáo + slide.
- Tổng hợp `slide-report/Report.docx`, làm `slide-report/Slide.pptx`, gửi mail assignment (CC nhóm).

**Trung (SE):**
- Hoàn thiện `sql/trung/01_createDB.sql` và `sql/trung/03_insert.sql` (tách dữ liệu từ `sql/quantl3/G7_Dbscript.sql`).
- Rà soát khoá chính/khoá ngoại, thêm index cần thiết.
- Viết `sql/trung/07_procedure.sql`.
- Hỗ trợ phần cài đặt vật lý trong báo cáo.

**Vi (IS):**
- Viết `sql/vi/02_constraints.sql` (≥3 ràng buộc: CHECK, UNIQUE, FK...).
- Viết `sql/vi/06_trigger.sql` và `sql/vi/05_transaction.sql` (có ROLLBACK).
- Đề xuất thêm khía cạnh bảo mật (phân quyền GRANT/REVOKE theo vai trò, kiểm tra rủi ro injection trong các câu query) - có thể tính là phần mở rộng cho báo cáo.

**Chung cả nhóm:**
- Thống nhất tỷ lệ đóng góp trước khi nộp để ghi vào báo cáo.
- Review chéo (Lắng nghe & phản biện) trước khi hoàn thiện bản nộp cuối.

## Hướng dẫn setup để dev tiếp

**1. Cài đặt cơ bản:** clone repo, cài **SQL Server** (Developer/Express edition) + **SQL Server Management Studio (SSMS)**.

**2. Dựng database:** mở SSMS, kết nối instance local, chạy lần lượt (Execute) các file `.sql` trong `sql/` theo thứ tự:
1. `sql/trung/01_createDB.sql` — tạo database `Group7` và các bảng.
2. `sql/trung/03_insert.sql` — nạp dữ liệu mẫu.
3. `sql/vi/02_constraints.sql` — thêm ràng buộc.
4. `sql/vi/05_transaction.sql`, `sql/vi/06_trigger.sql` — transaction và trigger.
5. `sql/trung/07_procedure.sql` — stored procedure.
6. `sql/hoang/04_queries.sql` — chạy thử các câu query.
7. `sql/hoang/08_nl2sql_view.sql` — tạo view `vw_game_sales_full` (cần cho NL2SQL Agent).

> Restore nhanh: chạy trực tiếp `sql/quantl3/G7_Dbscript.sql` để có database đầy đủ dữ liệu, rồi chạy tiếp các file còn lại từ bước 3.

**3. Chạy NL2SQL Agent:**
```
pip install -r ai/requirements.txt
cp ai/.env.example ai/.env
```
Mở file `ai/.env` vừa tạo, điền `ANTHROPIC_API_KEY` (hoặc `OPENAI_API_KEY`/`GOOGLE_API_KEY` tuỳ `LLM_PROVIDER`), sửa `DB_SERVER` đúng instance SQL Server đang chạy (vd `localhost\SQLEXPRESS01`), và đặt `ADMIN_PASSWORD` (để dùng trang xem log).

Chạy web chat:
```
python -m ai.nl2sql.webapp
```
Mở trình duyệt: http://127.0.0.1:5050 (trang chat) và http://127.0.0.1:5050/admin (xem log, đăng nhập bằng `ADMIN_USER`/`ADMIN_PASSWORD`).

Hoặc test nhanh qua CLI không cần mở web:
```
python -m ai.nl2sql.agent --question "Top 5 game bán chạy nhất ở Nhật năm 2016"
```

**4. Quy trình làm việc:** mỗi người sửa file trong thư mục phụ trách của mình thì tạo nhánh riêng (`git checkout -b <ten>/<mo-ta-ngan>`), commit, tạo Pull Request để cả nhóm review trước khi merge vào `main`.

**5. Trước khi nộp bài:** kiểm tra lại toàn bộ script chạy được từ đầu trên 1 database rỗng (drop và tạo lại `Group7` rồi chạy lại toàn bộ theo thứ tự ở bước 2).

## Nộp bài

Đóng gói theo tên `DBI202Project_CC_NNN_RN.zip` (CC = lớp, NNN = họ tên đầy đủ, RN = mã số/roll number — theo nguyên văn đề bài: *"CC is your class, NNN is your fullname and RN is your roll number"*), gồm:
- Báo cáo `.docx`/`.pdf` (từ `slide-report/Report.docx`).
- Toàn bộ file `.sql` trong `sql/`.
