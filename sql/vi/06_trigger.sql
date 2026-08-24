-- ============================================
-- File: trigger.sql
-- Phụ trách: Vi (IS)
-- Mục đích: >= 1 trigger để cài đặt ràng buộc phức tạp
-- ============================================

USE [Group7];
GO

/* =========================================================
   Requirement 9: Trigger
   Audit INSERT / UPDATE / DELETE actions on region_sales.
   ========================================================= */
IF OBJECT_ID('dbo.region_sales_audit', 'U') IS NOT NULL
    DROP TABLE dbo.region_sales_audit;
GO

CREATE TABLE dbo.region_sales_audit
(
    audit_id INT IDENTITY(1,1) PRIMARY KEY,
    action_type VARCHAR(10) NOT NULL,
    region_id INT NULL,
    game_platform_id INT NULL,
    old_num_sales DECIMAL(5,2) NULL,
    new_num_sales DECIMAL(5,2) NULL,
    changed_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO

IF OBJECT_ID('dbo.trg_region_sales_audit', 'TR') IS NOT NULL
    DROP TRIGGER dbo.trg_region_sales_audit;
GO

CREATE TRIGGER dbo.trg_region_sales_audit
ON dbo.region_sales
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    /* INSERT */
    IF EXISTS (SELECT 1 FROM inserted)
       AND NOT EXISTS (SELECT 1 FROM deleted)
    BEGIN
        INSERT INTO dbo.region_sales_audit
            (action_type, region_id, game_platform_id,
             old_num_sales, new_num_sales)
        SELECT
            'INSERT',
            region_id,
            game_platform_id,
            NULL,
            num_sales
        FROM inserted;
    END;

    /* DELETE */
    IF EXISTS (SELECT 1 FROM deleted)
       AND NOT EXISTS (SELECT 1 FROM inserted)
    BEGIN
        INSERT INTO dbo.region_sales_audit
            (action_type, region_id, game_platform_id,
             old_num_sales, new_num_sales)
        SELECT
            'DELETE',
            region_id,
            game_platform_id,
            num_sales,
            NULL
        FROM deleted;
    END;

    /* UPDATE: record old and new values separately.
       This also works with the duplicate pairs existing
       in the supplied dataset. */
    IF EXISTS (SELECT 1 FROM inserted)
       AND EXISTS (SELECT 1 FROM deleted)
    BEGIN
        INSERT INTO dbo.region_sales_audit
            (action_type, region_id, game_platform_id,
             old_num_sales, new_num_sales)
        SELECT
            'UPD_OLD',
            region_id,
            game_platform_id,
            num_sales,
            NULL
        FROM deleted;

        INSERT INTO dbo.region_sales_audit
            (action_type, region_id, game_platform_id,
             old_num_sales, new_num_sales)
        SELECT
            'UPD_NEW',
            region_id,
            game_platform_id,
            NULL,
            num_sales
        FROM inserted;
    END;
END;
GO

-- Cau lenh kiem tra trigger trg_region_sales_audit
INSERT INTO region_sales (region_id, game_platform_id, num_sales) VALUES (1, 1, 2.50);
SELECT TOP 5 * FROM region_sales_audit ORDER BY audit_id DESC;
-- -> sinh 1 dong audit action_type = 'INSERT'

UPDATE region_sales SET num_sales = 3.00 WHERE region_id = 1 AND game_platform_id = 1;
SELECT TOP 5 * FROM region_sales_audit ORDER BY audit_id DESC;
-- -> sinh 2 dong audit action_type = 'UPD_OLD' va 'UPD_NEW'

DELETE FROM region_sales WHERE region_id = 1 AND game_platform_id = 1;
SELECT TOP 5 * FROM region_sales_audit ORDER BY audit_id DESC;
-- -> sinh 1 dong audit action_type = 'DELETE'
