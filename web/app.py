"""
Phu trach: Trung (SE)
Muc dich: Web demo noi CSDL SQL Server (Group7) va phan goi y AI (ai/recommend.py)
lai voi nhau, minh hoa nghiep vu end-to-end cho bao cao/slide.

Cach chay:
    pip install -r requirements.txt
    (dam bao da chay xong cac file trong sql/ va cai dat ai/requirements.txt)
    python app.py
Mo trinh duyet: http://127.0.0.1:5000
"""

import sys
from pathlib import Path

import pyodbc
from flask import Flask, abort, flash, redirect, render_template, request, url_for

# Cho phep import module ai/recommend.py tu thu muc goc repo
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai.recommend import CONNECTION_STRING, load_data, recommend  # noqa: E402

app = Flask(__name__)
app.secret_key = "dbi202-group7-secret-key"

# ==============================================================
# Helper: ket noi truc tiep toi SQL Server
# ==============================================================

def get_db_connection():
    """Tra ve mot pyodbc connection toi database Group7."""
    return pyodbc.connect(CONNECTION_STRING)


def query_db(sql, params=None, fetchone=False):
    """Chay mot cau SELECT va tra ve ket qua dang list[dict] hoac dict."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        columns = [desc[0] for desc in cursor.description]
        if fetchone:
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def execute_db(sql, params=None):
    """Chay mot cau INSERT/UPDATE/DELETE (khong tra ve ket qua)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        conn.commit()
    finally:
        conn.close()


# ==============================================================
# Helper: lay danh sach lookup (genre, platform, publisher, region)
# ==============================================================

def get_genres():
    return query_db("SELECT id, genre_name FROM genre ORDER BY genre_name")


def get_platforms():
    return query_db("SELECT id, platform_name FROM platform ORDER BY platform_name")


def get_publishers():
    return query_db("SELECT id, publisher_name FROM publisher ORDER BY publisher_name")


def get_regions():
    return query_db("SELECT id, region_name FROM region ORDER BY region_name")


# ==============================================================
# Routes
# ==============================================================

@app.route("/")
def index():
    """Trang Dashboard: hien thi thong ke va top 20 game."""
    try:
        # Thong ke tong quat
        stats = query_db("""
            SELECT
                (SELECT COUNT(*) FROM game) AS total_games,
                (SELECT COUNT(*) FROM publisher) AS total_publishers,
                (SELECT COUNT(*) FROM platform) AS total_platforms,
                (SELECT ISNULL(SUM(num_sales), 0) FROM region_sales) AS total_sales
        """, fetchone=True)

        # Top 20 game ban chay nhat
        games = query_db("""
            SELECT TOP 20
                g.id AS game_id,
                g.game_name,
                gr.genre_name,
                p.publisher_name,
                ISNULL(SUM(rs.num_sales), 0) AS total_sales
            FROM game g
            JOIN genre gr ON gr.id = g.genre_id
            LEFT JOIN game_publisher gp ON gp.game_id = g.id
            LEFT JOIN publisher p ON p.id = gp.publisher_id
            LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
            LEFT JOIN region_sales rs ON rs.game_platform_id = gpl.id
            GROUP BY g.id, g.game_name, gr.genre_name, p.publisher_name
            ORDER BY total_sales DESC
        """)

        return render_template("index.html", stats=stats, games=games, active_page="home")

    except pyodbc.Error as e:
        flash(f"Lỗi kết nối CSDL: {e}", "error")
        return render_template("index.html", stats={
            "total_games": 0, "total_publishers": 0,
            "total_platforms": 0, "total_sales": 0
        }, games=[], active_page="home")


@app.route("/games")
def games_list():
    """Trang danh sach game voi search, filter, pagination."""
    keyword = request.args.get("q", "").strip()
    genre_id = request.args.get("genre", type=int)
    platform_id = request.args.get("platform", type=int)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 30

    try:
        # Dem tong so ket qua
        count_sql = """
            SELECT COUNT(DISTINCT g.id) AS cnt
            FROM game g
            LEFT JOIN game_publisher gp ON gp.game_id = g.id
            LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
            WHERE 1=1
        """
        params = []
        if keyword:
            count_sql += " AND g.game_name LIKE ?"
            params.append(f"%{keyword}%")
        if genre_id:
            count_sql += " AND g.genre_id = ?"
            params.append(genre_id)
        if platform_id:
            count_sql += " AND gpl.platform_id = ?"
            params.append(platform_id)

        total = query_db(count_sql, params, fetchone=True)["cnt"]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)
        offset = (page - 1) * per_page

        # Query du lieu
        data_sql = """
            SELECT
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
            WHERE 1=1
        """
        data_params = []
        if keyword:
            data_sql += " AND g.game_name LIKE ?"
            data_params.append(f"%{keyword}%")
        if genre_id:
            data_sql += " AND g.genre_id = ?"
            data_params.append(genre_id)
        if platform_id:
            data_sql += " AND gpl.platform_id = ?"
            data_params.append(platform_id)

        data_sql += """
            GROUP BY g.id, g.game_name, gr.genre_name, p.publisher_name,
                     pl.platform_name, gpl.release_year
            ORDER BY total_sales DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        data_params.extend([offset, per_page])

        games = query_db(data_sql, data_params)

        return render_template("games.html",
            games=games, keyword=keyword, genre_id=genre_id,
            platform_id=platform_id, page=page, total_pages=total_pages,
            offset=offset, genres=get_genres(), platforms=get_platforms(),
            active_page="games"
        )

    except pyodbc.Error as e:
        flash(f"Lỗi kết nối CSDL: {e}", "error")
        return render_template("games.html",
            games=[], keyword=keyword, genre_id=genre_id,
            platform_id=platform_id, page=1, total_pages=1,
            offset=0, genres=[], platforms=[], active_page="games"
        )


@app.route("/game/<int:game_id>")
def game_detail(game_id):
    """Trang chi tiet game: thong tin, publisher/platform, doanh so theo region."""
    try:
        # Thong tin game chinh
        game = query_db("""
            SELECT
                g.id AS game_id,
                g.game_name,
                gr.genre_name,
                ISNULL(SUM(rs.num_sales), 0) AS total_sales
            FROM game g
            JOIN genre gr ON gr.id = g.genre_id
            LEFT JOIN game_publisher gp ON gp.game_id = g.id
            LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
            LEFT JOIN region_sales rs ON rs.game_platform_id = gpl.id
            WHERE g.id = ?
            GROUP BY g.id, g.game_name, gr.genre_name
        """, [game_id], fetchone=True)

        if not game:
            abort(404, description=f"Khong tim thay game_id={game_id}")

        # Danh sach publisher/platform
        publishers = query_db("""
            SELECT DISTINCT
                p.publisher_name,
                pl.platform_name,
                gpl.release_year
            FROM game_publisher gp
            JOIN publisher p ON p.id = gp.publisher_id
            LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
            LEFT JOIN platform pl ON pl.id = gpl.platform_id
            WHERE gp.game_id = ?
            ORDER BY p.publisher_name, pl.platform_name
        """, [game_id])

        # Doanh so theo region
        sales = query_db("""
            SELECT
                r.region_name,
                pl.platform_name,
                rs.num_sales
            FROM region_sales rs
            JOIN region r ON r.id = rs.region_id
            JOIN game_platform gpl ON gpl.id = rs.game_platform_id
            JOIN game_publisher gp ON gp.id = gpl.game_publisher_id
            LEFT JOIN platform pl ON pl.id = gpl.platform_id
            WHERE gp.game_id = ?
            ORDER BY r.region_name, pl.platform_name
        """, [game_id])

        return render_template("game_detail.html",
            game=game, publishers=publishers, sales=sales, active_page="games"
        )

    except pyodbc.Error as e:
        flash(f"Lỗi kết nối CSDL: {e}", "error")
        return redirect(url_for("games_list"))


@app.route("/recommend/<int:game_id>")
def recommend_view(game_id):
    """Trang goi y game tuong tu bang AI (content-based filtering)."""
    try:
        # Lay ten game goc
        game = query_db("SELECT game_name FROM game WHERE id = ?", [game_id], fetchone=True)
        source_game = game["game_name"] if game else f"game_id={game_id}"

        result = recommend(game_id, top_n=10)
        return render_template("recommend.html",
            game_id=game_id,
            source_game=source_game,
            recommendations=result.to_dict(orient="records"),
            active_page=""
        )
    except ValueError:
        abort(404, description=f"Khong tim thay game_id={game_id}")
    except pyodbc.Error as e:
        flash(f"Lỗi kết nối CSDL: {e}", "error")
        return redirect(url_for("index"))


@app.route("/add", methods=["GET", "POST"])
def add_game():
    """Form them game moi - goi stored procedure sp_AddNewGame."""
    if request.method == "POST":
        game_name = request.form.get("game_name", "").strip()
        genre_id = request.form.get("genre_id", type=int)
        publisher_id = request.form.get("publisher_id", type=int)
        platform_id = request.form.get("platform_id", type=int)
        release_year = request.form.get("release_year", type=int)
        region_id = request.form.get("region_id", type=int)
        num_sales = request.form.get("num_sales", type=float)

        if not game_name or not genre_id or not publisher_id or not platform_id:
            flash("Vui lòng điền đầy đủ thông tin bắt buộc (*)", "error")
            return redirect(url_for("add_game"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Goi stored procedure sp_AddNewGame
            sql = """
                DECLARE @NewId INT;
                EXEC sp_AddNewGame
                    @GameName = ?,
                    @GenreId = ?,
                    @PublisherId = ?,
                    @PlatformId = ?,
                    @ReleaseYear = ?,
                    @RegionId = ?,
                    @NumSales = ?,
                    @NewGameId = @NewId OUTPUT;
                SELECT @NewId AS new_game_id;
            """
            cursor.execute(sql, [
                game_name, genre_id, publisher_id, platform_id,
                release_year, region_id, num_sales
            ])

            row = cursor.fetchone()
            new_id = row[0] if row else None
            conn.commit()
            conn.close()

            flash(f"Đã thêm game '{game_name}' thành công (ID={new_id})", "success")
            if new_id:
                return redirect(url_for("game_detail", game_id=new_id))
            return redirect(url_for("games_list"))

        except pyodbc.Error as e:
            flash(f"Lỗi khi thêm game: {e}", "error")
            return redirect(url_for("add_game"))

    # GET: hien thi form
    try:
        return render_template("add_game.html",
            genres=get_genres(),
            publishers=get_publishers(),
            platforms=get_platforms(),
            regions=get_regions(),
            active_page="add"
        )
    except pyodbc.Error as e:
        flash(f"Lỗi kết nối CSDL: {e}", "error")
        return render_template("add_game.html",
            genres=[], publishers=[], platforms=[], regions=[], active_page="add"
        )


@app.route("/delete/<int:game_id>")
def delete_game(game_id):
    """Xoa game - goi stored procedure sp_DeleteGame."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("EXEC sp_DeleteGame @GameId = ?", [game_id])
        conn.commit()
        conn.close()
        flash(f"Đã xoá game ID={game_id} và dữ liệu liên quan.", "success")
    except pyodbc.Error as e:
        flash(f"Lỗi khi xoá game: {e}", "error")

    return redirect(url_for("games_list"))


# ==============================================================
# Error handlers
# ==============================================================

@app.errorhandler(404)
def not_found(e):
    flash(str(e), "error")
    return redirect(url_for("index"))


@app.errorhandler(500)
def internal_error(e):
    flash("Lỗi máy chủ nội bộ. Vui lòng thử lại.", "error")
    return redirect(url_for("index"))


# ==============================================================
# Main
# ==============================================================

if __name__ == "__main__":
    app.run(debug=True)
