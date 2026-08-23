-- ============================================
-- File: 09_indexes.sql
-- Phụ trách: Hoàng (AI)
-- Mục đích: index cho các cột FK dùng để JOIN trong vw_game_sales_full
-- (sql/hoang/08_nl2sql_view.sql) - tăng tốc truy vấn cho NL2SQL Agent.
--
-- Phát hiện khi debug: bảng region_sales (65,320 dòng, bảng trung tâm mọi
-- JOIN trong view) đang là HEAP không có index nào, kể cả khoá chính - mọi
-- JOIN qua bảng này đều phải quét toàn bộ. Các bảng còn lại đã có clustered
-- index từ PRIMARY KEY (id) nhưng chưa có index trên các cột FK dùng để nối
-- bảng (vd game.genre_id, game_publisher.game_id...).
--
-- Ghi chú: region_sales có 16 cặp (region_id, game_platform_id) trùng lặp
-- (kiểm tra: SELECT COUNT(*) - COUNT(DISTINCT ...) trả về 16) nên KHÔNG thể
-- thêm PRIMARY KEY/UNIQUE ở đây (sẽ lỗi vi phạm) - để nguyên, chỉ thêm index
-- thường phục vụ hiệu năng. Việc xử lý trùng lặp là quyết định dữ liệu/
-- nghiệp vụ (báo cáo phần ràng buộc), không tự ý xoá ở đây.
--
-- Idempotent (IF NOT EXISTS): Trung đã tự thêm y hệt 5/6 index này thẳng vào
-- sql/trung/01_createDB.sql (không biết có sql/hoang/09_indexes.sql) - nếu
-- chạy CREATE INDEX thẳng sẽ báo lỗi "index đã tồn tại" khi 01_createDB.sql
-- chạy trước (đúng thứ tự trong README). Kiểm tra tồn tại trước khi tạo để
-- script này chạy an toàn dù 01_createDB.sql đã tạo sẵn hay chưa.
-- ============================================

USE [Group7]
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_region_sales_game_platform_id' AND object_id = OBJECT_ID('region_sales'))
    CREATE INDEX ix_region_sales_game_platform_id ON region_sales (game_platform_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_region_sales_region_id' AND object_id = OBJECT_ID('region_sales'))
    CREATE INDEX ix_region_sales_region_id ON region_sales (region_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_game_genre_id' AND object_id = OBJECT_ID('game'))
    CREATE INDEX ix_game_genre_id ON game (genre_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_game_publisher_game_id' AND object_id = OBJECT_ID('game_publisher'))
    CREATE INDEX ix_game_publisher_game_id ON game_publisher (game_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_game_publisher_publisher_id' AND object_id = OBJECT_ID('game_publisher'))
    CREATE INDEX ix_game_publisher_publisher_id ON game_publisher (publisher_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_game_platform_game_publisher_id' AND object_id = OBJECT_ID('game_platform'))
    CREATE INDEX ix_game_platform_game_publisher_id ON game_platform (game_publisher_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_game_platform_platform_id' AND object_id = OBJECT_ID('game_platform'))
    CREATE INDEX ix_game_platform_platform_id ON game_platform (platform_id);
GO
