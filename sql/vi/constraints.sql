-- ============================================
-- File: constraints.sql
-- Phụ trách: Vi (IS)
-- Mục đích: >= 3 ràng buộc dữ liệu bằng ALTER TABLE
-- ============================================

USE [Group7]
GO

ALTER TABLE region_sales
ADD CONSTRAINT ck_region_sales_nonnegative CHECK (num_sales >= 0);
GO

ALTER TABLE game
ADD CONSTRAINT uq_game_name UNIQUE (game_name);
GO

ALTER TABLE game_platform
ADD CONSTRAINT ck_release_year CHECK (release_year BETWEEN 1970 AND 2100);
GO

-- TODO (Vi): bổ sung thêm ràng buộc liên quan toàn vẹn dữ liệu / bảo mật nếu cần
-- (vd: DEFAULT, CHECK cho tên không rỗng, ...)
