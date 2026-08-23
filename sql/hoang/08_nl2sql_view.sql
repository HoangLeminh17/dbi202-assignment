-- ============================================
-- File: 08_nl2sql_view.sql
-- Phụ trách: Hoàng (AI)
-- Mục đích: semantic layer / view phẳng cho NL2SQL Agent (ai/nl2sql/) -
-- gộp sẵn các JOIN qua 2 bảng trung gian (game_publisher, game_platform) để:
--   1. Giảm khả năng LLM sinh sai JOIN.
--   2. Là nơi "whitelist" cột được phép truy vấn (che id kỹ thuật không cần thiết).
-- ============================================

USE [Group7]
GO

CREATE OR ALTER VIEW vw_game_sales_full AS
SELECT
    g.id           AS game_id,
    g.game_name,
    gr.genre_name,
    p.publisher_name,
    pl.platform_name,
    gpl.release_year,
    r.region_name,
    rs.num_sales
FROM region_sales rs
JOIN game_platform gpl   ON gpl.id = rs.game_platform_id
JOIN game_publisher gp   ON gp.id = gpl.game_publisher_id
JOIN game g               ON g.id = gp.game_id
JOIN genre gr              ON gr.id = g.genre_id
JOIN publisher p           ON p.id = gp.publisher_id
JOIN platform pl           ON pl.id = gpl.platform_id
JOIN region r               ON r.id = rs.region_id;
GO

-- NL2SQL Agent (xem ai/nl2sql/sql_validator.py) chỉ được whitelist SELECT trên
-- vw_game_sales_full, không truy vấn trực tiếp 8 bảng gốc.
