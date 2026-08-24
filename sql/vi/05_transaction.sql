-- ============================================
-- File: transaction.sql
-- Phụ trách: Vi (IS)
-- Mục đích: >= 1 transaction có sử dụng ROLLBACK
-- ============================================

USE [Group7];
GO

/* =========================================================
   Requirement 8: Transaction
   Insert one new game, publisher relation, platform relation,
   and four regional sales records as one atomic transaction.
   ========================================================= */
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @GameID INT =
        (SELECT ISNULL(MAX(id), 0) + 1 FROM dbo.game);
    DECLARE @GamePublisherID INT =
        (SELECT ISNULL(MAX(id), 0) + 1 FROM dbo.game_publisher);
    DECLARE @GamePlatformID INT =
        (SELECT ISNULL(MAX(id), 0) + 1 FROM dbo.game_platform);

    /* Use existing Nintendo publisher and Wii platform */
    INSERT INTO dbo.game (id, genre_id, game_name)
    VALUES (@GameID, 1, 'DBI202 Assignment Demo Game');

    INSERT INTO dbo.game_publisher (id, game_id, publisher_id)
    VALUES (@GamePublisherID, @GameID, 369);

    INSERT INTO dbo.game_platform
        (id, game_publisher_id, platform_id, release_year)
    VALUES
        (@GamePlatformID, @GamePublisherID, 1, 2026);

    INSERT INTO dbo.region_sales
        (region_id, game_platform_id, num_sales)
    VALUES
        (1, @GamePlatformID, 1.20),
        (2, @GamePlatformID, 0.80),
        (3, @GamePlatformID, 0.50),
        (4, @GamePlatformID, 0.20);

    COMMIT TRANSACTION;
    PRINT 'Transaction committed successfully.';
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
