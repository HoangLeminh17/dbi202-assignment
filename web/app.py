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

from flask import Flask, abort, render_template

# Cho phep import module ai/recommend.py tu thu muc goc repo
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai.recommend import load_data, recommend  # noqa: E402

app = Flask(__name__)


@app.route("/")
def index():
    df = load_data()
    top_games = (
        df.groupby(["game_id", "game_name"], as_index=False)["total_sales"]
        .sum()
        .sort_values("total_sales", ascending=False)
        .head(20)
    )
    return render_template("index.html", games=top_games.to_dict(orient="records"))


@app.route("/recommend/<int:game_id>")
def recommend_view(game_id):
    try:
        result = recommend(game_id, top_n=5)
    except ValueError:
        abort(404, description=f"Khong tim thay game_id={game_id}")
    return render_template(
        "recommend.html",
        game_id=game_id,
        recommendations=result.to_dict(orient="records"),
    )


if __name__ == "__main__":
    app.run(debug=True)

# TODO (Trung): bo sung route CRUD co ban (them/sua/xoa game) goi truc tiep
# vao stored procedure trong sql/trung/procedure.sql neu can demo day du hon.
