-- ============================================
-- File: procedure.sql
-- Phụ trách: Trung (SE)
-- Mục đích: >= 1 stored procedure để giải quyết nghiệp vụ
-- ============================================

USE [Group7]
GO

CREATE OR ALTER PROCEDURE sp_GetTopGamesByRegion
    @RegionId INT,
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@TopN) g.game_name, rs.num_sales
    FROM region_sales rs
    JOIN game_platform gpl ON gpl.id = rs.game_platform_id
    JOIN game_publisher gp ON gp.id = gpl.game_publisher_id
    JOIN game g ON g.id = gp.game_id
    WHERE rs.region_id = @RegionId
    ORDER BY rs.num_sales DESC;
END;
GO

-- TODO (Trung): bổ sung thêm procedure/function khác nếu nghiệp vụ cần
-- (vd: sp thêm game mới kèm publisher/platform/sales trong 1 lần gọi)
