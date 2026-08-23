"""Schema-as-context (compact) + few-shot SQL examples cho NL2SQL Agent.

Chi dua vw_game_sales_full (xem sql/hoang/08_nl2sql_view.sql) vao context thay vi
toan bo 8 bang goc, de LLM khong phai tu suy JOIN qua 2 bang trung gian
(game_publisher, game_platform) - noi LLM de sinh sai SQL nhat.
"""

ALLOWED_TABLES = {"vw_game_sales_full"}

SCHEMA_CONTEXT = """\
Chi duoc truy van 1 view duy nhat: vw_game_sales_full (SQL Server / T-SQL).
Cot: game_id (int), game_name (varchar), genre_name (varchar),
     publisher_name (varchar), platform_name (varchar), release_year (int),
     region_name (varchar), num_sales (decimal - trieu ban, tai 1 region/platform).
Moi dong = doanh so cua 1 game, tren 1 platform, boi 1 publisher, tai 1 region.
"""

FEW_SHOT_EXAMPLES = [
    (
        "Top 5 game ban chay nhat o Nhat nam 2016",
        "SELECT TOP 5 game_name, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full "
        "WHERE region_name = 'Japan' AND release_year = 2016 "
        "GROUP BY game_name ORDER BY total_sales DESC;",
    ),
    (
        "Tong doanh so theo the loai",
        "SELECT genre_name, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full GROUP BY genre_name ORDER BY total_sales DESC;",
    ),
    (
        "Nha phat hanh nao co nhieu game nhat",
        "SELECT TOP 10 publisher_name, COUNT(DISTINCT game_id) AS so_luong_game "
        "FROM vw_game_sales_full GROUP BY publisher_name "
        "ORDER BY so_luong_game DESC;",
    ),
    (
        "Xu huong doanh so theo nam tren nen tang PS4",
        "SELECT release_year, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full WHERE platform_name = 'PS4' "
        "GROUP BY release_year ORDER BY release_year;",
    ),
    (
        "Doanh so game 'FIFA 17' o tung khu vuc",
        "SELECT region_name, SUM(num_sales) AS total_sales "
        "FROM vw_game_sales_full WHERE game_name = 'FIFA 17' "
        "GROUP BY region_name ORDER BY total_sales DESC;",
    ),
]


def build_prompt_context() -> str:
    examples = "\n".join(
        f"Q: {q}\nSQL: {sql}" for q, sql in FEW_SHOT_EXAMPLES
    )
    return f"{SCHEMA_CONTEXT}\nVi du:\n{examples}"
