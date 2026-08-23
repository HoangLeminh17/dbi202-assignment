-- ============================================
-- File: 11_freshness_columns.sql
-- Phụ trách: Hoàng (AI)
-- Mục đích: Data Freshness THẬT cho NL2SQL Agent (/admin) - trước đó dùng
-- proxy (STATS_DATE, MAX(release_year)) vì region_sales không có cột thời
-- gian. STATS_DATE chỉ phản ánh lần optimizer tự update thống kê (ngưỡng
-- ~20% số dòng thay đổi mới trigger, hoặc nhảy giả khi ai đó chạy UPDATE
-- STATISTICS thủ công dù không ai ghi dữ liệu) - không đáng tin để khẳng
-- định "dữ liệu có mới không". Thêm audit column thật, tự động qua trigger,
-- để có con số chính xác 100% thay vì suy luận gián tiếp.
--
-- Backfill: NOT NULL DEFAULT GETDATE() nên toàn bộ dòng hiện có được gán
-- ngay thời điểm chạy script này (không có timestamp gốc thật để khôi phục).
--
-- Lưu ý: region_sales không có cột id (PK) - có 16 cặp (region_id,
-- game_platform_id) trùng lặp (xem 09_indexes.sql). Trigger dưới match theo
-- 2 cột này (EXISTS, không phải join 1-1 bằng khoá) nên với các dòng trùng
-- cặp khoá, cả cụm có thể cùng được cập nhật updated_at - chấp nhận được vì
-- get_data_freshness() chỉ đọc MAX(updated_at) tổng hợp, không cần chính xác
-- từng dòng.
--
-- Lưu ý 2: Vi có 1 trigger INSTEAD OF INSERT, UPDATE trên region_sales
-- (sql/vi/06_trigger.sql, hiện CHƯA chạy trên DB local này) - trigger AFTER
-- UPDATE dưới đây tương thích: nếu trigger INSTEAD OF của Vi thực thi 1 lệnh
-- UPDATE thật bên trong (theo đúng TODO của Vi), trigger AFTER này sẽ tự
-- được gọi lồng bên trong đó (nested trigger, mặc định bật sẵn ở SQL Server).
-- ============================================
USE [Group7]
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('region_sales') AND name = 'created_at')
BEGIN
    ALTER TABLE region_sales ADD created_at DATETIME NOT NULL DEFAULT GETDATE();
END
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('region_sales') AND name = 'updated_at')
BEGIN
    ALTER TABLE region_sales ADD updated_at DATETIME NOT NULL DEFAULT GETDATE();
END
GO

CREATE OR ALTER TRIGGER trg_region_sales_updated
ON region_sales
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE rs
    SET updated_at = GETDATE()
    FROM region_sales rs
    WHERE EXISTS (
        SELECT 1 FROM inserted i
        WHERE i.region_id = rs.region_id AND i.game_platform_id = rs.game_platform_id
    );
END;
GO
