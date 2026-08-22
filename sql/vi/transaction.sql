-- ============================================
-- File: transaction.sql
-- Phụ trách: Vi (IS)
-- Mục đích: >= 1 transaction có sử dụng ROLLBACK
-- ============================================

USE [Group7]
GO

BEGIN TRANSACTION;

BEGIN TRY
    UPDATE region_sales
    SET num_sales = num_sales + 1
    WHERE region_id = 1;

    -- Giả lập lỗi để kiểm tra rollback (bỏ comment để test)
    -- RAISERROR('Loi gia lap', 16, 1);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    PRINT 'Transaction rolled back: ' + ERROR_MESSAGE();
END CATCH;
GO

-- TODO (Vi): thay bằng transaction gắn với nghiệp vụ thực tế
-- (vd: thêm game + game_publisher + game_platform + region_sales cùng lúc,
-- rollback nếu 1 bước thất bại)
