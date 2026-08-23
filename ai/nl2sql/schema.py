"""Schema-as-context (compact) + few-shot SQL examples cho NL2SQL Agent.

Chỉ đưa vw_game_sales_full (xem sql/hoang/08_nl2sql_view.sql) vào context thay vì
toàn bộ 8 bảng gốc, để LLM không phải tự suy JOIN qua 2 bảng trung gian
(game_publisher, game_platform) - nơi LLM dễ sinh sai SQL nhất.
"""

ALLOWED_TABLES = {"vw_game_sales_full"}

SCHEMA_CONTEXT = """\
Chỉ được truy vấn 1 view duy nhất: vw_game_sales_full (SQL Server / T-SQL).
Cột: game_id (int), game_name (varchar), genre_name (varchar),
     publisher_name (varchar), platform_name (varchar), release_year (int),
     region_name (varchar), num_sales (decimal - triệu bản, tại 1 region/platform).
Mỗi dòng = doanh số của 1 game, trên 1 platform, bởi 1 publisher, tại 1 region.
"""

FEW_SHOT_EXAMPLES = [
    (
        "Top 5 game bán chạy nhất ở Nhật năm 2016",
        "SELECT TOP 5 game_name, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full "
        "WHERE region_name = 'Japan' AND release_year = 2016 "
        "GROUP BY game_name ORDER BY total_sales DESC;",
    ),
    (
        "Tổng doanh số theo thể loại",
        "SELECT genre_name, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full GROUP BY genre_name ORDER BY total_sales DESC;",
    ),
    (
        "Nhà phát hành nào có nhiều game nhất",
        "SELECT TOP 10 publisher_name, COUNT(DISTINCT game_id) AS so_luong_game "
        "FROM vw_game_sales_full GROUP BY publisher_name "
        "ORDER BY so_luong_game DESC;",
    ),
    (
        "Xu hướng doanh số theo năm trên nền tảng PS4",
        "SELECT release_year, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full WHERE platform_name = 'PS4' "
        "GROUP BY release_year ORDER BY release_year;",
    ),
    (
        "Doanh số game 'FIFA 17' ở từng khu vực",
        "SELECT region_name, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full WHERE game_name = 'FIFA 17' "
        "GROUP BY region_name ORDER BY total_sales DESC;",
    ),
]


def build_prompt_context() -> str:
    examples = "\n".join(
        f"Q: {q}\nSQL: {sql}" for q, sql in FEW_SHOT_EXAMPLES
    )
    return f"{SCHEMA_CONTEXT}\nVí dụ:\n{examples}"
