"""Web demo (nội bộ) cho NL2SQL Agent - chat hỏi đáp dữ liệu doanh số game.

Chạy: python -m ai.nl2sql.webapp
Mở trình duyệt: http://127.0.0.1:5050
Trang admin (xem log toàn bộ luồng xử lý): http://127.0.0.1:5050/admin
  - Đăng nhập bằng ADMIN_USER/ADMIN_PASSWORD trong ai/.env.
"""
import functools
import threading
import time
from collections import defaultdict, deque

from flask import Flask, Response, jsonify, render_template_string, request

from . import agent, db, llm_client, logging_store
from .config import CONFIG

app = Flask(__name__)

# Rate limit don gian theo IP cho /ask - demo noi bo (1 tien trinh, khong sau
# proxy) nen luu in-memory la du, KHONG dung X-Forwarded-For (client tu goi
# header nay de gia mao IP that neu khong co proxy tin cay dung truoc chuan
# hoa no) - dung thang request.remote_addr. San xuat that voi nhieu instance
# can chuyen sang store dung chung (vd Redis) thay vi in-memory per-process.
_RATE_LIMIT_MAX_REQUESTS = 20
_RATE_LIMIT_WINDOW_SECONDS = 60
_rate_lock = threading.Lock()
_rate_log = defaultdict(deque)  # ip -> deque[timestamp giay, tang dan]


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        q = _rate_log[ip]
        while q and now - q[0] > _RATE_LIMIT_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= _RATE_LIMIT_MAX_REQUESTS:
            return True
        q.append(now)
        return False


def require_admin_auth(view):
    """HTTP Basic Auth đơn giản cho trang /admin - so khớp ADMIN_USER/ADMIN_PASSWORD."""

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        if (
            not CONFIG.admin_password
            or not auth
            or auth.username != CONFIG.admin_user
            or auth.password != CONFIG.admin_password
        ):
            return Response(
                "Yêu cầu đăng nhập admin (xem ADMIN_USER/ADMIN_PASSWORD trong ai/.env).",
                401,
                {"WWW-Authenticate": 'Basic realm="NL2SQL Admin"'},
            )
        return view(*args, **kwargs)

    return wrapped

PAGE = """
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>NL2SQL Agent - Group7 Video Game Sales (demo nội bộ)</title>
<style>
  :root {
    color-scheme: light;
    --accent: #4f46e5; --accent-dark: #4338ca;
    --bg: #f4f5f7; --panel: #ffffff; --border: #e5e7eb;
    --text: #1f2430; --text-dim: #6b7280;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body { font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; color: var(--text);
         background: var(--bg); }
  .app { display: flex; height: 100vh; overflow: hidden; }

  /* Sidebar - lich su chat */
  .sidebar { width: 260px; flex-shrink: 0; background: var(--panel); border-right: 1px solid var(--border);
             display: flex; flex-direction: column; padding: 14px; overflow-y: auto; }
  .brand { font-weight: 700; font-size: 15px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
  .new-chat-btn { background: var(--accent); color: white; border: none; border-radius: 8px;
                  padding: 10px 12px; font-size: 13.5px; cursor: pointer; margin-bottom: 14px; text-align: left; }
  .new-chat-btn:hover { background: var(--accent-dark); }
  .history-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase;
                    letter-spacing: .04em; margin: 4px 0 6px; }
  .history-list { display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
  .history-item { padding: 9px 8px 9px 10px; border-radius: 8px; font-size: 13px; color: var(--text);
                   cursor: pointer; border: 1px solid transparent;
                   display: flex; align-items: center; gap: 6px; }
  .history-item:hover { background: #f0f1f5; }
  .history-item.active { background: #eef0fe; border-color: #d9dcfb; color: var(--accent-dark); font-weight: 600; }
  .history-item .title { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .history-item .title input { width: 100%; border: 1px solid var(--accent); border-radius: 4px;
                                font: inherit; color: inherit; padding: 1px 4px; background: white; }
  .history-item .item-actions { display: flex; gap: 2px; opacity: 0; flex-shrink: 0; }
  .history-item:hover .item-actions { opacity: 1; }
  .icon-btn { background: none; border: none; padding: 3px; border-radius: 5px; cursor: pointer;
              color: var(--text-dim); display: inline-flex; align-items: center; justify-content: center; }
  .icon-btn:hover { background: #e2e4ec; color: var(--text); }
  .icon-btn svg { width: 14px; height: 14px; }
  .icon-btn.fb-up.active { color: #0ca30c; }
  .icon-btn.fb-down.active { color: #d03b3b; }
  .sidebar-footer { margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border); }
  .sidebar-footer a { font-size: 12px; color: var(--text-dim); text-decoration: none; }
  .sidebar-footer a:hover { color: var(--accent); }

  /* Main - header co dinh, chat cuon rieng */
  .main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .topbar { flex-shrink: 0; padding: 14px 24px; border-bottom: 1px solid var(--border);
            background: var(--panel); display: flex; justify-content: space-between; align-items: center; }
  .topbar h1 { font-size: 17px; margin: 0; }
  .topbar .sub { font-size: 12px; color: var(--text-dim); font-weight: 400; }
  .ghost-btn { background: none; border: 1px solid var(--border); color: var(--text);
               padding: 7px 12px; border-radius: 7px; font-size: 12.5px; cursor: pointer; }
  .ghost-btn:hover { background: #f0f1f5; }

  .examples { flex-shrink: 0; padding: 10px 24px; font-size: 12px; color: var(--text-dim);
              border-bottom: 1px solid var(--border); background: var(--panel); }
  .examples button { background: none; border: 1px solid var(--border); color: #333; padding: 4px 9px;
                      border-radius: 999px; font-size: 12px; margin: 3px 4px 0 0; cursor: pointer; }
  .examples button:hover { background: #f0f1f5; }

  #chat { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
  .empty-state { color: var(--text-dim); font-size: 13px; text-align: center; margin-top: 60px; }
  .msg-row { display: flex; flex-direction: column; margin-bottom: 10px; }
  .msg-row.user-row { align-items: flex-end; }
  .msg-row.bot-row { align-items: flex-start; }
  .msg { padding: 12px 14px; border-radius: 12px; max-width: 78%; white-space: pre-wrap; line-height: 1.45; }
  .user { background: var(--accent); color: white; border-bottom-right-radius: 3px; }
  .bot { background: var(--panel); border: 1px solid var(--border); border-bottom-left-radius: 3px; }
  .bot.blocked { border-color: #f0b429; background: #fffbea; }
  .bot.error { border-color: #e5b8a8; background: #fff4ef; }
  .bot .sql { margin-top: 8px; font-family: Consolas, monospace; font-size: 12.5px;
              background: #f2f2f4; padding: 8px; border-radius: 6px; overflow-x: auto; }
  .bot .meta { font-size: 11px; color: #888; margin-top: 6px; }
  .msg-actions { display: flex; gap: 2px; margin-top: 3px; opacity: 0; transition: opacity .1s; }
  .msg-row:hover .msg-actions { opacity: 1; }
  .msg-time { font-size: 10.5px; color: var(--text-dim); padding: 0 4px; align-self: center; }

  .edit-box { width: 100%; max-width: 78%; align-self: flex-end; }
  .edit-box textarea { width: 100%; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--accent);
                        font: inherit; font-size: 14px; resize: vertical; box-sizing: border-box; }
  .edit-box textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  .edit-btn-row { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }
  .edit-cancel-btn, .edit-save-btn { padding: 6px 14px; border-radius: 7px; font-size: 12.5px; cursor: pointer; }
  .edit-cancel-btn { background: none; border: 1px solid var(--border); color: var(--text); }
  .edit-cancel-btn:hover { background: #f0f1f5; }
  .edit-save-btn { background: var(--accent); border: none; color: white; }
  .edit-save-btn:hover { background: var(--accent-dark); }

  .composer { flex-shrink: 0; padding: 16px 24px; border-top: 1px solid var(--border);
              background: var(--panel); display: flex; gap: 8px; }
  input[type=text] { flex: 1; padding: 12px 14px; border-radius: 9px; border: 1px solid #d0d3da;
                      font-size: 14px; }
  input[type=text]:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  button[type=submit] { padding: 12px 20px; border-radius: 9px; border: none; background: var(--accent);
           color: white; font-size: 14px; cursor: pointer; }
  button[type=submit]:hover { background: var(--accent-dark); }
  button:disabled { background: #a8adba !important; cursor: default; }
  #stopBtn { padding: 12px 20px; border-radius: 9px; border: 1px solid #d0341f; background: white;
             color: #d0341f; font-size: 14px; cursor: pointer; }
  #stopBtn:hover { background: #fdecea; }
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">Chatbot nội bộ G7 - Video game sales</div>
    <button class="new-chat-btn" id="newChatBtn">+ Đoạn chat mới</button>
    <div class="history-label">Lịch sử</div>
    <div class="history-list" id="historyList"></div>
    <div class="sidebar-footer"><a href="/admin">Admin monitor &rarr;</a></div>
  </aside>

  <main class="main">
    <div class="topbar">
      <h1>Group7 Video Game Sales <span class="sub">- demo nội bộ, không public{{ (' · ' + freshness_note) if freshness_note else '' }}</span></h1>
    </div>
    <div class="examples">
      Ví dụ:
      <button onclick="ask('Top 5 game bán chạy nhất ở Nhật năm 2016')">Top 5 game Nhật 2016</button>
      <button onclick="ask('Nền tảng nào bán chạy nhất')">Nền tảng bán chạy nhất</button>
      <button onclick="ask('Xu hướng doanh số theo năm')">Xu hướng theo năm</button>
      <button onclick="ask('Thời tiết hôm nay thế nào')">(thử câu ngoài phạm vi)</button>
    </div>

    <div id="chat"></div>

    <form class="composer" id="form">
      <input type="text" id="question" placeholder="Nhập câu hỏi..." autocomplete="off" required>
      <button type="submit" id="send">Gửi</button>
      <button type="button" id="stopBtn" style="display:none;">Dừng</button>
    </form>
  </main>
</div>

<script>
const chatEl = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('question');
const send = document.getElementById('send');
const stopBtn = document.getElementById('stopBtn');
const historyList = document.getElementById('historyList');
const newChatBtn = document.getElementById('newChatBtn');

let currentAbortController = null;

const STORE_KEY = 'nl2sql_chat_sessions_v1';

const ICONS = {
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  retry: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg>',
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg>',
};

function iconBtn(name, title, onClick) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'icon-btn';
  btn.title = title;
  btn.innerHTML = ICONS[name];
  btn.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
  return btn;
}

function formatTime(ms) {
  const d = new Date(ms);
  return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0');
}

function loadStore() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) || { sessions: {}, order: [], currentId: null };
  } catch (e) { return { sessions: {}, order: [], currentId: null }; }
}
function saveStore(store) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) {}
}

let store = loadStore();

function newSession() {
  const id = 'c' + Date.now();
  store.sessions[id] = { id, title: 'Đoạn chat mới', messages: [] };
  store.order.unshift(id);
  store.currentId = id;
  saveStore(store);
  renderSidebar();
  renderChat();
}

function currentSession() {
  if (!store.currentId || !store.sessions[store.currentId]) {
    if (store.order.length) { store.currentId = store.order[0]; }
    else { newSession(); }
  }
  return store.sessions[store.currentId];
}

function switchSession(id) {
  store.currentId = id;
  saveStore(store);
  renderSidebar();
  renderChat();
}

function renameSession(id, title) {
  const s = store.sessions[id];
  if (!s) return;
  s.title = title.trim() || 'Đoạn chat mới';
  saveStore(store);
  renderSidebar();
}

function deleteSession(id) {
  if (!confirm('Xoá đoạn chat này?')) return;
  delete store.sessions[id];
  store.order = store.order.filter((x) => x !== id);
  if (store.currentId === id) store.currentId = null;
  saveStore(store);
  if (!store.order.length) { newSession(); return; }
  currentSession();
  saveStore(store);
  renderSidebar();
  renderChat();
}

function renderSidebar() {
  historyList.innerHTML = '';
  for (const id of store.order) {
    const s = store.sessions[id];
    if (!s) continue;
    const div = document.createElement('div');
    div.className = 'history-item' + (id === store.currentId ? ' active' : '');
    div.onclick = () => switchSession(id);

    const titleEl = document.createElement('div');
    titleEl.className = 'title';
    titleEl.textContent = s.title;
    div.appendChild(titleEl);

    const actions = document.createElement('div');
    actions.className = 'item-actions';
    actions.appendChild(iconBtn('edit', 'Đổi tên', () => {
      titleEl.innerHTML = '';
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.value = s.title;
      titleEl.appendChild(inp);
      inp.focus();
      inp.select();
      const commit = () => renameSession(id, inp.value);
      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); commit(); }
        if (e.key === 'Escape') { e.preventDefault(); renderSidebar(); }
      });
      inp.addEventListener('blur', commit);
    }));
    actions.appendChild(iconBtn('trash', 'Xoá đoạn chat', () => deleteSession(id)));
    div.appendChild(actions);

    historyList.appendChild(div);
  }
}

function retryFromBotIndex(index) {
  if (currentAbortController) return;
  const s = currentSession();
  for (let i = index - 1; i >= 0; i--) {
    if (s.messages[i].role === 'user') {
      const question = s.messages[i].text;
      s.messages.splice(i); // bo cau hoi + cau tra loi cu, sinh lai ngay tai cho nay
      saveStore(store);
      renderChat();
      renderSidebar();
      ask(question);
      return;
    }
  }
}

function copyText(text) {
  if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
}

function sendFeedback(index, value) {
  const s = currentSession();
  const m = s.messages[index];
  if (!m || !m.requestId) return;
  m.feedback = m.feedback === value ? null : value; // bam lai nut da chon -> bo danh gia
  saveStore(store);
  renderChat();
  fetch('/feedback', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({request_id: m.requestId, feedback: m.feedback}),
  }).catch(() => {});
}

let editingIndex = null;

function startEdit(index) {
  editingIndex = index;
  renderChat();
  const ta = chatEl.querySelector('.edit-box textarea');
  if (ta) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }
}

function cancelEdit() {
  editingIndex = null;
  renderChat();
}

function saveEdit(index, newText) {
  newText = newText.trim();
  if (!newText) return;
  editingIndex = null;
  const s = currentSession();
  s.messages.splice(index); // bo tin nhan nay + moi thu sau no (cau tra loi cu da het gia tri)
  saveStore(store);
  renderChat();
  renderSidebar();
  ask(newText); // chay lai ngay voi prompt da sua
}

function renderMsg(m, index) {
  const row = document.createElement('div');
  row.className = 'msg-row ' + (m.role === 'user' ? 'user-row' : 'bot-row');

  if (m.role === 'user' && index === editingIndex) {
    const box = document.createElement('div');
    box.className = 'edit-box';
    const ta = document.createElement('textarea');
    ta.value = m.text;
    ta.rows = Math.min(6, Math.max(2, Math.ceil(m.text.length / 40)));
    box.appendChild(ta);

    const btnRow = document.createElement('div');
    btnRow.className = 'edit-btn-row';
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'edit-cancel-btn';
    cancelBtn.textContent = 'Huỷ';
    cancelBtn.addEventListener('click', cancelEdit);
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'edit-save-btn';
    saveBtn.textContent = 'Lưu & chạy lại';
    saveBtn.addEventListener('click', () => saveEdit(index, ta.value));
    ta.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveEdit(index, ta.value); }
      if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
    });
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(saveBtn);
    box.appendChild(btnRow);

    row.appendChild(box);
    chatEl.appendChild(row);
    return;
  }

  const div = document.createElement('div');
  div.className = 'msg ' + (m.role === 'user' ? 'user' : ('bot' + (m.error ? ' error' : (m.blocked ? ' blocked' : ''))));
  div.textContent = m.text;
  if (m.sql) {
    const pre = document.createElement('div');
    pre.className = 'sql';
    pre.textContent = m.sql;
    div.appendChild(pre);
  }
  if (m.role === 'bot' && m.elapsedSec !== undefined) {
    const meta = document.createElement('div');
    meta.className = 'meta';
    const parts = [];
    if (!m.blocked && !m.error && m.rowCount !== undefined) parts.push(m.rowCount + ' dòng kết quả');
    parts.push('trả lời sau ' + m.elapsedSec + 's');
    meta.textContent = parts.join(' · ');
    div.appendChild(meta);
  }
  row.appendChild(div);

  const actionsRow = document.createElement('div');
  actionsRow.className = 'msg-actions';
  if (m.role === 'user') {
    actionsRow.appendChild(iconBtn('edit', 'Chỉnh sửa', () => startEdit(index)));
  } else {
    actionsRow.appendChild(iconBtn('copy', 'Sao chép', () => copyText(m.text)));
    actionsRow.appendChild(iconBtn('retry', 'Thử lại', () => retryFromBotIndex(index)));
    if (m.requestId && !m.blocked && !m.error) {
      const upBtn = iconBtn('up', 'Câu trả lời hữu ích', () => sendFeedback(index, 'up'));
      upBtn.classList.add('fb-up');
      if (m.feedback === 'up') upBtn.classList.add('active');
      actionsRow.appendChild(upBtn);
      const downBtn = iconBtn('down', 'Câu trả lời chưa đúng', () => sendFeedback(index, 'down'));
      downBtn.classList.add('fb-down');
      if (m.feedback === 'down') downBtn.classList.add('active');
      actionsRow.appendChild(downBtn);
    }
  }
  if (m.timestamp) {
    const t = document.createElement('span');
    t.className = 'msg-time';
    t.textContent = formatTime(m.timestamp);
    actionsRow.appendChild(t);
  }
  row.appendChild(actionsRow);

  chatEl.appendChild(row);
}

function renderChat() {
  chatEl.innerHTML = '';
  const s = currentSession();
  if (!s.messages.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'Đặt câu hỏi về doanh số game để bắt đầu.';
    chatEl.appendChild(empty);
  } else {
    s.messages.forEach(renderMsg);
  }
  chatEl.scrollTop = chatEl.scrollHeight;
}

function pushMsg(msg) {
  const s = currentSession();
  msg.timestamp = msg.timestamp || Date.now();
  s.messages.push(msg);
  if (msg.role === 'user' && s.messages.filter(m => m.role === 'user').length === 1) {
    s.title = msg.text.slice(0, 40) + (msg.text.length > 40 ? '...' : '');
  }
  saveStore(store);
}

async function ask(question) {
  if (currentAbortController) return; // dang co 1 cau hoi chay do, khong gui chong

  const s0 = currentSession();
  const userMsg = { role: 'user', text: question };
  pushMsg(userMsg);
  const emptyState = chatEl.querySelector('.empty-state');
  if (emptyState) emptyState.remove();
  renderMsg(userMsg, s0.messages.length - 1);
  chatEl.scrollTop = chatEl.scrollHeight;
  renderSidebar();

  input.value = '';
  input.disabled = true;
  send.style.display = 'none';
  stopBtn.style.display = 'inline-block';

  const pendingRow = document.createElement('div');
  pendingRow.className = 'msg-row bot-row';
  const pending = document.createElement('div');
  pending.className = 'msg bot';
  pending.textContent = 'Đang xử lý... (0s)';
  pendingRow.appendChild(pending);
  chatEl.appendChild(pendingRow);
  chatEl.scrollTop = chatEl.scrollHeight;

  const startedAt = Date.now();
  const tick = setInterval(() => {
    pending.textContent = 'Đang xử lý... (' + Math.floor((Date.now() - startedAt) / 1000) + 's)';
  }, 1000);

  const controller = new AbortController();
  currentAbortController = controller;

  let botMsg;
  let stopped = false;
  try {
    const resp = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question}),
      signal: controller.signal
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    if (data.error) {
      botMsg = { role: 'bot', error: true, text: data.reason };
    } else if (data.blocked) {
      botMsg = { role: 'bot', blocked: true, text: '[BỊ CHẶN] ' + data.reason };
    } else {
      botMsg = { role: 'bot', text: data.answer, sql: data.sql, rowCount: data.row_count, requestId: data.request_id };
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      stopped = true;
      botMsg = { role: 'bot', blocked: true, text: 'Đã dừng theo yêu cầu của bạn.' };
    } else {
      // Fetch tu no fail nghia la khong ket noi duoc toi server (server sap/mat mang)
      botMsg = { role: 'bot', error: true, text: 'Mất kết nối tới server, vui lòng thử lại sau.' };
    }
  }
  clearInterval(tick);
  currentAbortController = null;
  botMsg.elapsedSec = Math.round((Date.now() - startedAt) / 1000);
  pendingRow.remove();
  pushMsg(botMsg);
  renderMsg(botMsg, currentSession().messages.length - 1);
  chatEl.scrollTop = chatEl.scrollHeight;

  input.disabled = false;
  send.style.display = 'inline-block';
  stopBtn.style.display = 'none';
  if (stopped) {
    input.value = question;
    input.focus();
  }
}

stopBtn.addEventListener('click', () => {
  if (currentAbortController) currentAbortController.abort();
});

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  ask(q);
});

newChatBtn.addEventListener('click', newSession);

if (!store.order.length) { newSession(); } else { renderSidebar(); renderChat(); }
</script>
</body>
</html>
"""


@app.route("/")
def index():
    # Data Freshness cho user - chi can biet du lieu moi toi dau, khong can
    # provenance/lineage (nhung thu do chi admin can qua /admin).
    try:
        fresh = db.get_data_freshness()
        last_update = fresh["last_data_update"]
        freshness_note = f"Dữ liệu cập nhật lần cuối: {last_update:%d/%m/%Y}"
    except Exception:
        agent.logger.exception("Không lấy được data freshness cho trang chủ")
        freshness_note = None  # DB chua san sang - khong chan trang chat vi ly do nay
    return render_template_string(PAGE, freshness_note=freshness_note)


@app.route("/ask", methods=["POST"])
def ask():
    if _is_rate_limited(request.remote_addr or "unknown"):
        return jsonify({
            "blocked": True,
            "reason": (
                f"Bạn gửi quá nhiều câu hỏi (tối đa {_RATE_LIMIT_MAX_REQUESTS} "
                f"câu / {_RATE_LIMIT_WINDOW_SECONDS}s). Vui lòng thử lại sau."
            ),
        }), 429

    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"blocked": True, "reason": "Câu hỏi trống."})

    try:
        result = agent.ask(question)
    except Exception as exc:  # phong thu cuoi cung, khong de request treo/500
        category = agent._categorize_error(exc)
        return jsonify({"error": True, "reason": agent.ERROR_CATEGORY_MESSAGES[category]})

    return jsonify(
        {
            "blocked": result.blocked,
            "error": result.error,
            "reason": result.reason,
            "sql": result.sql,
            "answer": result.answer,
            "row_count": len(result.rows),
            "request_id": result.request_id,
        }
    )


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json(force=True) or {}
    request_id = data.get("request_id")
    value = data.get("feedback")
    if not request_id or value not in ("up", "down", None):
        return jsonify({"ok": False}), 400
    ok = logging_store.set_feedback(int(request_id), value)
    return jsonify({"ok": ok})


ADMIN_PAGE = """
<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="45">
<title>Admin monitor - NL2SQL Agent</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 1200px;
         margin: 0 auto; padding: 24px; background: #f6f7f9; }
  h1 { font-size: 20px; margin-bottom: 4px; text-align: center; }
  .toolbar { display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; }
  .toolbar a {
    font-size: 12.5px; padding: 6px 14px; border-radius: 999px; border: 1px solid #d6d6d0;
    background: white; color: #1f2430; text-decoration: none;
  }
  .toolbar a:hover { background: #f0f1f5; }
  .stats { display: flex; gap: 12px; margin-bottom: 20px; }
  .stat { background: white; border: 1px solid #e2e2e2; border-radius: 8px; padding: 12px 18px;
          flex: 1; }
  .stat .num { font-size: 22px; font-weight: 700; }
  .stat .label { font-size: 12px; color: #666; }
  .dashboard { display: flex; gap: 20px; align-items: stretch; margin-bottom: 20px; flex-wrap: wrap; }
  .dashboard > .donut-card, .dashboard > .metric-card { flex: 1 1 300px; }
  .donut-card { background: white; border: 1px solid #e2e2e2; border-radius: 8px; padding: 16px 20px;
                display: flex; flex-direction: column; }
  .donut-body { display: flex; align-items: center; gap: 20px; flex: 1; }
  .metric-card { background: white; border: 1px solid #e2e2e2; border-radius: 8px; padding: 16px 20px;
                 display: flex; flex-direction: column; }
  .metric-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
  .metric-card h2 { font-size: 13px; margin: 0; color: #52514e; font-weight: 600; }
  .cost-badge { font-size: 12px; font-weight: 700; color: #0ca30c; background: #eaf7ea;
                border-radius: 999px; padding: 3px 10px; font-variant-numeric: tabular-nums; }
  .metric-row { display: flex; gap: 10px; }
  .metric-tile { flex: 1; background: #f8f8f6; border: 1px solid #ececE6; border-top: 3px solid var(--mc, #ccc);
                 border-radius: 0 0 6px 6px; padding: 12px 12px; text-align: center; }
  .metric-tile .v { font-size: 21px; font-weight: 700; color: var(--mc, #1f2430); font-variant-numeric: tabular-nums; }
  .metric-tile .k { font-size: 10.5px; color: #898781; text-transform: uppercase; letter-spacing: .03em; margin-top: 3px; }
  .metric-empty { font-size: 12.5px; color: #b6b3aa; padding: 18px 0; text-align: center; }
  .lat-viz { display: flex; flex-direction: column; justify-content: center; gap: 14px; flex: 1; }
  .lat-row { display: flex; align-items: center; gap: 10px; }
  .lat-row .lbl { width: 28px; font-family: Consolas, monospace; font-size: 11.5px; font-weight: 700; flex-shrink: 0; }
  .lat-row .track { flex: 1; height: 16px; background: #f0f0ee; border-radius: 8px; overflow: hidden; }
  .lat-row .fill { height: 100%; border-radius: 8px; }
  .lat-row .val { font-size: 12.5px; font-weight: 700; color: #1f2430; flex-shrink: 0; min-width: 82px;
                   text-align: right; font-variant-numeric: tabular-nums; }
  .donut-card h2 { font-size: 13px; margin: 0 0 0 0; color: #52514e; font-weight: 600; }
  .donut-wrap { position: relative; width: 176px; height: 176px; flex-shrink: 0; }
  .donut { width: 176px; height: 176px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(0,0,0,.04); }
  .donut-count-label { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
                        font-size: 10.5px; font-weight: 700; color: #111;
                        white-space: nowrap; pointer-events: none; }
  .donut-hole { position: absolute; inset: 28px; background: white; border-radius: 50%;
                display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .donut-hole .n { font-size: 22px; font-weight: 700; color: #0b0b0b; }
  .donut-hole .l { font-size: 10px; color: #898781; }
  .legend { display: flex; flex-direction: column; gap: 10px; font-size: 12.5px; flex: 1; min-width: 0; }
  .legend .row { display: flex; align-items: center; gap: 9px; cursor: default; }
  .legend .swatch { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
  .legend .name { color: #1f2430; font-weight: 600; flex: 1; min-width: 0; }
  .legend .pct { color: #1f2430; font-weight: 700; font-variant-numeric: tabular-nums; flex-shrink: 0; }
  table { width: 100%; border-collapse: collapse; background: white; font-size: 12.5px; }
  th, td { border: 1px solid #e2e2e2; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f0f2f5; position: sticky; top: 0; }
  td.mono { font-family: Consolas, monospace; font-size: 11.5px; max-width: 320px;
            white-space: pre-wrap; word-break: break-word; }
  tr.blocked { background: #fffbea; }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 11px; }
  .badge.ok { background: #e6f4ea; color: #1a7f37; }
  .badge.blocked { background: #fdecea; color: #b3261e; }
  .gov-glossary { background: #f0f1fa; border: 1px solid #dcdef5; border-radius: 8px; padding: 10px 14px;
                  margin-bottom: 10px; font-size: 12px; color: #44475a; display: grid;
                  grid-template-columns: repeat(4, 1fr); gap: 4px 16px; }
  .gov-glossary strong { color: #1f2430; }
  .gov-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; align-items: stretch; }
  .gov-card { background: white; border: 1px solid #e2e2e2; border-left: 3px solid var(--gc, #4f46e5);
              border-radius: 8px; padding: 12px 14px; font-size: 12.5px; display: flex; flex-direction: column; gap: 5px; }
  .gov-card h3 { font-size: 12px; margin: 0 0 2px; color: var(--gc, #4f46e5); text-transform: uppercase;
                 letter-spacing: .03em; display: flex; align-items: center; gap: 6px; }
  .gov-card p { margin: 0; color: #3a3a3a; }
  .gov-card p strong { color: #111; }
  .gov-card ol { margin: 2px 0 0; padding-left: 16px; color: #3a3a3a; }
  .gov-card ol li { margin-bottom: 3px; }
  .stage-bar-card { background: white; border: 1px solid #e2e2e2; border-radius: 8px;
                     padding: 14px 18px; margin-bottom: 20px; }
  .stage-bar-card h2 { font-size: 13px; margin: 0 0 10px; color: #52514e; font-weight: 600; }
  .stage-bar { display: flex; width: 100%; height: 26px; border-radius: 6px; overflow: hidden;
               background: #e1e0d9; }
  .stage-bar .seg { display: flex; align-items: center; justify-content: center; color: white;
                     font-size: 11px; font-weight: 600; white-space: nowrap; overflow: hidden; }
  /* Ngoặc TỔNG nằm TRÊN thanh - mở xuống dưới (⎡‾‾⎤), 2 chân trỏ xuống chạm mép thanh */
  .stage-total { display: flex; flex-direction: column; align-items: center; }
  .stage-total .total-ms { font-size: 11.5px; font-weight: 700; color: #3a3a3a; margin-bottom: 3px; }
  .stage-total .bracket { width: 97%; height: 7px; border: 1.5px solid #9c9a90; border-bottom: none;
                           border-radius: 3px 3px 0 0; }
  /* Ngoặc từng giai đoạn nằm DƯỚI thanh - mở lên trên (⎣__⎦), 2 chân trỏ lên chạm mép thanh */
  .stage-dims { display: flex; width: 100%; }
  .stage-dims .dim { display: flex; flex-direction: column; align-items: center; }
  .stage-dims .bracket { width: 100%; height: 6px; border-radius: 0 0 3px 3px;
                          border: 1.5px solid #c7c5bb; border-top: none; box-sizing: border-box; }
  .stage-dims .ms { margin-top: 3px; font-size: 11px; font-weight: 700; color: #1f2430;
                     font-variant-numeric: tabular-nums; white-space: nowrap; }
  .stage-legend { display: flex; gap: 18px; margin-top: 14px; font-size: 12.5px; flex-wrap: wrap; }
  .stage-legend .row { display: flex; align-items: center; gap: 6px; }
  .stage-legend .swatch { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
  .stage-head { display: flex; justify-content: space-between; align-items: center;
                flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
  .stage-filter { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 12px; }
  .stage-filter a.fbtn, .stage-filter button {
    font: inherit; font-size: 12px; padding: 4px 10px; border-radius: 999px;
    border: 1px solid #d6d6d0; background: white; color: #333; text-decoration: none; cursor: pointer;
  }
  .stage-filter a.fbtn:hover, .stage-filter button:hover { background: #f0f1f5; }
  .stage-filter a.fbtn.active { background: #1f2430; color: white; border-color: #1f2430; }
  .stage-filter input[type=number] { width: 66px; padding: 3px 6px; border-radius: 6px; border: 1px solid #d6d6d0; font-size: 12px; }
  .row-pick { transform: scale(1.05); cursor: pointer; }
  th.pick-col, td.pick-col { text-align: center; width: 30px; }
  .log-search { background: white; border: 1px solid #e2e2e2; border-radius: 8px;
                padding: 10px 14px; margin-bottom: 10px; }
  .log-search-form { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; font-size: 12.5px; }
  .log-search-form label { display: flex; align-items: center; gap: 6px; color: #52514e; }
  .log-search-form select, .log-search-form input[type=date] {
    font: inherit; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; border: 1px solid #d6d6d0;
  }
  .log-search-form button {
    font: inherit; font-size: 12.5px; padding: 5px 14px; border-radius: 999px;
    border: 1px solid #d6d6d0; background: white; color: #1f2430; cursor: pointer;
  }
  .log-search-form button:hover { background: #f0f1f5; }
  .log-search-form .clear-link { color: #b3261e; text-decoration: none; }
  .log-search-form .clear-link:hover { text-decoration: underline; }
  .log-search-form .result-hint { color: #898781; margin-left: auto; }
</style>
</head>
<body>
  <h1>Admin Monitor - NL2SQL Agent</h1>
  <div class="toolbar"><a href="/">&larr; Về trang chat</a><a href="/admin">Làm mới</a></div>
  <div class="stats">
    <div class="stat"><div class="num">{{ stats.total }}</div><div class="label">💬 Tổng số câu hỏi</div></div>
    <div class="stat"><div class="num">{{ stats.blocked }}</div><div class="label">🛡️ Bị chặn (guardrail/validator)</div></div>
    <div class="stat"><div class="num">{{ stats.avg_ms }} ms</div><div class="label">⏱️ Thời gian xử lý trung bình (câu thành công)</div></div>
    <div class="stat"><div class="num">👍 {{ feedback_stats.up }} / 👎 {{ feedback_stats.down }}</div><div class="label">Đánh giá của user (thumbs up/down)</div></div>
  </div>
  <div class="dashboard">
    <div class="donut-card">
      <div class="metric-head"><h2>📊 Trạng thái request</h2></div>
      <div class="donut-body">
        <div class="donut-wrap">
          <div class="donut" style="background: {{ donut_gradient }};" role="img"
               aria-label="Tỷ lệ request theo trạng thái"></div>
          {% for s in donut_slices %}
          <div class="donut-count-label" style="transform: translate(calc(-50% + {{ s.label_x }}px), calc(-50% + {{ s.label_y }}px));">{{ s.count }}</div>
          {% endfor %}
          <div class="donut-hole"><div class="n">{{ donut_total }}</div><div class="l">request</div></div>
        </div>
        <div class="legend">
          {% if donut_slices %}
            {% for s in donut_slices %}
            <div class="row" title="{{ s.detail }}">
              <span class="swatch" style="background: {{ s.color }};"></span>
              <span class="name">{{ s.label }}</span>
              <span class="pct">{{ s.pct }}%</span>
            </div>
            {% endfor %}
          {% else %}
            <div class="row"><span class="name">Chưa có dữ liệu.</span></div>
          {% endif %}
        </div>
      </div>
    </div>

    <div class="metric-card">
      <div class="metric-head">
        <h2 title="Thang màu tính theo % ngân sách timeout của pipeline (2 lần gọi LLM + 1 lần query DB) - không phải so P50/P90/P99 với nhau, để phản ánh đúng nhanh/chậm thực tế.">⏱ Độ trễ theo percentile</h2>
      </div>
      {% if latency_bars %}
      <div class="lat-viz">
        {% for b in latency_bars %}
        <div class="lat-row">
          <span class="lbl" style="color: {{ b.color }};">{{ b.label }}</span>
          <div class="track"><div class="fill" style="width: {{ b.pct }}%; background: {{ b.color }};"></div></div>
          <span class="val">{{ b.ms }} ms</span>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <div class="metric-empty">Chưa có dữ liệu</div>
      {% endif %}
    </div>

    <div class="metric-card">
      <div class="metric-head">
        <h2>🪙 Token &amp; chi phí</h2>
        {% if cost_estimate %}
          <span class="cost-badge" title="Theo giá cấu hình trong .env, trên {{ token_stats.requests_with_usage }} request có gọi LLM">≈ ${{ '%.4f'|format(cost_estimate) }}</span>
        {% endif %}
      </div>
      {% if token_stats.requests_with_usage %}
      <div class="metric-row">
        <div class="metric-tile"><div class="v">{{ '{:,}'.format(token_stats.input_tokens) }}</div><div class="k">Input</div></div>
        <div class="metric-tile"><div class="v">{{ '{:,}'.format(token_stats.output_tokens) }}</div><div class="k">Output</div></div>
        <div class="metric-tile" title="Token đọc từ cache (rẻ hơn nhiều so với input token thường)"><div class="v">{{ '{:,}'.format(token_stats.cache_read_tokens) }}</div><div class="k">Cache-read</div></div>
      </div>
      {% else %}
      <div class="metric-empty">Chưa có dữ liệu</div>
      {% endif %}
    </div>
  </div>

  <div class="gov-glossary">
    <span><strong>Knowledge Cutoff</strong> — mốc kiến thức huấn luyện của model AI.</span>
    <span><strong>Data Freshness</strong> — dữ liệu được ghi/cập nhật lần cuối khi nào.</span>
    <span><strong>Data Provenance</strong> — dữ liệu đến từ đâu, ai nạp/xử lý.</span>
    <span><strong>Data Lineage</strong> — dòng chảy xử lý dữ liệu từ nguồn tới câu trả lời.</span>
  </div>

  <div class="gov-grid">
    <div class="gov-card" style="--gc:#4f46e5;">
      <h3>🧠 Knowledge Cutoff</h3>
      <p><strong>{{ model_info.provider }}/{{ model_info.model }}</strong></p>
      <p>Mốc kiến thức: {{ model_info.knowledge_cutoff }}</p>
    </div>
    <div class="gov-card" style="--gc:#2563eb;">
      <h3>🕒 Data Freshness</h3>
      <p>Cập nhật lần cuối: <strong>{{ freshness.last_data_update }}</strong></p>
      <p>Nội dung phủ tới năm: {{ freshness.content_coverage_year }}</p>
      <p>{{ freshness.total_rows }} dòng doanh số</p>
    </div>
    <div class="gov-card" style="--gc:#7c3aed;">
      <h3>📦 Data Provenance</h3>
      <p>Dataset gốc: <strong>Video Game Sales</strong></p>
      <p>Nạp qua G7_Dbscript.sql (quantl3@fpt.edu.vn)</p>
      <p>Ràng buộc: Vi · Index/view NL2SQL: Hoàng</p>
    </div>
    <div class="gov-card" style="--gc:#0891b2;">
      <h3>🔗 Data Lineage</h3>
      <ol>
        <li>Tạo bảng + insert (G7_Dbscript.sql)</li>
        <li>Ràng buộc (02_constraints.sql)</li>
        <li>Index (09_indexes.sql)</li>
        <li>View vw_game_sales_full</li>
        <li>NL2SQL Agent → LLM → trả lời</li>
      </ol>
    </div>
  </div>

  <div class="stage-bar-card">
    <div class="stage-head">
      <h2 style="margin:0;">Thời gian xử lý trung bình theo giai đoạn</h2>
      <div class="stage-filter" id="stageFilter">
        {% for preset in ['10', '50', '100', 'all'] %}
          <a class="fbtn {{ 'active' if stage_n == preset else '' }}" href="/admin?n={{ preset }}" data-n="{{ preset }}">{{ 'Tất cả' if preset == 'all' else preset + ' gần nhất' }}</a>
        {% endfor %}
        <form method="get" action="/admin" id="stageCustomForm" style="display:inline-flex; gap:4px;">
          <input type="number" name="n" min="1" placeholder="Tuỳ chỉnh N">
          <button type="submit">Xem</button>
        </form>
      </div>
    </div>
    {% if stage_total %}
    <div class="stage-total">
      <div class="total-ms" id="stageTotalMs">Tổng: {{ stage_total }} ms</div>
      <div class="bracket"></div>
    </div>
    <div class="stage-bar" id="stageBar" role="img" aria-label="Phân bổ thời gian xử lý theo từng giai đoạn">
      {% for s in stage_segments %}
        {% if s.ms > 0 %}
        <div class="seg" style="width: {{ s.pct }}%; background: {{ s.color }};"
             title="{{ s.label }}: {{ s.ms }} ms ({{ s.pct }}%)">
          {% if s.pct >= 8 %}{{ s.pct }}%{% endif %}
        </div>
        {% endif %}
      {% endfor %}
    </div>
    <div class="stage-dims" id="stageDims">
      {% for s in stage_segments %}
        {% if s.ms > 0 %}
        <div class="dim" style="width: {{ s.pct }}%;">
          <div class="bracket" style="border-color: {{ s.color }};"></div>
          <div class="ms">{{ s.ms }} ms</div>
        </div>
        {% endif %}
      {% endfor %}
    </div>
    <div class="stage-legend">
      {% for s in stage_segments %}
      <div class="row">
        <span class="swatch" style="background: {{ s.color }};"></span>
        <span>{{ s.label }}</span>
      </div>
      {% endfor %}
    </div>
    <script>
      window.__stageDefaultAvg = {
        gen: {{ stage_segments[0].ms }},
        db: {{ stage_segments[1].ms }},
        explain: {{ stage_segments[2].ms }}
      };
    </script>
    {% else %}
    <div style="font-size: 12.5px; color: #898781;">Chưa có dữ liệu.</div>
    {% endif %}
  </div>

  <div class="log-search">
    <form method="get" action="/admin" class="log-search-form">
      {% if stage_n %}<input type="hidden" name="n" value="{{ stage_n }}">{% endif %}
      <label>Trạng thái
        <select name="status">
          <option value="" {{ 'selected' if not status_filter else '' }}>Tất cả</option>
          <option value="ok" {{ 'selected' if status_filter == 'ok' else '' }}>Thành công</option>
          <option value="blocked" {{ 'selected' if status_filter == 'blocked' else '' }}>Bị chặn theo thiết kế</option>
          <option value="error" {{ 'selected' if status_filter == 'error' else '' }}>Lỗi hạ tầng</option>
        </select>
      </label>
      <label>Từ ngày <input type="date" name="date_from" value="{{ date_from }}"></label>
      <label>Đến ngày <input type="date" name="date_to" value="{{ date_to }}"></label>
      <button type="submit">Tìm</button>
      {% if status_filter or date_from or date_to %}
        <a class="clear-link" href="/admin{{ '?n=' + stage_n if stage_n else '' }}">Xoá lọc</a>
      {% endif %}
      <span class="result-hint">{{ logs|length }} dòng khớp (tối đa 200)</span>
    </form>
  </div>

  <table>
    <thead>
      <tr>
        <th class="pick-col">Chọn</th>
        <th>Thời gian</th><th>Câu hỏi</th><th>Trạng thái</th><th>Đánh giá</th><th>SQL đã sinh</th>
        <th>SQL sau validate</th><th>Số dòng</th><th>Câu trả lời</th>
        <th>LLM sinh SQL (ms)</th><th>DB exec (ms)</th><th>LLM diễn giải (ms)</th><th>Tổng (ms)</th>
      </tr>
    </thead>
    <tbody>
    {% for r in logs %}
      <tr class="{{ 'blocked' if r.blocked else '' }}">
        <td class="pick-col">
          {% if not r.blocked %}
          <input type="checkbox" class="row-pick" title="Dùng dòng này để tính thanh breakdown ở trên"
                 data-ms-gen="{{ r.ms_generate_sql or 0 }}" data-ms-db="{{ r.ms_db_exec or 0 }}"
                 data-ms-explain="{{ r.ms_explain or 0 }}">
          {% endif %}
        </td>
        <td>{{ r.created_at }}</td>
        <td>{{ r.question }}</td>
        <td>
          {% if r.blocked %}
            <span class="badge blocked">BLOCKED - {{ r.block_stage }}</span><br>{{ r.reason }}
          {% else %}
            <span class="badge ok">OK</span>
          {% endif %}
        </td>
        <td>{% if r.feedback == 'up' %}👍{% elif r.feedback == 'down' %}👎{% endif %}</td>
        <td class="mono">{{ r.raw_sql }}</td>
        <td class="mono">{{ r.safe_sql }}</td>
        <td>{{ r.row_count }}</td>
        <td>{{ r.answer }}</td>
        <td>{{ r.ms_generate_sql }}</td>
        <td>{{ r.ms_db_exec }}</td>
        <td>{{ r.ms_explain }}</td>
        <td>{{ r.ms_total }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <script>
  (function () {
    var STAGE_META = [
      { key: 'gen', label: 'LLM sinh SQL', color: '#4f46e5' },
      { key: 'db', label: 'DB thực thi', color: '#0891b2' },
      { key: 'explain', label: 'LLM diễn giải', color: '#d97706' }
    ];
    var boxes = document.querySelectorAll('.row-pick');
    var bar = document.getElementById('stageBar');
    var dims = document.getElementById('stageDims');
    var totalMs = document.getElementById('stageTotalMs');
    var filterEl = document.getElementById('stageFilter');
    var customForm = document.getElementById('stageCustomForm');

    function render(avg) {
      if (!bar || !dims || !totalMs) return;
      var total = avg.gen + avg.db + avg.explain;
      bar.innerHTML = '';
      dims.innerHTML = '';
      STAGE_META.forEach(function (m) {
        var ms = avg[m.key];
        if (ms <= 0) return;
        var pct = total ? (ms / total * 100) : 0;
        var seg = document.createElement('div');
        seg.className = 'seg';
        seg.style.width = pct + '%';
        seg.style.background = m.color;
        seg.title = m.label + ': ' + ms + ' ms (' + pct.toFixed(1) + '%)';
        if (pct >= 8) seg.textContent = pct.toFixed(1) + '%';
        bar.appendChild(seg);

        var dim = document.createElement('div');
        dim.className = 'dim';
        dim.style.width = pct + '%';
        var bracket = document.createElement('div');
        bracket.className = 'bracket';
        bracket.style.borderColor = m.color;
        var msLabel = document.createElement('div');
        msLabel.className = 'ms';
        msLabel.textContent = ms + ' ms';
        dim.appendChild(bracket);
        dim.appendChild(msLabel);
        dims.appendChild(dim);
      });
      totalMs.textContent = 'Tổng: ' + total + ' ms';
    }

    // --- tick tay tung dong trong bang log: tinh lai avg tu cac dong da chon ---
    function recomputeFromCheckboxes() {
      var picked = Array.prototype.filter.call(boxes, function (c) { return c.checked; });
      if (!picked.length) {
        render(window.__stageDefaultAvg);
        return;
      }
      var sums = { gen: 0, db: 0, explain: 0 };
      picked.forEach(function (c) {
        sums.gen += parseFloat(c.getAttribute('data-ms-gen') || 0);
        sums.db += parseFloat(c.getAttribute('data-ms-db') || 0);
        sums.explain += parseFloat(c.getAttribute('data-ms-explain') || 0);
      });
      var n = picked.length;
      var avg = {
        gen: Math.round(sums.gen / n),
        db: Math.round(sums.db / n),
        explain: Math.round(sums.explain / n)
      };
      render(avg);
    }
    boxes.forEach(function (c) { c.addEventListener('change', recomputeFromCheckboxes); });

    // --- nut/form chon N request gan nhat: fetch() thay vi dieu huong ca trang,
    // de bam khong bi reload/nhay len dau trang ---
    function setActiveButton(nStr) {
      if (!filterEl) return;
      Array.prototype.forEach.call(filterEl.querySelectorAll('.fbtn'), function (a) {
        a.classList.toggle('active', a.getAttribute('data-n') === nStr);
      });
    }

    function applyStageData(data) {
      if (!bar) { window.location.href = '/admin?n=' + encodeURIComponent(data.n); return; }
      var avg = {
        gen: data.segments[0] ? data.segments[0].ms : 0,
        db: data.segments[1] ? data.segments[1].ms : 0,
        explain: data.segments[2] ? data.segments[2].ms : 0,
      };
      window.__stageDefaultAvg = avg;
      Array.prototype.forEach.call(boxes, function (c) { c.checked = false; });
      render(avg);
      setActiveButton(data.n);
    }

    function loadStage(n, pushUrl) {
      fetch('/admin/stage-bar?n=' + encodeURIComponent(n))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          applyStageData(data);
          if (pushUrl !== false) {
            var url = new URL(window.location);
            url.searchParams.set('n', data.n);
            history.pushState({ n: data.n }, '', url);
          }
        })
        .catch(function () { window.location.href = '/admin?n=' + encodeURIComponent(n); });
    }

    if (filterEl) {
      Array.prototype.forEach.call(filterEl.querySelectorAll('.fbtn'), function (a) {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          loadStage(a.getAttribute('data-n'));
        });
      });
    }
    if (customForm) {
      customForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var val = customForm.querySelector('input[name=n]').value;
        if (val) loadStage(val);
      });
    }
    window.addEventListener('popstate', function () {
      var n = new URL(window.location).searchParams.get('n') || '10';
      loadStage(n, false);
    });
  })();
  </script>
</body>
</html>
"""


# 3 nhom - dung dung bo mau status (good/warning/critical) theo dataviz
# skill: da chay validate_palette.js voi 6 mau tach rieng tung block_stage,
# KHONG mau nao qua duoc kiem tra all-pairs (chinh tai lieu skill xac nhan
# qua 3 slot categorical la het an toan) - nen gop lai con 3 nhom co y nghia
# ro rang, dung dung role "status" (luon di kem nhan chu + so luong trong
# legend, day la bien phap giam thieu chinh thuc cho mau status theo skill,
# khong phai boi vi status duoc mien kiem tra CVD). Chi tiet tung loai chan
# (injection/ngoai pham vi/SQL loi/hallucination) van xem day du o bang log.
STATUS_META = [
    ("ok", "Thành công", "Guardrail/validator không chặn, trả lời bình thường", "#0ca30c"),
    ("blocked_by_design", "Bị chặn theo thiết kế", "Guardrail hoặc SQL validator chủ động chặn", "#fab219"),
    ("service_error", "Lỗi hạ tầng", "Timeout / mất kết nối LLM hoặc database", "#d03b3b"),
]

_BLOCKED_BY_DESIGN = {
    "input_guardrail", "llm_not_applicable", "sql_validator", "output_guardrail",
}


def _build_donut():
    raw_counts = {r["status"]: r["count"] for r in logging_store.fetch_status_breakdown()}
    counts = {"ok": 0, "blocked_by_design": 0, "service_error": 0}
    for status, n in raw_counts.items():
        if status in _BLOCKED_BY_DESIGN:
            counts["blocked_by_design"] += n
        elif status in counts:
            counts[status] += n
    total = sum(counts.values())

    slices = []
    for status, label, detail, color in STATUS_META:
        n = counts.get(status, 0)
        if n:
            slices.append(
                {"status": status, "label": label, "detail": detail, "color": color,
                 "count": n, "pct": round(n / total * 100, 1) if total else 0}
            )

    # Dat SO LUONG (khong phai %) ngay tren vanh mau - % chi hien o legend, tranh
    # trung lap thong tin. Ban kinh giua vanh: donut rong 176px, lo giua inset
    # 28px -> vanh tu r=60 den r=88, lay r=74 lam tam vanh de dat nhan.
    import math

    RING_MID_R = 74
    stops = []
    angle = 0.0
    for s in slices:
        span = (s["count"] / total * 360) if total else 0
        start, end = angle, angle + span
        stops.append(f"{s['color']} {start:.2f}deg {end:.2f}deg")
        mid_rad = math.radians((start + end) / 2)
        s["label_x"] = round(RING_MID_R * math.sin(mid_rad), 1)
        s["label_y"] = round(-RING_MID_R * math.cos(mid_rad), 1)
        angle = end
    gradient_css = (
        "conic-gradient(" + ", ".join(stops) + ")" if stops else "#e1e0d9"
    )
    return slices, gradient_css, total


# 3 giai đoạn của pipeline (agent.py): LLM sinh SQL -> DB thực thi -> LLM diễn
# giải kết quả. Cùng dùng bộ 3 màu categorical tách biệt donut/status ở trên để
# tránh nhầm 2 nhóm biểu đồ khác ý nghĩa với nhau.
STAGE_META = [
    ("generate_sql", "LLM sinh SQL", "#4f46e5"),
    ("db_exec", "DB thực thi", "#0891b2"),
    ("explain", "LLM diễn giải", "#d97706"),
]


# Preset cho bo loc "N request thanh cong gan nhat" tren thanh breakdown thoi
# gian - "10" la mac dinh (mau nho, phan anh dung hieu nang HIEN TAI, khong bi
# cac request rat cu truoc khi toi uu index/prompt keo lech trung binh).
_STAGE_N_DEFAULT = "10"
_STAGE_N_PRESETS = {"10", "50", "100", "all"}


def _parse_stage_n(raw: str) -> tuple:
    """Tra ve (limit, label) - limit=None nghia la khong gioi han (tat ca)."""
    raw = (raw or _STAGE_N_DEFAULT).strip().lower()
    if raw == "all":
        return None, "all"
    try:
        n = int(raw)
        if n > 0:
            return n, str(n)
    except ValueError:
        pass
    return 10, "10"


def _build_stage_bar(limit: int = None):
    avg = logging_store.fetch_stage_avg_ms(limit=limit)
    count = avg.pop("count")
    total = sum(avg.values())
    segments = [
        {
            "label": label,
            "color": color,
            "ms": avg[key],
            "pct": round(avg[key] / total * 100, 1) if total else 0,
        }
        for key, label, color in STAGE_META
    ]
    return segments, total, count


@app.route("/admin/stage-bar")
@require_admin_auth
def admin_stage_bar():
    """JSON cho bộ lọc N-gần-nhất trên /admin - gọi bằng fetch() từ JS thay vì
    điều hướng cả trang, để bấm nút không bị reload/nhảy lên đầu trang.
    """
    stage_limit, stage_n = _parse_stage_n(request.args.get("n"))
    segments, total, count = _build_stage_bar(limit=stage_limit)
    return jsonify({
        "n": stage_n,
        "count": count,
        "total": total,
        "segments": segments,
    })


def _cost_estimate(token_stats: dict) -> float:
    """None nếu chưa cấu hình giá trong .env (xem config.py) - trả về số $0
    trong trường hợp đó sẽ trông như 1 con số thật, gây hiểu lầm là miễn phí."""
    if not CONFIG.price_per_1m_input and not CONFIG.price_per_1m_output:
        return None
    return (
        token_stats["input_tokens"] * CONFIG.price_per_1m_input
        + token_stats["output_tokens"] * CONFIG.price_per_1m_output
    ) / 1_000_000


# Ngan sach thoi gian toi da 1 request co the chay truoc khi CHINH HE THONG tu
# timeout: 2 lan goi LLM (generate_sql + explain_result, moi lan toi da
# llm_client.REQUEST_TIMEOUT_SECONDS) + 1 lan query DB (CONFIG.query_timeout_seconds).
# Dung moc nay lam "thang do tuyet doi" cho bieu do do tre thay vi so P50/P90/P99
# VOI NHAU - neu chi so sanh noi bo, hinh dang 3 thanh se LUON giong nhau bat ke
# he thong dang nhanh hay cham, khong tra loi duoc "vay la tot hay xau".
_LATENCY_CEILING_MS = (llm_client.REQUEST_TIMEOUT_SECONDS * 2 + CONFIG.query_timeout_seconds) * 1000


def _latency_bars(percentiles: dict) -> list:
    bars = []
    for label, val in (("P50", percentiles["p50"]), ("P90", percentiles["p90"]), ("P99", percentiles["p99"])):
        ratio = (val / _LATENCY_CEILING_MS) if _LATENCY_CEILING_MS else 0
        if ratio < 0.33:
            color = "#0ca30c"
        elif ratio < 0.66:
            color = "#fab219"
        else:
            color = "#d03b3b"
        bars.append({"label": label, "ms": val, "pct": max(min(ratio * 100, 100), 3), "color": color})
    return bars


@app.route("/admin")
@require_admin_auth
def admin():
    status_filter = (request.args.get("status") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    logs = logging_store.fetch_recent(
        limit=200,
        status=status_filter or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    stats = logging_store.fetch_stats()
    feedback_stats = logging_store.fetch_feedback_stats()
    donut_slices, donut_gradient, donut_total = _build_donut()
    stage_limit, stage_n = _parse_stage_n(request.args.get("n"))
    stage_segments, stage_total, stage_count = _build_stage_bar(limit=stage_limit)
    percentiles = logging_store.fetch_latency_percentiles()
    latency_bars = _latency_bars(percentiles) if percentiles["count"] else []
    token_stats = logging_store.fetch_token_stats()
    try:
        freshness = db.get_data_freshness()
    except Exception as exc:
        freshness = {"content_coverage_year": "?", "total_rows": "?", "last_data_update": f"lỗi: {exc}"}
    return render_template_string(
        ADMIN_PAGE,
        logs=logs,
        stats=stats,
        feedback_stats=feedback_stats,
        donut_slices=donut_slices,
        donut_gradient=donut_gradient,
        donut_total=donut_total,
        stage_segments=stage_segments,
        stage_total=stage_total,
        stage_count=stage_count,
        stage_n=stage_n,
        percentiles=percentiles,
        latency_bars=latency_bars,
        token_stats=token_stats,
        cost_estimate=_cost_estimate(token_stats),
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        model_info=llm_client.get_model_info(),
        freshness=freshness,
    )


if __name__ == "__main__":
    import os

    # 0.0.0.0 de Docker port-forward duoc; van truy cap binh thuong qua
    # 127.0.0.1 khi chay local (khong Docker).
    host = os.getenv("WEBAPP_HOST", "0.0.0.0")
    debug = os.getenv("WEBAPP_DEBUG", "1") == "1"
    # threaded=True: neu 1 request /ask dang bi client huy (nut "Dung") nhung
    # van con chay ngam o server, request /ask tiep theo khong bi ket lai cho.
    app.run(host=host, port=5050, debug=debug, threaded=True)
