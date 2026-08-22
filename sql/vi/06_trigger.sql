-- ============================================
-- File: trigger.sql
-- Phụ trách: Vi (IS)
-- Mục đích: >= 1 trigger để cài đặt ràng buộc phức tạp
-- ============================================

USE [Group7]
GO

CREATE OR ALTER TRIGGER trg_region_sales_no_negative
ON region_sales
INSTEAD OF INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1 FROM inserted WHERE num_sales < 0)
    BEGIN
        RAISERROR('num_sales khong duoc am', 16, 1);
        RETURN;
    END

    -- TODO (Vi): viết lại logic insert/update thực tế cho instead of trigger này
    -- (ví dụ: MERGE vào region_sales từ inserted khi dữ liệu hợp lệ)
END;
GO

-- TODO (Vi): bổ sung thêm trigger audit/log nếu cần (vd: log thay đổi giá/doanh số)
