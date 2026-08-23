-- ============================================
-- File: 10_readonly_login.sql
-- Phụ trách: Hoàng (AI)
-- Mục đích: DB-layer defense-in-depth cho NL2SQL Agent - tạo 1 database user
-- CHỈ có quyền SELECT trên view vw_game_sales_full, không có quyền gì trên 8
-- bảng gốc. Hiện tại agent chỉ được chặn bởi app-layer (sql_validator.py
-- whitelist bảng + guardrails.py) - nếu app-layer có lỗ hổng bypass nào đó,
-- lớp DB này vẫn chặn được vì user DB không hề có quyền đọc/ghi bảng gốc.
--
-- Dùng CREATE USER ... WITHOUT LOGIN (user không có mật khẩu/không tự đăng
-- nhập được) thay vì CREATE LOGIN - tránh phải bật SQL Server mixed-mode
-- authentication (cần đổi registry + restart service, ảnh hưởng cả instance).
-- Ứng dụng vẫn kết nối bằng Windows Authentication như cũ, nhưng trước khi
-- chạy SQL đã validate thì "đóng vai" user này qua EXECUTE AS USER (xem
-- db.py execute_select()) - DB thực sự chỉ cho SELECT trên view trong lúc đó.
--
-- Chạy: sqlcmd -S "localhost\SQLEXPRESS01" -d Group7 -E -C -i sql/hoang/10_readonly_login.sql
-- ============================================
USE [Group7]
GO
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'nl2sql_readonly')
BEGIN
    CREATE USER nl2sql_readonly WITHOUT LOGIN;
END
GO

-- Chỉ GRANT đúng 1 quyền SELECT trên view - không GRANT gì trên 8 bảng gốc,
-- mặc định user mới không có quyền gì (deny-by-default) nên không cần DENY tường minh.
GRANT SELECT ON dbo.vw_game_sales_full TO nl2sql_readonly;
GO
