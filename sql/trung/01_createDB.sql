-- ============================================
-- File: createDB.sql
-- Phụ trách: Trung (SE)
-- Contributor: quantl3@fpt.edu.vn (nội dung tách/tham khảo từ ../quantl3/G7_Dbscript.sql)
-- Mục đích: Tạo database Group7 và các bảng theo mô hình quan hệ (đã chuẩn hoá 3NF)
-- Đã đối chiếu với mô hình ER cuối cùng (xem erd-dictionary/ERD.md)
-- ============================================

USE [master]
GO
IF EXISTS (SELECT name FROM master.sys.databases WHERE name = N'Group7')
    DROP DATABASE [Group7]
GO
CREATE DATABASE [Group7]
GO
USE [Group7]
GO

-- ========== BẢNG LOOKUP (không phụ thuộc bảng khác) ==========

CREATE TABLE platform (
    id INT PRIMARY KEY,
    platform_name VARCHAR(50) NOT NULL
);

CREATE TABLE genre (
    id INT PRIMARY KEY,
    genre_name VARCHAR(50) NOT NULL
);

CREATE TABLE publisher (
    id INT PRIMARY KEY,
    publisher_name VARCHAR(100) NOT NULL
);

CREATE TABLE region (
    id INT PRIMARY KEY,
    region_name VARCHAR(50) NOT NULL
);

-- ========== BẢNG CHÍNH ==========

CREATE TABLE game (
    id INT PRIMARY KEY,
    genre_id INT NOT NULL,
    game_name VARCHAR(200) NOT NULL,
    CONSTRAINT fk_game_genre FOREIGN KEY (genre_id) REFERENCES genre(id)
);

CREATE TABLE game_publisher (
    id INT PRIMARY KEY,
    game_id INT NOT NULL,
    publisher_id INT NOT NULL,
    CONSTRAINT fk_gp_game FOREIGN KEY (game_id) REFERENCES game(id),
    CONSTRAINT fk_gp_publisher FOREIGN KEY (publisher_id) REFERENCES publisher(id)
);

CREATE TABLE game_platform (
    id INT PRIMARY KEY,
    game_publisher_id INT NOT NULL,
    platform_id INT NOT NULL,
    release_year INT,
    CONSTRAINT fk_gpl_gamepublisher FOREIGN KEY (game_publisher_id) REFERENCES game_publisher(id),
    CONSTRAINT fk_gpl_platform FOREIGN KEY (platform_id) REFERENCES platform(id)
);

CREATE TABLE region_sales (
    region_id INT NOT NULL,
    game_platform_id INT NOT NULL,
    num_sales DECIMAL(5, 2),
    CONSTRAINT pk_region_sales PRIMARY KEY (region_id, game_platform_id),
    CONSTRAINT fk_rs_region FOREIGN KEY (region_id) REFERENCES region(id),
    CONSTRAINT fk_rs_gameplatform FOREIGN KEY (game_platform_id) REFERENCES game_platform(id)
);
GO

-- ========== INDEX cho hiệu năng truy vấn ==========
-- Tạo non-clustered index trên các cột FK thường dùng trong JOIN/WHERE
-- để tăng tốc các câu query aggregate, join nhiều bảng.

CREATE NONCLUSTERED INDEX ix_game_genre_id
    ON game (genre_id);

CREATE NONCLUSTERED INDEX ix_game_publisher_game_id
    ON game_publisher (game_id);

CREATE NONCLUSTERED INDEX ix_game_publisher_publisher_id
    ON game_publisher (publisher_id);

CREATE NONCLUSTERED INDEX ix_game_platform_game_publisher_id
    ON game_platform (game_publisher_id);

CREATE NONCLUSTERED INDEX ix_game_platform_platform_id
    ON game_platform (platform_id);

CREATE NONCLUSTERED INDEX ix_region_sales_game_platform_id
    ON region_sales (game_platform_id);

-- Index hỗ trợ tìm kiếm game theo tên (dùng trong web demo search)
CREATE NONCLUSTERED INDEX ix_game_name
    ON game (game_name);

-- Index hỗ trợ lọc game_platform theo năm phát hành
CREATE NONCLUSTERED INDEX ix_game_platform_release_year
    ON game_platform (release_year);
GO
