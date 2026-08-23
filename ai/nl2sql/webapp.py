"""Web demo (nội bộ) cho NL2SQL Agent - chat hỏi đáp dữ liệu doanh số game.

Chạy: python -m ai.nl2sql.webapp
Mở trình duyệt: http://127.0.0.1:5050
"""
from flask import Flask, jsonify, render_template_string, request

from . import agent

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>NL2SQL Agent - Group7 Video Game Sales (demo nội bộ)</title>
<style>
  :root { color-scheme: light; }
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 860px;
         margin: 0 auto; padding: 24px; background: #f6f7f9; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .note { color: #666; font-size: 13px; margin-bottom: 20px; }
  #chat { display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px; }
  .msg { padding: 12px 14px; border-radius: 10px; max-width: 85%; white-space: pre-wrap; }
  .user { align-self: flex-end; background: #2563eb; color: white; }
  .bot { align-self: flex-start; background: white; border: 1px solid #e2e2e2; }
  .bot.blocked { border-color: #f0b429; background: #fffbea; }
  .bot .sql { margin-top: 8px; font-family: Consolas, monospace; font-size: 12.5px;
              background: #f2f2f2; padding: 8px; border-radius: 6px; overflow-x: auto; }
  .bot .meta { font-size: 11px; color: #888; margin-top: 6px; }
  form { display: flex; gap: 8px; position: sticky; bottom: 16px; }
  input[type=text] { flex: 1; padding: 12px 14px; border-radius: 8px; border: 1px solid #ccc;
                      font-size: 14px; }
  button { padding: 12px 18px; border-radius: 8px; border: none; background: #2563eb;
           color: white; font-size: 14px; cursor: pointer; }
  button:disabled { background: #999; cursor: default; }
  .examples { font-size: 12px; color: #666; margin-bottom: 18px; }
  .examples button { background: none; border: 1px solid #ccc; color: #333; padding: 4px 8px;
                      border-radius: 6px; font-size: 12px; margin: 2px; cursor: pointer; }
</style>
</head>
<body>
  <h1>NL2SQL Agent - Group7 Video Game Sales</h1>
  <div class="note">Demo nội bộ nhóm/lớp - hỏi đáp dữ liệu doanh số game bằng tiếng Việt/Anh.
    Không public ra ngoài.</div>

  <div class="examples">
    Ví dụ:
    <button onclick="ask('Top 5 game bán chạy nhất ở Nhật năm 2016')">Top 5 game Nhật 2016</button>
    <button onclick="ask('Nền tảng nào bán chạy nhất')">Nền tảng bán chạy nhất</button>
    <button onclick="ask('Xu hướng doanh số theo năm')">Xu hướng theo năm</button>
    <button onclick="ask('Thời tiết hôm nay thế nào')">(thử câu ngoài phạm vi)</button>
  </div>

  <div id="chat"></div>

  <form id="form">
    <input type="text" id="question" placeholder="Nhập câu hỏi..." autocomplete="off" required>
    <button type="submit" id="send">Gửi</button>
  </form>

<script>
const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('question');
const send = document.getElementById('send');

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  chat.appendChild(div);
  window.scrollTo(0, document.body.scrollHeight);
  return div;
}

async function ask(question) {
  input.value = question;
  addMsg(question, 'user');
  send.disabled = true;
  const botDiv = document.createElement('div');
  botDiv.className = 'msg bot';
  botDiv.textContent = 'Đang xử lý...';
  chat.appendChild(botDiv);
  window.scrollTo(0, document.body.scrollHeight);

  try {
    const resp = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question})
    });
    const data = await resp.json();
    if (data.blocked) {
      botDiv.classList.add('blocked');
      botDiv.textContent = '[BỊ CHẶN] ' + data.reason;
    } else {
      botDiv.textContent = data.answer;
      if (data.sql) {
        const pre = document.createElement('div');
        pre.className = 'sql';
        pre.textContent = data.sql;
        botDiv.appendChild(pre);
      }
      const meta = document.createElement('div');
      meta.className = 'meta';
      meta.textContent = data.row_count + ' dòng kết quả';
      botDiv.appendChild(meta);
    }
  } catch (e) {
    botDiv.textContent = 'Lỗi: ' + e;
  } finally {
    send.disabled = false;
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  ask(q);
  input.value = '';
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"blocked": True, "reason": "Câu hỏi trống."})

    result = agent.ask(question)
    return jsonify(
        {
            "blocked": result.blocked,
            "reason": result.reason,
            "sql": result.sql,
            "answer": result.answer,
            "row_count": len(result.rows),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
