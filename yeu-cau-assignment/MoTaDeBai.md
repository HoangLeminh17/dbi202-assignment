# Mô tả đề bài (Assignment1.docx & Assignment2.docx)

Thư mục này chứa 2 file đề bài gốc do giảng viên cung cấp cho đồ án môn DBI202. File này gộp nội dung của cả hai file thành một bản tóm tắt tiếng Việt duy nhất, để cả nhóm không cần mở lại `.docx` mỗi lần tra cứu.

## So sánh 2 bản đề bài

- **Assignment1.docx** viết bằng **tiếng Anh**, tập trung vào **quy trình làm bài và yêu cầu nộp bài**: các bước thực hiện (chọn hệ thống → ER → quan hệ → 3NF → cài đặt), và **quy định rất cụ thể** về số lượng tối thiểu (≥3 ràng buộc, ≥5 dòng/bảng, ≥1 câu cho mỗi loại query...), tên file `.sql` cần tách riêng (`createDB.sql`, `constraints.sql`, `insert.sql`, `queries.sql`, `transaction.sql`, `trigger.sql`, `procedure.sql`), và cách đặt tên file zip khi nộp.
- **Assignment2.docx** viết bằng **tiếng Việt**, có thể xem là bản **bổ sung/làm rõ** cho Assignment1 chứ không phải bản dịch — tập trung vào **cấu trúc nội dung báo cáo** (đặt vấn đề → mô hình ER → mô hình quan hệ → đặc tả dữ liệu → ràng buộc → cài đặt → query → trigger → procedure/function → kết luận).
  - **Chi tiết hơn** ở phần **data dictionary**: có kèm ví dụ cụ thể (data element "delivery instruction", "delivery location", "delivery time window" với các cột Description/Composition/Length/Values) — phần này Assignment1 không có.
  - **Ngắn gọn/tổng quát hơn** ở phần yêu cầu kỹ thuật: không nêu số lượng tối thiểu cụ thể (không nói rõ "≥3 ràng buộc" hay "≥5 dòng/bảng" như Assignment1).
  - **Khác biệt về cách tổ chức file**: Assignment2 gộp toàn bộ script vào **một file `script.sql` duy nhất**, trong khi Assignment1 yêu cầu **tách riêng thành nhiều file** theo từng loại yêu cầu.
- **Điểm chung:** cả 2 file đều dùng chung bảng phân nhóm/tiêu chí review ("Lắng nghe & phản biện") và cùng gợi ý database tham khảo là **AdventureWorks**.

> Nhóm áp dụng theo hướng kết hợp: tách file theo Assignment1 (dễ phân công theo từng thành viên) nhưng vẫn bổ sung phần data dictionary chi tiết theo yêu cầu của Assignment2 vào báo cáo.

## Nội dung yêu cầu hợp nhất

### 1. Chọn hệ thống / nghiệp vụ

Nhóm 7 chọn chủ đề **video game sales**.

> Ví dụ (sẽ làm): mô tả ngắn gọn hệ thống thống kê doanh số bán game theo khu vực, nền tảng, thể loại và nhà phát hành, dựa trên dataset video game sales.

### 2. Phát biểu bài toán & mô tả nghiệp vụ

- Mô tả chi tiết cách hệ thống hoạt động: các entity và chức năng của chúng, thông tin cần cho mỗi entity, luồng công việc (workflow).
- Liệt kê từng nghiệp vụ cụ thể của hệ thống.

> Ví dụ (sẽ làm): liệt kê các nghiệp vụ như "thêm game mới", "gán game cho nhà phát hành/nền tảng", "ghi nhận doanh số theo khu vực", "thống kê doanh số theo thể loại/nền tảng/khu vực".

### 3. Mô hình ER

Xây dựng mô hình Entity/Relationship (ER) cho hệ thống, vẽ đúng ký hiệu chuẩn.

> Ví dụ (output sẽ trông như): một sơ đồ ER gồm các entity `game`, `genre`, `publisher`, `platform`, `region`, với các quan hệ 1-n / n-n tương ứng (vd: một game thuộc 1 genre, một game có thể được nhiều publisher phát hành trên nhiều platform, mỗi cặp game-platform có doanh số theo từng region) — vẽ bằng draw.io/dbdiagram.io rồi chèn ảnh vào báo cáo.

### 4. Mô hình quan hệ & chuẩn hoá

Chuyển mô hình ER sang mô hình quan hệ (relational model) với các quan hệ và phụ thuộc hàm tương ứng, chuẩn hoá về **3NF**.

> Ví dụ (sẽ làm): liệt kê các quan hệ `game(id, genre_id, game_name)`, `game_publisher(id, game_id, publisher_id)`, `game_platform(id, game_publisher_id, platform_id, release_year)`, `region_sales(region_id, game_platform_id, num_sales)` kèm phụ thuộc hàm và giải thích vì sao đã đạt 3NF (không có phụ thuộc bắc cầu).

### 5. Đặc tả yêu cầu dữ liệu (Data dictionary)

Mô tả từng thuộc tính dữ liệu quan trọng, gồm các cột: tên thuộc tính (Data Element), mô tả (Description), thành phần/kiểu dữ liệu (Composition or Data Type), độ dài (Length), giá trị hợp lệ (Values).

Ví dụ minh hoạ từ đề bài (Assignment2):

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| delivery instruction | nơi và người nhận khi một suất ăn cần được giao, nếu không lấy trực tiếp tại căn tin | patron name + patron phone number + meal date + delivery location + delivery time window | | |
| delivery location | toà nhà và phòng cần giao suất ăn đã đặt | alphanumeric | 50 | cho phép dấu gạch ngang và dấu phẩy |
| delivery time window | thời điểm bắt đầu của khoảng 15 phút trong ngày đặt ăn để giao suất ăn | time | hh:mm | giờ địa phương; hh = 0-23, mm = 00/15/30/45 |

> Ví dụ (sẽ làm): áp dụng mẫu bảng trên cho thuộc tính `num_sales` (region_sales) — Description: "doanh số bán (triệu bản) của một game trên một nền tảng tại một khu vực"; Composition/Data Type: decimal; Length: (5,2); Values: >= 0.

### 6. Danh sách ràng buộc dữ liệu

Liệt kê các ràng buộc dữ liệu của hệ thống.

> Ví dụ (sẽ làm): `num_sales >= 0`, `release_year` nằm trong khoảng hợp lý (1970–2100), `game_name` không trùng lặp, mỗi `game_platform` phải gắn với đúng 1 `game_publisher` đã tồn tại.

### 7. Cài đặt vật lý trên SQL Server

Tách thành các file `.sql` riêng theo từng người phụ trách (xem [`sql/`](../sql/) và bảng phân công trong [README.md](../README.md)):

- `createDB.sql` — tạo database và các bảng bằng câu lệnh SQL.
- `constraints.sql` — tối thiểu 3 ràng buộc bằng `ALTER TABLE`.
- `insert.sql` — dữ liệu mẫu, tối thiểu 5 dòng/bảng.
- Cài đặt index nếu cần cho hiệu năng truy vấn.

### 8. Truy vấn

Viết tối thiểu 1 câu truy vấn cho mỗi loại sau, lưu trong `queries.sql`, kèm câu trả lời/kết quả tương ứng:

- Query dùng inner join.
- Query dùng outer join.
- Dùng subquery trong `WHERE`.
- Dùng subquery trong `FROM`.
- Query dùng `GROUP BY` và hàm aggregate.

> Ví dụ (output sẽ trông như): kết quả câu query "tổng doanh số theo thể loại" trả về bảng 2 cột `genre_name`, `total_sales`, sắp xếp giảm dần — chụp màn hình kết quả trong SSMS và chèn vào báo cáo.

### 9. Transaction

Viết tối thiểu 1 transaction có dùng `ROLLBACK`, lưu trong `transaction.sql`.

> Ví dụ (sẽ làm): transaction thêm một game mới kèm publisher, platform và doanh số ban đầu trong cùng 1 giao dịch — nếu bước ghi doanh số lỗi thì rollback toàn bộ, không để game "mồ côi" dữ liệu.

### 10. Trigger

Viết tối thiểu 1 trigger để cài đặt ràng buộc phức tạp, lưu trong `trigger.sql`.

> Ví dụ (sẽ làm): trigger chặn insert/update `region_sales` khi `num_sales` âm, hoặc trigger tự động ghi log mỗi khi doanh số một game thay đổi.

### 11. Procedure / Function

Viết tối thiểu 1 stored procedure (và hàm nếu cần) để giải quyết nghiệp vụ, lưu trong `procedure.sql`.

> Ví dụ (sẽ làm): procedure `sp_GetTopGamesByRegion(@RegionId, @TopN)` trả về top N game bán chạy nhất tại một khu vực.

### 12. Kết luận

Kết luận, hướng phát triển của đồ án.

> Ví dụ (sẽ làm): tóm tắt các nghiệp vụ đã cài đặt, hạn chế hiện tại (vd: chưa có dữ liệu theo thời gian thực), hướng phát triển (vd: thêm bảng đánh giá/review game, tích hợp AI để gợi ý game theo xu hướng khu vực).

## Nộp bài

- Đóng gói toàn bộ file thành `DBI202Project_CC_NNN_RN.zip` (CC = lớp, NNN = họ tên đầy đủ, RN = mã số/roll number — theo nguyên văn đề bài: *"CC is your class, NNN is your fullname and RN is your roll number"*).
- Gồm: báo cáo cuối cùng dạng `.docx`/`.pdf` mô tả chi tiết toàn bộ các bước đã làm, và toàn bộ file `.sql` của project.
- Database tham khảo: **AdventureWorks** (Microsoft SQL Server sample DB).
- Tiêu chí review: **Lắng nghe & phản biện**.

## Ghi chú đối chiếu với repo hiện tại

- Nhóm tách script theo cấu trúc nhiều file trong thư mục [`sql/`](../sql/), chia theo từng thư mục con tương ứng người phụ trách (`sql/hoang/`, `sql/trung/`, `sql/vi/`, `sql/quantl3/`) thay vì gộp vào 1 file `script.sql`, để dễ phân công theo từng thành viên — cần nêu rõ lý do này trong báo cáo.
- Phần data dictionary và mô hình ER/quan hệ chưa có file riêng trong repo — cần bổ sung vào báo cáo [`material/Report.docx`](../material/Report.docx).
