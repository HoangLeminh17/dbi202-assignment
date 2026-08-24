-- ============================================
-- File: constraints.sql
-- Phụ trách: Vi (IS)
-- Mục đích: >= 3 ràng buộc dữ liệu bằng ALTER TABLE
-- ============================================

USE [Group7]
GO

-- 6.1. Tên Platform không được để trống
ALTER TABLE dbo.platform
ADD CONSTRAINT CK_platform_name_not_empty
CHECK (LEN(LTRIM(RTRIM(platform_name))) > 0);
GO

-- 6.2. Tên Genre không được để trống
ALTER TABLE dbo.genre
ADD CONSTRAINT CK_genre_name_not_empty
CHECK (LEN(LTRIM(RTRIM(genre_name))) > 0);
GO

-- 6.3. Doanh số không được âm
ALTER TABLE dbo.region_sales
ADD CONSTRAINT CK_region_sales_non_negative
CHECK (num_sales >= 0);
GO

-- 6.4. Năm phát hành phải hợp lệ
ALTER TABLE dbo.game_platform
ADD CONSTRAINT CK_game_platform_release_year
CHECK (
    release_year IS NULL
    OR release_year BETWEEN 1980 AND 2026
);
GO
