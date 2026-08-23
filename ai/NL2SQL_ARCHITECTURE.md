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

`agent.py` hiện log từng bước pipeline qua `logging` (SQL sinh ra, SQL sau
validate, số dòng kết quả, lý do bị guardrail chặn). Đây là nền tối thiểu; đầy
đủ hơn cho production cần 3 nhóm (hướng phát triển, chưa cài đặt):

- **Hệ thống/hiệu năng**: latency từng bước, error rate, resource usage DB -
  Prometheus + Grafana hoặc APM.
- **Chất lượng/an toàn AI**: tỉ lệ guardrail chặn, % câu trả lời grounded,
  human feedback (thumbs up/down), drift detection trên phân bố câu hỏi.
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
| Log pipeline | Đã cài đặt (module `logging`) |
| Intent classifier riêng, rate limit, cost estimate/EXPLAIN | Hướng phát triển |
| Staging + validation + merge có audit log | Hướng phát triển (mô tả ở mục 5) |
| Anomaly detection, trust scoring, immutable audit trail | Hướng phát triển (mục 6) |
| Monitoring production (Prometheus/Grafana, drift detection) | Hướng phát triển (mục 7) |
