# Kiến trúc NL2SQL Agent - Group7 Video Game Sales

Phụ trách: Hoàng (AI) - nhánh `hoang/ai`

> **Phạm vi sử dụng: nội bộ nhóm/lớp, không public ra Internet.** Không deploy
> chatbot này thành dịch vụ công khai; chỉ chạy local hoặc trong mạng nội bộ khi
> demo/nộp bài.

Code cài đặt: [`ai/nl2sql/`](nl2sql/). Chạy thử:

```
pip install -r ai/requirements.txt
cp ai/.env.example ai/.env   # điền API key + thông tin DB, KHÔNG commit .env
python -m ai.nl2sql.agent --question "Top 5 game bán chạy nhất ở Nhật năm 2016"
```

## 1. Kiến trúc tổng thể

Với schema quan hệ 3NF nhiều bảng trung gian (`game_publisher`, `game_platform`),
bài toán phù hợp với **NL2SQL (Text-to-SQL) Agent** hơn là RAG văn bản thuần tuý,
vì câu hỏi kiểu "top 5 game bán chạy nhất ở Nhật năm 2016" cần JOIN + AGGREGATE
chính xác, mà semantic search không đảm bảo đúng số liệu.

```
User query (NL)
  -> Guardrail Input (intent + injection check)          [guardrails.py]
  -> Schema context (view đã gộp sẵn JOIN)                [schema.py]
  -> NL2SQL (LLM sinh SQL)                                [llm_client.py]
  -> SQL Validator (whitelist, AST, TOP/LIMIT)            [sql_validator.py]
  -> Read-only DB execution                               [db.py]
  -> LLM diễn giải kết quả thành câu trả lời tự nhiên      [llm_client.py]
  -> Guardrail Output (grounding check)                   [guardrails.py]
  -> Trả lời + log toàn bộ pipeline                        [agent.py]
```

## 2. Đọc / load database cho AI

Không cho LLM đọc raw DB trực tiếp:

- **Schema-as-context**: đưa mô tả schema rút gọn (tên cột, kiểu, ý nghĩa 1 dòng)
  vào prompt thay vì cả file Markdown dài - xem `SCHEMA_CONTEXT` trong `schema.py`.
- **Few-shot SQL examples**: 5 cặp (câu hỏi NL - SQL đúng) cho các dạng truy vấn
  phổ biến (top N, group by, trend theo năm) - `FEW_SHOT_EXAMPLES` trong
  `schema.py`, giúp LLM bắt đúng pattern JOIN qua 2 tầng trung gian.
- **Semantic layer / view**: [`sql/hoang/08_nl2sql_view.sql`](../sql/hoang/08_nl2sql_view.sql)
  tạo view `vw_game_sales_full` gộp sẵn `game + genre + publisher + platform +
  region_sales`, vừa giảm khả năng LLM sinh sai JOIN, vừa "che" các cột id kỹ
  thuật không cần thiết.
- **Kết nối DB read-only**: `db.py` khuyến nghị dùng SQL Server login chỉ có
  quyền `SELECT` trên `vw_game_sales_full` (không cấp quyền bảng gốc, không
  dùng `sa`/admin) - xem chú thích trong file.

## 3. Che thông tin không cần thiết (data minimization)

Dataset này không có bảng user/customer (không PII), nhưng vẫn áp dụng nguyên
tắc tối thiểu hoá:

- **Whitelist bảng/view**: `sql_validator.py` chỉ cho phép SELECT trên
  `vw_game_sales_full` (`ALLOWED_TABLES` trong `schema.py`), chặn mọi bảng gốc.
- **View thay vì bảng gốc**: nếu sau này thêm dữ liệu nhạy cảm (giá hợp đồng
  publisher...), tạo view riêng, không cho AI đụng bảng gốc.
- **Row-level filter theo tenant**: chưa cần với dữ liệu hiện tại (không
  multi-tenant); nếu mở rộng, filter phải do backend chèn cố định vào `WHERE`,
  không để LLM tự quyết định.

## 4. Guardrail

**Input** (`guardrails.check_input`):
- Regex chặn injection (`ignore previous instructions`, `DROP TABLE`,
  `xp_cmdshell`...) - `INJECTION_PATTERNS`. Đây là ranh giới bảo mật phải chặn
  **trước khi** gọi LLM, không thể giao cho LLM tự xử lý an toàn.
- **Lọc domain (câu hỏi có thuộc chủ đề doanh số game không) do chính LLM
  quyết định**, không dùng keyword-matching tĩnh: system prompt trong
  `llm_client.py` yêu cầu LLM trả về đúng token `NOT_APPLICABLE` nếu câu hỏi
  ngoài phạm vi/yêu cầu sửa-xoá dữ liệu/injection. `agent.py` kiểm tra token
  này trước khi đưa SQL vào validator. Lý do đổi từ keyword-matching: danh
  sách từ khóa tĩnh dễ chặn nhầm câu hỏi diễn đạt khác thường (vd hỏi thuần
  Việt không dùng đúng từ trong danh sách), trong khi LLM hiểu ngữ nghĩa tốt
  hơn nhiều và không cần bảo trì danh sách từ khóa.
- *Chưa làm (production)*: rate limit theo user/IP.

**SQL Validator** (`sql_validator.validate_and_enforce_limit`, lớp quan trọng
nhất):
- Parse SQL bằng AST (`sqlglot`, dialect T-SQL) thay vì regex.
- Chỉ chấp nhận 1 câu `SELECT` duy nhất; chặn cứng
  `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/MERGE/TRUNCATE` ở mọi node trong cây.
- Whitelist bảng/view (mục 3).
- Tự động thêm `TOP 100` (`MAX_ROWS` trong `.env`) nếu SQL từ LLM thiếu giới
  hạn số dòng.
- *Chưa làm (production)*: `EXPLAIN`/cost estimate trước khi chạy, timeout
  query (đã có tham số `QUERY_TIMEOUT_SECONDS` nhưng cần benchmark thêm).

**Output** (`guardrails.check_output`):
- Grounding check đơn giản: mọi con số LLM nêu trong câu trả lời phải khớp với
  giá trị có trong kết quả SQL thật - chặn hallucinate số liệu rõ ràng.
- *Chưa làm (production)*: kiểm tra ngữ nghĩa sâu hơn (không chỉ so khớp
  chuỗi số).

## 5. Cập nhật dữ liệu mới (không cho AI ghi trực tiếp)

AI/API không được ghi vào bảng production. Quy trình đề xuất (chưa cài đặt
code, mô tả để tham khảo khi mở rộng):

1. **Staging area**: dữ liệu mới nạp vào bảng staging trước.
2. **Validation**: FK phải tồn tại, `num_sales >= 0`, `release_year` hợp lý
   (đã có constraint tương ứng, xem `sql/vi/02_constraints.sql`), check
   duplicate PK, check outlier thống kê (z-score) để flag review thủ công.
3. **Human-in-the-loop** cho bản ghi bị flag hoặc entity mới (publisher/genre
   mới).
4. **Transactional merge**: merge vào production trong 1 transaction, rollback
   nếu lỗi (mẫu ROLLBACK đã có ở `sql/vi/05_transaction.sql`).
5. **Audit log**: ghi ai/khi nào/nguồn nào đưa dữ liệu vào.
6. Sau merge, invalidate cache/semantic layer để AI không dùng dữ liệu cũ.

## 6. Kiểm soát dữ liệu bẩn / tấn công (data poisoning)

- Constraint ở DB level đã có (`ck_region_sales_nonnegative`, `ck_release_year`,
  `uq_game_name` - xem `sql/vi/02_constraints.sql`).
- Anomaly detection (z-score/IQR trên `num_sales` theo genre/platform) trước
  khi merge - hướng phát triển, chưa cài đặt.
- Trust scoring theo nguồn dữ liệu nếu nhận từ nhiều nguồn - hướng phát triển.
- Immutable audit trail (write-once) để revert khi phát hiện tấn công chèn dữ
  liệu giả - hướng phát triển.
- Dữ liệu mới không bao giờ dùng trực tiếp để few-shot/fine-tune LLM mà không
  qua review, tránh ảnh hưởng hành vi model.

## 7. Monitoring khi chạy production

**Đã cài đặt** (mức cơ bản, đủ cho demo nội bộ):

- `agent.py` đo thời gian từng bước (LLM sinh SQL, DB exec, LLM diễn giải,
  tổng) và ghi 1 dòng log cho **mọi** request (dù thành công/bị chặn/lỗi hạ
  tầng) vào `ai/nl2sql/logs.db` (SQLite) - xem `logging_store.py`.
- **Trang admin** `webapp.py` route `/admin` (bảo vệ bằng HTTP Basic Auth,
  `ADMIN_USER`/`ADMIN_PASSWORD` trong `.env`): bảng toàn bộ request gần nhất
  (câu hỏi, SQL sinh ra, SQL sau validate, số dòng, câu trả lời, bị chặn ở
  bước nào, latency từng bước) + 3 số liệu tổng quan (tổng số câu hỏi, số bị
  chặn, latency trung bình).
- **Bắt lỗi hạ tầng**: LLM call có timeout 30s (`llm_client.REQUEST_TIMEOUT_SECONDS`),
  DB có query timeout tương ứng `QUERY_TIMEOUT_SECONDS`; nếu timeout/mất kết
  nối, `agent.ask()` trả về `error=True` thay vì treo tiến trình, phía web
  hiện thông báo bảo trì thay vì đứng im vô thời hạn.
- Nhờ đo latency từng bước mà phát hiện được 1 bug thật khi demo: `db.py`
  trước đó mở connection SQL Server mới cho mỗi câu hỏi, tốn 18-118 giây/lần
  (đo được qua cột "DB exec" trên `/admin`) do bắt tay với named instance qua
  SQL Browser không ổn định - sửa bằng cách tái sử dụng 1 connection cho cả
  tiến trình, giảm còn ~vài chục-vài trăm ms.
- **Bug thật thứ 2** (vẫn qua cột "DB exec"): database `Group7` đang test
  hoàn toàn **không có index** ngoài khoá chính (kể cả `region_sales` - bảng
  lớn nhất, 65,320 dòng, trung tâm mọi JOIN trong `vw_game_sales_full` - là
  HEAP không index) - mỗi câu hỏi phải quét toàn bộ 8 bảng. Đo trực tiếp bằng
  `SET STATISTICS TIME ON`: `MAX(release_year)` qua view mất **8.6 giây**
  (so với 3ms nếu query thẳng 1 bảng không qua join) - vượt luôn
  `QUERY_TIMEOUT_SECONDS=10`. Đã thêm index cho các cột FK dùng để JOIN
  (`sql/hoang/09_indexes.sql`) - cùng câu hỏi đó sau khi index "ấm" cache còn
  **67ms** (nhanh hơn ~130 lần). Lưu ý: `region_sales` có 16 cặp
  `(region_id, game_platform_id)` trùng lặp nên chưa thêm được PRIMARY KEY/
  UNIQUE (sẽ báo lỗi) - chỉ thêm index thường, việc xử lý trùng lặp là quyết
  định nghiệp vụ/ràng buộc dữ liệu, không tự ý xoá.
- **Biểu đồ tròn (donut, CSS conic-gradient)** trên `/admin` thể hiện tỷ lệ 3
  nhóm trạng thái: Thành công / Bị chặn theo thiết kế (gộp cả 4 loại guardrail
  và validator) / Lỗi hạ tầng - tự làm mới mỗi 45s. Ban đầu thử tách riêng
  từng loại chặn thành 6 màu, nhưng chạy `validate_palette.js` (skill
  `dataviz`) cho thấy không tổ hợp 6 màu nào trong bảng màu categorical vượt
  qua kiểm tra all-pairs (đúng như tài liệu skill cảnh báo: quá 3 màu là hết
  an toàn) - nên gộp còn 3 nhóm dùng đúng bộ màu status (good/warning/
  critical), luôn kèm nhãn chữ trong legend. Chi tiết từng loại chặn cụ thể
  vẫn xem đầy đủ ở bảng log.
- **Lỗi hạ tầng hiện cho user theo nhóm** (timeout / mất kết nối / lỗi xác
  thực / không rõ nguyên nhân - `agent._categorize_error`), không lộ chi tiết
  exception/stack trace ra giao diện; chi tiết thật vẫn được ghi đầy đủ vào
  `logs.db` để admin debug qua `/admin`.

**Chưa cài đặt (hướng phát triển)** - đầy đủ hơn cho production cần 3 nhóm:

- **Hệ thống/hiệu năng**: Prometheus + Grafana hoặc APM thay vì SQLite/HTML
  tự chế; connection pool thật thay vì 1 connection đơn.
- **Chất lượng/an toàn AI**: % câu trả lời grounded theo thời gian, human
  feedback (thumbs up/down), drift detection trên phân bố câu hỏi.
- **Dữ liệu**: dashboard chất lượng dữ liệu, alert khi constraint bị vi phạm
  bất thường.

## Tóm tắt: đã cài đặt vs. hướng phát triển

| Hạng mục | Trạng thái |
|---|---|
| Pipeline NL2SQL end-to-end (guardrail → SQL → DB → trả lời) | Đã cài đặt (`ai/nl2sql/`) |
| Schema-as-context + few-shot | Đã cài đặt (`schema.py`) |
| Semantic view whitelist | Đã cài đặt (`sql/hoang/08_nl2sql_view.sql`) |
| SQL Validator (AST, whitelist, auto-limit) | Đã cài đặt (`sql_validator.py`) |
| Guardrail input (injection filter + domain check qua LLM) | Đã cài đặt (`guardrails.py` + `llm_client.NOT_APPLICABLE`) |
| Guardrail output (grounding check cơ bản) | Đã cài đặt (`guardrails.py`) |
| Log pipeline + trang admin monitor (`/admin`) | Đã cài đặt (`logging_store.py`, `webapp.py`) |
| Timeout + bắt lỗi hạ tầng (LLM/DB), không treo vô hạn | Đã cài đặt (`llm_client.py`, `agent.py`, `db.py`) |
| Intent classifier riêng, rate limit, cost estimate/EXPLAIN | Hướng phát triển |
| Staging + validation + merge có audit log | Hướng phát triển (mô tả ở mục 5) |
| Anomaly detection, trust scoring, immutable audit trail | Hướng phát triển (mục 6) |
| Monitoring production (Prometheus/Grafana, drift detection) | Hướng phát triển (mục 7) |
