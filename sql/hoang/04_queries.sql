-- ============================================
-- File: queries.sql
-- Phụ trách: Hoàng (AI)
-- Mục đích: >= 1 câu cho mỗi loại: inner join, outer join,
-- subquery trong WHERE, subquery trong FROM, group by + aggregate
-- ============================================

USE [Group7]
GO

-- 1. INNER JOIN: liệt kê tên game, thể loại, nhà phát hành
SELECT g.game_name, gr.genre_name, p.publisher_name
FROM game g
INNER JOIN genre gr ON g.genre_id = gr.id
INNER JOIN game_publisher gp ON gp.game_id = g.id
INNER JOIN publisher p ON p.id = gp.publisher_id;

-- 2. OUTER JOIN: liệt kê tất cả game, kể cả game chưa có bản ghi doanh số
SELECT g.game_name, rs.num_sales
FROM game g
LEFT JOIN game_publisher gp ON gp.game_id = g.id
LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
LEFT JOIN region_sales rs ON rs.game_platform_id = gpl.id;

-- 3. Subquery trong WHERE: game có bản ghi doanh số cao hơn trung bình
SELECT DISTINCT g.game_name
FROM game g
JOIN game_publisher gp ON gp.game_id = g.id
JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
JOIN region_sales rs ON rs.game_platform_id = gpl.id
WHERE rs.num_sales > (SELECT AVG(num_sales) FROM region_sales);

-- 4. Subquery trong FROM: tổng doanh số theo thể loại
SELECT genre_name, total_sales
FROM (
    SELECT gr.genre_name, SUM(rs.num_sales) AS total_sales
    FROM genre gr
    JOIN game g ON g.genre_id = gr.id
    JOIN game_publisher gp ON gp.game_id = g.id
    JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
    JOIN region_sales rs ON rs.game_platform_id = gpl.id
    GROUP BY gr.genre_name
) AS genre_sales
ORDER BY total_sales DESC;

-- 5. GROUP BY + aggregate: số lượng game và tổng doanh số theo nhà phát hành
SELECT p.publisher_name, COUNT(DISTINCT g.id) AS so_luong_game, SUM(rs.num_sales) AS tong_doanh_so
FROM publisher p
JOIN game_publisher gp ON gp.publisher_id = p.id
JOIN game g ON g.id = gp.game_id
JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
JOIN region_sales rs ON rs.game_platform_id = gpl.id
GROUP BY p.publisher_name
ORDER BY tong_doanh_so DESC;

-- TODO (Hoàng): bổ sung thêm các câu query insight (có thể có AI hỗ trợ thiết kế)
