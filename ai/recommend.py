"""
Phu trach: Hoang (AI)
Muc dich: Phan mo rong ap dung AI cho do an DBI202 - goi y (recommend) game
tuong tu dua tren the loai, nen tang, nha phat hanh va doanh so vung (region_sales).

Cach chay:
    pip install -r requirements.txt
    python recommend.py --game-id 1 --top-n 5

Yeu cau: SQL Server driver (ODBC Driver 17/18 for SQL Server) da cai tren may,
va database Group7 da duoc tao + insert du lieu (xem sql/).
"""

import argparse

import pandas as pd
import pyodbc
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# TODO (Hoang): thay connection string cho dung voi SQL Server instance cua nhom
CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=Group7;"
    "Trusted_Connection=yes;"
)

QUERY = """
SELECT
    g.id AS game_id,
    g.game_name,
    gr.genre_name,
    p.publisher_name,
    pl.platform_name,
    ISNULL(SUM(rs.num_sales), 0) AS total_sales
FROM game g
JOIN genre gr ON gr.id = g.genre_id
LEFT JOIN game_publisher gp ON gp.game_id = g.id
LEFT JOIN publisher p ON p.id = gp.publisher_id
LEFT JOIN game_platform gpl ON gpl.game_publisher_id = gp.id
LEFT JOIN platform pl ON pl.id = gpl.platform_id
LEFT JOIN region_sales rs ON rs.game_platform_id = gpl.id
GROUP BY g.id, g.game_name, gr.genre_name, p.publisher_name, pl.platform_name
"""


def load_data() -> pd.DataFrame:
    with pyodbc.connect(CONNECTION_STRING) as conn:
        return pd.read_sql(QUERY, conn)


def build_content_matrix(df: pd.DataFrame):
    # Ghep genre + publisher + platform thanh 1 "van ban" dac trung cho tung game
    # (content-based filtering: game giong nhau ve dac trung se co vector gan nhau)
    df = df.copy()
    df["features"] = (
        df["genre_name"].fillna("")
        + " "
        + df["publisher_name"].fillna("")
        + " "
        + df["platform_name"].fillna("")
    )
    # Gom theo game_id vi 1 game co the co nhieu dong (nhieu platform/publisher)
    grouped = df.groupby(["game_id", "game_name"], as_index=False).agg(
        {"features": lambda x: " ".join(x), "total_sales": "sum"}
    )

    vectorizer = CountVectorizer()
    matrix = vectorizer.fit_transform(grouped["features"])
    return grouped, matrix


def recommend(game_id: int, top_n: int = 5) -> pd.DataFrame:
    df = load_data()
    grouped, matrix = build_content_matrix(df)

    if game_id not in grouped["game_id"].values:
        raise ValueError(f"Khong tim thay game_id={game_id}")

    idx = grouped.index[grouped["game_id"] == game_id][0]
    similarity = cosine_similarity(matrix[idx], matrix).flatten()

    grouped["similarity"] = similarity
    result = (
        grouped[grouped["game_id"] != game_id]
        .sort_values(["similarity", "total_sales"], ascending=False)
        .head(top_n)
    )
    return result[["game_id", "game_name", "similarity", "total_sales"]]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Goi y game tuong tu (content-based)")
    parser.add_argument("--game-id", type=int, required=True)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()

    recommendations = recommend(args.game_id, args.top_n)
    print(recommendations.to_string(index=False))

# TODO (Hoang): mo rong them - vd doi sang collaborative filtering theo doanh so
# vung (region_sales), hoac dung embedding/LLM de mo ta ly do goi y bang ngon ngu tu nhien.
