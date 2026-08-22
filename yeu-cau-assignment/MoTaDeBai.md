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

Làm việc theo nhóm, chọn một hệ thống/nghiệp vụ thực tế để nghiên cứu (có thể dựa trên dữ liệu/thông tin của một website nhỏ nào đó). Nhóm 7 chọn chủ đề **video game sales**.

### 2. Phát biểu bài toán & mô tả nghiệp vụ

- Mô tả chi tiết cách hệ thống hoạt động: các entity và chức năng của chúng, thông tin cần cho mỗi entity, luồng công việc (workflow).
- Liệt kê từng nghiệp vụ cụ thể của hệ thống.

### 3. Mô hình ER

Xây dựng mô hình Entity/Relationship (ER) cho hệ thống, vẽ đúng ký hiệu chuẩn.

### 4. Mô hình quan hệ & chuẩn hoá

Chuyển mô hình ER sang mô hình quan hệ (relational model) với các quan hệ và phụ thuộc hàm tương ứng, chuẩn hoá về **3NF**.

### 5. Đặc tả yêu cầu dữ liệu (Data dictionary)

Mô tả từng thuộc tính dữ liệu quan trọng, gồm các cột: tên thuộc tính (Data Element), mô tả (Description), thành phần/kiểu dữ liệu (Composition or Data Type), độ dài (Length), giá trị hợp lệ (Values).

Ví dụ minh hoạ từ đề bài (Assignment2):

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| delivery instruction | nơi và người nhận khi một suất ăn cần được giao, nếu không lấy trực tiếp tại căn tin | patron name + patron phone number + meal date + delivery location + delivery time window | | |
| delivery location | toà nhà và phòng cần giao suất ăn đã đặt | alphanumeric | 50 | cho phép dấu gạch ngang và dấu phẩy |
| delivery time window | thời điểm bắt đầu của khoảng 15 phút trong ngày đặt ăn để giao suất ăn | time | hh:mm | giờ địa phương; hh = 0-23, mm = 00/15/30/45 |

### 6. Danh sách ràng buộc dữ liệu

Liệt kê các ràng buộc dữ liệu của hệ thống.

### 7. Cài đặt vật lý trên SQL Server

Tách thành các file `.sql` riêng (theo Assignment1; Assignment2 chấp nhận gộp chung vào `script.sql`):

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

### 9. Transaction

Viết tối thiểu 1 transaction có dùng `ROLLBACK`, lưu trong `transaction.sql`.

### 10. Trigger

Viết tối thiểu 1 trigger để cài đặt ràng buộc phức tạp, lưu trong `trigger.sql`.

### 11. Procedure / Function

Viết tối thiểu 1 stored procedure (và hàm nếu cần) để giải quyết nghiệp vụ, lưu trong `procedure.sql`.

### 12. Kết luận

Kết luận, hướng phát triển của đồ án.

## Nộp bài

- Đóng gói toàn bộ file thành `DBI202Project_CC_NNN_RN.zip` (CC = lớp, NNN = họ tên đầy đủ, RN = mã số).
- Gồm: báo cáo cuối cùng dạng `.docx`/`.pdf` mô tả chi tiết toàn bộ các bước đã làm, và toàn bộ file `.sql` của project.
- Database tham khảo: **AdventureWorks** (Microsoft SQL Server sample DB).
- Tiêu chí review: **Lắng nghe & phản biện**.

## Ghi chú đối chiếu với repo hiện tại

- Nhóm tách script theo cấu trúc nhiều file trong thư mục [`sql/`](../sql/), chia theo từng thư mục con tương ứng người phụ trách (`sql/hoang/`, `sql/trung/`, `sql/vi/`, `sql/quantl3/`) thay vì gộp vào 1 file `script.sql`, để dễ phân công theo từng thành viên — cần nêu rõ lý do này trong báo cáo.
- Phần data dictionary và mô hình ER/quan hệ chưa có file riêng trong repo — cần bổ sung vào báo cáo [`material/Report.docx`](../material/Report.docx).
