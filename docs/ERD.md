# Sơ đồ ER (Entity/Relationship) - Group7 Video Game Sales

Phụ trách: Hoàng (AI)

Sơ đồ dưới đây mô tả mô hình ER tương ứng với schema đã cài đặt trong [`sql/quantl3/G7_Dbscript.sql`](../sql/quantl3/G7_Dbscript.sql), vẽ theo **ký hiệu Chen** (entity = hình chữ nhật, relationship = hình thoi, attribute = hình oval, khoá chính gạch chân) - đúng chuẩn được yêu cầu trong đề bài, thay vì ký hiệu crow's foot của Mermaid.

File nguồn (vector, chỉnh sửa được): [`docs/ERD.svg`](ERD.svg) - mở trực tiếp bằng trình duyệt để xem/phóng to, hoặc bằng Inkscape/Illustrator nếu cần sửa. File ảnh xuất sẵn để chèn vào báo cáo: [`docs/ERD.jpg`](ERD.jpg).

![ERD Group7 Video Game Sales](ERD.jpg)

Khi đưa vào `material/Report.docx`: chèn trực tiếp file `docs/ERD.jpg` vào Word (Insert → Pictures). Nếu cần sửa nội dung sơ đồ, sửa `docs/ERD.svg` rồi xuất lại JPG.

## Giải thích các entity và quan hệ

| Entity | Vai trò | Quan hệ |
|---|---|---|
| `Genre` | Thể loại game (Action, RPG, Sports...) | 1 Genre - N Game (quan hệ `Classifies`) |
| `Game` | Một tựa game cụ thể | N Game - 1 Genre; 1 Game có thể có N bản ghi phát hành (`Game_Publisher`) qua quan hệ `Published_as` |
| `Publisher` | Nhà phát hành game | 1 Publisher - N Game_Publisher (quan hệ `Publishes`) |
| `Game_Publisher` | Thực thể trung gian: 1 Game do 1 Publisher phát hành | N-1 với Game (`Published_as`), N-1 với Publisher (`Publishes`); 1 Game_Publisher có thể có N bản phát hành theo nền tảng (`Game_Platform`) qua quan hệ `Released_on` |
| `Platform` | Nền tảng chơi game (PS4, Xbox, PC...) | 1 Platform - N Game_Platform (quan hệ `Hosts`) |
| `Game_Platform` | Thực thể trung gian: 1 bản phát hành (Game_Publisher) trên 1 Platform, kèm năm phát hành | N-1 với Game_Publisher (`Released_on`), N-1 với Platform (`Hosts`); N-N với Region qua quan hệ `Sold_in` |
| `Region` | Khu vực địa lý (NA, EU, JP, Other...) | N-N với Game_Platform qua quan hệ `Sold_in` |
| `Sold_in` | Quan hệ N-N giữa Game_Platform và Region, mang thuộc tính `num_sales` (tương ứng bảng `region_sales` trong mô hình quan hệ) | N Game_Platform - N Region |

## Lý do thiết kế 2 bảng trung gian (`game_publisher`, `game_platform`)

- Một game có thể được nhiều publisher phát hành ở các khu vực/thời điểm khác nhau (n-n giữa `Game` và `Publisher`) → tách thành thực thể trung gian `Game_Publisher`.
- Một bản phát hành (`Game_Publisher`) có thể ra mắt trên nhiều platform vào các năm khác nhau (n-n giữa `Game_Publisher` và `Platform`) → tách thành thực thể trung gian `Game_Platform`.
- Doanh số không gắn thẳng vào `Game`, mà gắn với từng cặp (`Game_Platform`, `Region`) cụ thể qua quan hệ N-N `Sold_in` (mang thuộc tính `num_sales`), vì cùng 1 game trên các platform/publisher khác nhau có doanh số khác nhau ở từng khu vực.
- Khi chuyển sang mô hình quan hệ (relational model), 2 thực thể trung gian `Game_Publisher`/`Game_Platform` trở thành bảng riêng (có khoá chính `id`), còn quan hệ N-N `Sold_in` trở thành bảng `region_sales` với khoá chính phức hợp `(region_id, game_platform_id)` - xem chi tiết trong `sql/quantl3/G7_Dbscript.sql`.

> Xem đặc tả chi tiết từng thuộc tính tại [`docs/DataDictionary.md`](DataDictionary.md).
