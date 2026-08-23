-- ============================================
-- File: procedure.sql
-- Phụ trách: Trung (SE)
-- Mục đích: Stored procedure / function để giải quyết nghiệp vụ
-- ============================================

USE [Group7]
GO

-- ============================================
-- 1. sp_GetTopGamesByRegion
--    Trả về top N game bán chạy nhất tại một khu vực
-- ============================================
CREATE OR ALTER PROCEDURE sp_GetTopGamesByRegion
    @RegionId INT,
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@TopN)
        g.id AS game_id,
        g.game_name,
        gr.genre_name,
        p.publisher_name,
        pl.platform_name,
        rs.num_sales
    FROM region_sales rs
    JOIN game_platform gpl ON gpl.id = rs.game_platform_id
    JOIN game_publisher gp ON gp.id = gpl.game_publisher_id
    JOIN game g ON g.id = gp.game_id
    JOIN genre gr ON gr.id = g.genre_id
    JOIN publisher p ON p.id = gp.publisher_id
    JOIN platform pl ON pl.id = gpl.platform_id
    WHERE rs.region_id = @RegionId
    ORDER BY rs.num_sales DESC;
END;
GO

-- ============================================
-- 2. sp_AddNewGame
--    Thêm game mới kèm publisher, platform, sales
--    trong 1 giao dịch duy nhất (nếu 1 bước lỗi → rollback tất cả)
-- ============================================
CREATE OR ALTER PROCEDURE sp_AddNewGame
    @GameName VARCHAR(200),
    @GenreId INT,
    @PublisherId INT,
    @PlatformId INT,
    @ReleaseYear INT = NULL,
    @RegionId INT = NULL,
    @NumSales DECIMAL(5,2) = NULL,
    @NewGameId INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @GamePublisherId INT;
    DECLARE @GamePlatformId INT;

    BEGIN TRANSACTION;
    BEGIN TRY
        -- Tạo ID mới cho game (MAX + 1)
        SELECT @NewGameId = ISNULL(MAX(id), 0) + 1 FROM game;

        -- 1. Insert vào bảng game
        INSERT INTO game (id, genre_id, game_name)
        VALUES (@NewGameId, @GenreId, @GameName);

        -- 2. Insert vào bảng game_publisher
        SELECT @GamePublisherId = ISNULL(MAX(id), 0) + 1 FROM game_publisher;
        INSERT INTO game_publisher (id, game_id, publisher_id)
        VALUES (@GamePublisherId, @NewGameId, @PublisherId);

        -- 3. Insert vào bảng game_platform
        SELECT @GamePlatformId = ISNULL(MAX(id), 0) + 1 FROM game_platform;
        INSERT INTO game_platform (id, game_publisher_id, platform_id, release_year)
        VALUES (@GamePlatformId, @GamePublisherId, @PlatformId, @ReleaseYear);

        -- 4. Insert doanh số nếu có
        IF @RegionId IS NOT NULL AND @NumSales IS NOT NULL
        BEGIN
            INSERT INTO region_sales (region_id, game_platform_id, num_sales)
            VALUES (@RegionId, @GamePlatformId, @NumSales);
        END

        COMMIT TRANSACTION;
        PRINT 'Game moi da duoc them thanh cong: ' + @GameName;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        PRINT 'Loi khi them game - rollback: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END;
GO

-- ============================================
-- 3. sp_UpdateGameSales
--    Cập nhật doanh số game tại 1 region cụ thể
--    Nếu chưa có bản ghi → insert mới
-- ============================================
CREATE OR ALTER PROCEDURE sp_UpdateGameSales
    @GamePlatformId INT,
    @RegionId INT,
    @NewSales DECIMAL(5,2)
AS
BEGIN
    SET NOCOUNT ON;

    IF @NewSales < 0
    BEGIN
        RAISERROR('Doanh so khong duoc am', 16, 1);
        RETURN;
    END

    IF EXISTS (
        SELECT 1 FROM region_sales
        WHERE game_platform_id = @GamePlatformId AND region_id = @RegionId
    )
    BEGIN
        UPDATE region_sales
        SET num_sales = @NewSales
        WHERE game_platform_id = @GamePlatformId AND region_id = @RegionId;
        PRINT 'Da cap nhat doanh so.';
    END
    ELSE
    BEGIN
        INSERT INTO region_sales (region_id, game_platform_id, num_sales)
        VALUES (@RegionId, @GamePlatformId, @NewSales);
        PRINT 'Da them ban ghi doanh so moi.';
    END
END;
GO

-- ============================================
-- 4. sp_DeleteGame
--    Xoá game và toàn bộ dữ liệu liên quan
--    (region_sales → game_platform → game_publisher → game)
-- ============================================
CREATE OR ALTER PROCEDURE sp_DeleteGame
    @GameId INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM game WHERE id = @GameId)
    BEGIN
        RAISERROR('Khong tim thay game_id=%d', 16, 1, @GameId);
        RETURN;
    END

    BEGIN TRANSACTION;
    BEGIN TRY
        -- 1. Xoá region_sales của tất cả game_platform thuộc game này
        DELETE rs
        FROM region_sales rs
        JOIN game_platform gpl ON gpl.id = rs.game_platform_id
        JOIN game_publisher gp ON gp.id = gpl.game_publisher_id
        WHERE gp.game_id = @GameId;

        -- 2. Xoá game_platform
        DELETE gpl
        FROM game_platform gpl
        JOIN game_publisher gp ON gp.id = gpl.game_publisher_id
        WHERE gp.game_id = @GameId;

        -- 3. Xoá game_publisher
        DELETE FROM game_publisher WHERE game_id = @GameId;

        -- 4. Xoá game
        DELETE FROM game WHERE id = @GameId;

        COMMIT TRANSACTION;
        PRINT 'Da xoa game va du lieu lien quan.';
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        PRINT 'Loi khi xoa game - rollback: ' + ERROR_MESSAGE();
        THROW;
    END CATCH
END;
GO

-- ============================================
-- 5. sp_SearchGames
--    Tìm kiếm game theo tên (LIKE), có thể lọc theo genre/platform
--    Hỗ trợ web demo search
-- ============================================
CREATE OR ALTER PROCEDURE sp_SearchGames
    @Keyword VARCHAR(200) = NULL,
    @GenreId INT = NULL,
    @PlatformId INT = NULL,
    @TopN INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@TopN)
        g.id AS game_id,
        g.game_name,
        gr.genre_name,
        p.publisher_name,
        pl.platform_name,
        gpl.release_year,
        ISNULL(SUM(rs.num_sales), 0) AS total_sales
    FROM game g
    JOIN genre gr ON gr.id = g.genre_id
    LEFT JOIN game_publisher gp ON gp.game_id = g.id
    LEFT JOIN publisher p ON p.id = gp.publisher_id
    LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
    LEFT JOIN platform pl ON pl.id = gpl.platform_id
    LEFT JOIN region_sales rs ON rs.game_platform_id = gpl.id
    WHERE
        (@Keyword IS NULL OR g.game_name LIKE '%' + @Keyword + '%')
        AND (@GenreId IS NULL OR g.genre_id = @GenreId)
        AND (@PlatformId IS NULL OR gpl.platform_id = @PlatformId)
    GROUP BY g.id, g.game_name, gr.genre_name, p.publisher_name, pl.platform_name, gpl.release_year
    ORDER BY total_sales DESC;
END;
GO

-- ============================================
-- 6. fn_GetTotalSalesByGame (scalar function)
--    Trả về tổng doanh số toàn cầu của 1 game (tất cả platform, tất cả region)
-- ============================================
CREATE OR ALTER FUNCTION fn_GetTotalSalesByGame(@GameId INT)
RETURNS DECIMAL(10, 2)
AS
BEGIN
    DECLARE @Total DECIMAL(10, 2);

    SELECT @Total = ISNULL(SUM(rs.num_sales), 0)
    FROM region_sales rs
    JOIN game_platform gpl ON gpl.id = rs.game_platform_id
    JOIN game_publisher gp ON gp.id = gpl.game_publisher_id
    WHERE gp.game_id = @GameId;

    RETURN @Total;
END;
GO
