# Đặc tả yêu cầu dữ liệu (Data Dictionary) - Group7 Video Game Sales

Phụ trách: Hoàng (AI)

Theo đúng format mẫu trong đề bài (xem [`yeu-cau-assignment/MoTaDeBai.md`](../yeu-cau-assignment/MoTaDeBai.md), mục 5): mỗi thuộc tính gồm Data Element, Description, Composition or Data Type, Length, Values. Đối chiếu với schema đã cài đặt tại [`sql/quantl3/G7_Dbscript.sql`](../sql/quantl3/G7_Dbscript.sql) và [`erd-dictionary/ERD.md`](ERD.md).

## Bảng `genre`

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| genre.id | Mã định danh duy nhất cho một thể loại game | int (Primary Key) | - | > 0, tự tăng |
| genre.genre_name | Tên thể loại game | varchar | 50 | vd: Action, Sports, Role-Playing |

## Bảng `platform`

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| platform.id | Mã định danh duy nhất cho một nền tảng chơi game | int (Primary Key) | - | > 0, tự tăng |
| platform.platform_name | Tên nền tảng (console/PC) | varchar | 50 | vd: PS4, XOne, PC, Wii |

## Bảng `publisher`

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| publisher.id | Mã định danh duy nhất cho một nhà phát hành | int (Primary Key) | - | > 0, tự tăng |
| publisher.publisher_name | Tên nhà phát hành game | varchar | 100 | không rỗng |

## Bảng `region`

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| region.id | Mã định danh duy nhất cho một khu vực địa lý | int (Primary Key) | - | > 0, tự tăng |
| region.region_name | Tên khu vực ghi nhận doanh số | varchar | 50 | vd: North America, Europe, Japan, Other |

## Bảng `game`

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| game.id | Mã định danh duy nhất cho một tựa game | int (Primary Key) | - | > 0, tự tăng |
| game.genre_id | Thể loại của game này | int (Foreign Key → genre.id) | - | phải tồn tại trong bảng genre |
| game.game_name | Tên tựa game | varchar | 200 | không rỗng |

## Bảng `game_publisher`

Bảng trung gian: một game được phát hành bởi một publisher.

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| game_publisher.id | Mã định danh duy nhất cho một bản ghi phát hành | int (Primary Key) | - | > 0, tự tăng |
| game_publisher.game_id | Game được phát hành | int (Foreign Key → game.id) | - | phải tồn tại trong bảng game |
| game_publisher.publisher_id | Nhà phát hành thực hiện phát hành | int (Foreign Key → publisher.id) | - | phải tồn tại trong bảng publisher |

## Bảng `game_platform`

Bảng trung gian: một bản phát hành (game_publisher) được phát hành trên một nền tảng, kèm năm phát hành.

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| game_platform.id | Mã định danh duy nhất cho một bản phát hành theo nền tảng | int (Primary Key) | - | > 0, tự tăng |
| game_platform.game_publisher_id | Bản ghi phát hành (game + publisher) tương ứng | int (Foreign Key → game_publisher.id) | - | phải tồn tại trong bảng game_publisher |
| game_platform.platform_id | Nền tảng phát hành | int (Foreign Key → platform.id) | - | phải tồn tại trong bảng platform |
| game_platform.release_year | Năm phát hành trên nền tảng này | int | - | 1970–2100 (đề xuất ràng buộc, xem `sql/vi/02_constraints.sql`) |

## Bảng `region_sales`

Doanh số bán của một `game_platform` cụ thể tại một `region` cụ thể. Khoá chính là cặp `(region_id, game_platform_id)`.

| Data Element | Description | Composition or Data Type | Length | Values |
|---|---|---|---|---|
| region_sales.region_id | Khu vực ghi nhận doanh số | int (Primary Key, Foreign Key → region.id) | - | phải tồn tại trong bảng region |
| region_sales.game_platform_id | Bản phát hành theo nền tảng được ghi nhận doanh số | int (Primary Key, Foreign Key → game_platform.id) | - | phải tồn tại trong bảng game_platform |
| region_sales.num_sales | Doanh số bán (triệu bản) của game_platform này tại region này | decimal | (5,2) | >= 0 (xem ràng buộc `ck_region_sales_nonnegative` trong `sql/vi/02_constraints.sql`) |
