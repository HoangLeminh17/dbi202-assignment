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
-- ============================================

USE [Group7]
GO

-- region_sales: bảng lớn nhất, la trung tam moi JOIN (game_platform_id, region_id)
CREATE INDEX ix_region_sales_game_platform_id ON region_sales (game_platform_id);
GO
CREATE INDEX ix_region_sales_region_id ON region_sales (region_id);
GO

-- FK con lai chua co index ho tro JOIN
CREATE INDEX ix_game_genre_id ON game (genre_id);
GO
CREATE INDEX ix_game_publisher_game_id ON game_publisher (game_id);
GO
CREATE INDEX ix_game_publisher_publisher_id ON game_publisher (publisher_id);
GO
CREATE INDEX ix_game_platform_game_publisher_id ON game_platform (game_publisher_id);
GO
CREATE INDEX ix_game_platform_platform_id ON game_platform (platform_id);
GO
