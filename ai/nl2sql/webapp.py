"""Web demo (nội bộ) cho NL2SQL Agent - chat hỏi đáp dữ liệu doanh số game.

Chạy: python -m ai.nl2sql.webapp
Mở trình duyệt: http://127.0.0.1:5050
Trang admin (xem log toàn bộ luồng xử lý): http://127.0.0.1:5050/admin
  - Đăng nhập bằng ADMIN_USER/ADMIN_PASSWORD trong ai/.env.
"""
import functools

from flask import Flask, Response, jsonify, render_template_string, request

from . import agent, db, llm_client, logging_store
from .config import CONFIG

app = Flask(__name__)


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
  h1 { font-size: 20px; margin-bottom: 16px; }
  .stats { display: flex; gap: 12px; margin-bottom: 20px; }
  .stat { background: white; border: 1px solid #e2e2e2; border-radius: 8px; padding: 12px 18px; }
  .stat .num { font-size: 22px; font-weight: 700; }
  .stat .label { font-size: 12px; color: #666; }
  .dashboard { display: flex; gap: 20px; align-items: stretch; margin-bottom: 20px; }
  .donut-card { background: white; border: 1px solid #e2e2e2; border-radius: 8px; padding: 16px 20px;
                display: flex; align-items: center; gap: 20px; }
  .donut-card h2 { font-size: 13px; margin: 0 0 0 0; color: #52514e; font-weight: 600; }
  .donut-wrap { position: relative; width: 140px; height: 140px; flex-shrink: 0; }
  .donut { width: 140px; height: 140px; border-radius: 50%; }
  .donut-hole { position: absolute; inset: 22px; background: white; border-radius: 50%;
                display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .donut-hole .n { font-size: 22px; font-weight: 700; color: #0b0b0b; }
  .donut-hole .l { font-size: 10px; color: #898781; }
  .legend { display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; }
  .legend .row { display: flex; align-items: center; gap: 8px; }
  .legend .swatch { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
  .legend .name { color: #1f2430; }
  .legend .count { color: #898781; margin-left: auto; padding-left: 14px; font-variant-numeric: tabular-nums; }
  table { width: 100%; border-collapse: collapse; background: white; font-size: 12.5px; }
  th, td { border: 1px solid #e2e2e2; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #f0f2f5; position: sticky; top: 0; }
  td.mono { font-family: Consolas, monospace; font-size: 11.5px; max-width: 320px;
            white-space: pre-wrap; word-break: break-word; }
  tr.blocked { background: #fffbea; }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 11px; }
  .badge.ok { background: #e6f4ea; color: #1a7f37; }
  .badge.blocked { background: #fdecea; color: #b3261e; }
  .toolbar { margin-bottom: 12px; font-size: 13px; }
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
</style>
</head>
<body>
  <h1>Admin monitor - NL2SQL Agent (Group7 Video Game Sales)</h1>
  <div class="toolbar"><a href="/">&larr; Về trang chat</a> &middot; <a href="/admin">Làm mới</a> &middot; tự làm mới mỗi 45s</div>
  <div class="stats">
    <div class="stat"><div class="num">{{ stats.total }}</div><div class="label">Tổng số câu hỏi</div></div>
    <div class="stat"><div class="num">{{ stats.blocked }}</div><div class="label">Bị chặn (guardrail/validator)</div></div>
    <div class="stat"><div class="num">{{ stats.avg_ms }} ms</div><div class="label">Thời gian xử lý trung bình (câu thành công)</div></div>
    <div class="stat"><div class="num">👍 {{ feedback_stats.up }} / 👎 {{ feedback_stats.down }}</div><div class="label">Đánh giá của user (thumbs up/down)</div></div>
  </div>
  <div class="dashboard">
    <div class="donut-card">
      <div class="donut-wrap">
        <div class="donut" style="background: {{ donut_gradient }};" role="img"
             aria-label="Tỷ lệ request theo trạng thái"></div>
        <div class="donut-hole"><div class="n">{{ donut_total }}</div><div class="l">request</div></div>
      </div>
      <div class="legend">
        {% if donut_slices %}
          {% for s in donut_slices %}
          <div class="row">
            <span class="swatch" style="background: {{ s.color }};"></span>
            <span class="name">{{ s.label }}</span>
            <span class="count">{{ s.count }} ({{ s.pct }}%)</span>
          </div>
          {% endfor %}
        {% else %}
          <div class="row"><span class="name">Chưa có dữ liệu.</span></div>
        {% endif %}
      </div>
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

  <table>
    <thead>
      <tr>
        <th>Thời gian</th><th>Câu hỏi</th><th>Trạng thái</th><th>Đánh giá</th><th>SQL đã sinh</th>
        <th>SQL sau validate</th><th>Số dòng</th><th>Câu trả lời</th>
        <th>LLM sinh SQL (ms)</th><th>DB exec (ms)</th><th>LLM diễn giải (ms)</th><th>Tổng (ms)</th>
      </tr>
    </thead>
    <tbody>
    {% for r in logs %}
      <tr class="{{ 'blocked' if r.blocked else '' }}">
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
    ("ok", "Thành công", "#0ca30c"),
    ("blocked_by_design", "Bị chặn theo thiết kế (guardrail/validator)", "#fab219"),
    ("service_error", "Lỗi hạ tầng (timeout/mất kết nối)", "#d03b3b"),
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
    for status, label, color in STATUS_META:
        n = counts.get(status, 0)
        if n:
            slices.append(
                {"status": status, "label": label, "color": color, "count": n,
                 "pct": round(n / total * 100, 1) if total else 0}
            )

    stops = []
    angle = 0.0
    for s in slices:
        start, end = angle, angle + (s["count"] / total * 360 if total else 0)
        stops.append(f"{s['color']} {start:.2f}deg {end:.2f}deg")
        angle = end
    gradient_css = (
        "conic-gradient(" + ", ".join(stops) + ")" if stops else "#e1e0d9"
    )
    return slices, gradient_css, total


@app.route("/admin")
@require_admin_auth
def admin():
    logs = logging_store.fetch_recent(limit=200)
    stats = logging_store.fetch_stats()
    feedback_stats = logging_store.fetch_feedback_stats()
    donut_slices, donut_gradient, donut_total = _build_donut()
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
