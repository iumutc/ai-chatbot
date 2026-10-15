TEST_UI_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Chatbot Test UI</title>
  <style>
    :root {
      --bg: #f4efe7;
      --panel: #fffaf2;
      --line: #d9cdbb;
      --text: #1c1a17;
      --muted: #6f6559;
      --accent: #b85c38;
      --accent-2: #355c7d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, #f9e7cf 0, transparent 28%),
        linear-gradient(135deg, #f4efe7, #efe3d2 55%, #e5d6c1 100%);
      color: var(--text);
      min-height: 100vh;
    }
    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      min-height: 100vh;
    }
    .sidebar, .main {
      padding: 24px;
    }
    .sidebar {
      border-right: 1px solid var(--line);
      background: rgba(255, 250, 242, 0.82);
      backdrop-filter: blur(8px);
    }
    .brand {
      margin-bottom: 18px;
    }
    .brand h1 {
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0.02em;
    }
    .brand p, .meta {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 12px 30px rgba(61, 44, 23, 0.08);
    }
    .sidebar .panel + .panel, .main .panel + .panel {
      margin-top: 18px;
    }
    label {
      display: block;
      margin-bottom: 10px;
      font-size: 13px;
      color: var(--muted);
    }
    input, select, textarea, button {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      font: inherit;
      background: #fff;
      color: var(--text);
    }
    textarea {
      min-height: 92px;
      resize: vertical;
    }
    button {
      background: var(--accent);
      color: #fff7f0;
      cursor: pointer;
      transition: transform 120ms ease, opacity 120ms ease;
      border: none;
    }
    button.secondary {
      background: var(--accent-2);
    }
    button:hover { transform: translateY(-1px); }
    button:disabled { opacity: 0.6; cursor: wait; }
    .conversation-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-height: 50vh;
      overflow: auto;
    }
    .conversation-item {
      padding: 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fffcf7;
      text-align: left;
    }
    .conversation-item.active {
      border-color: var(--accent);
      background: #fff2e8;
    }
    .conversation-title {
      font-size: 15px;
      margin-bottom: 4px;
    }
    .chat-wrap {
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 18px;
      height: calc(100vh - 48px);
    }
    .messages {
      overflow: auto;
      padding-right: 8px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .message {
      max-width: 78%;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid var(--line);
      line-height: 1.5;
      white-space: pre-wrap;
      animation: rise 180ms ease;
    }
    .message.user {
      align-self: flex-end;
      background: #2d4f66;
      border-color: #2d4f66;
      color: #f6efe6;
    }
    .message.assistant {
      align-self: flex-start;
      background: #fffaf3;
    }
    .message.system {
      align-self: center;
      background: #f2e9dd;
      color: var(--muted);
      font-size: 13px;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .footer-note {
      font-size: 13px;
      color: var(--muted);
      margin-top: 8px;
    }
    @keyframes rise {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (max-width: 960px) {
      .layout { grid-template-columns: 1fr; }
      .sidebar { border-right: none; border-bottom: 1px solid var(--line); }
      .chat-wrap { height: auto; min-height: 70vh; }
      .message { max-width: 100%; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <h1>Chatbot Lab</h1>
        <p>Konusma, kanal ve urun baglamini birlikte test edin.</p>
      </div>

      <div class="panel">
        <div class="meta">Yeni konusma</div>
        <label>Baslik
          <input id="title" placeholder="Orn. Pamuk tisort sorulari">
        </label>
        <div class="row">
          <label>Kanal
            <select id="channel">
              <option value="site">site</option>
              <option value="trendyol">trendyol</option>
              <option value="amazon">amazon</option>
              <option value="hepsiburada">hepsiburada</option>
            </select>
          </label>
          <label>Dil
            <input id="language" value="tr">
          </label>
        </div>
        <div class="row">
          <label>Product ID
            <input id="productId" placeholder="1001">
          </label>
          <label>Marketplace
            <input id="marketplace" placeholder="trendyol">
          </label>
        </div>
        <button id="createBtn">Konusma Olustur</button>
        <div class="footer-note">Yeni mesajlar secili konusmaya yazilir.</div>
      </div>

      <div class="panel">
        <div class="meta">Konusmalar</div>
        <div id="conversationList" class="conversation-list"></div>
      </div>
    </aside>

    <main class="main">
      <div class="chat-wrap panel">
        <div>
          <div id="chatTitle" class="brand">
            <h1 style="font-size:24px; margin-bottom:4px;">Konusma secilmedi</h1>
            <p id="chatMeta">Soldan bir konusma olustur veya sec.</p>
          </div>
        </div>

        <div id="messages" class="messages"></div>

        <div>
          <label>Mesaj
            <textarea id="messageInput" placeholder="Kullanici sorusunu yazin..."></textarea>
          </label>
          <button id="sendBtn" class="secondary">Mesaj Gonder</button>
        </div>
      </div>
    </main>
  </div>

  <script>
    let currentConversationId = null;

    async function loadConversations() {
      const res = await fetch('/conversations');
      const data = await res.json();
      const list = document.getElementById('conversationList');
      list.innerHTML = '';

      data.conversations.forEach((conv) => {
        const button = document.createElement('button');
        button.className = 'conversation-item' + (conv.id === currentConversationId ? ' active' : '');
        button.innerHTML = `
          <div class="conversation-title">${escapeHtml(conv.title)}</div>
          <div class="meta">#${conv.id} - ${escapeHtml(conv.channel)}${conv.product_id ? ' - urun ' + escapeHtml(conv.product_id) : ''}</div>
        `;
        button.onclick = () => selectConversation(conv.id);
        list.appendChild(button);
      });
    }

    async function selectConversation(id) {
      currentConversationId = id;
      await loadConversations();
      const res = await fetch(`/conversations/${id}`);
      const data = await res.json();

      document.querySelector('#chatTitle h1').textContent = data.conversation.title;
      document.getElementById('chatMeta').textContent = `${data.conversation.channel} | product_id: ${data.conversation.product_id || '-'} | marketplace: ${data.conversation.marketplace || '-'}`;

      const messages = document.getElementById('messages');
      messages.innerHTML = '';
      data.messages.forEach(renderMessage);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderMessage(message) {
      const messages = document.getElementById('messages');
      const div = document.createElement('div');
      div.className = `message ${message.role}`;
      div.textContent = message.content;
      messages.appendChild(div);
    }

    async function createConversation() {
      const payload = {
        title: document.getElementById('title').value || 'Yeni konusma',
        channel: document.getElementById('channel').value,
        language: document.getElementById('language').value || 'tr',
        product_id: document.getElementById('productId').value || null,
        marketplace: document.getElementById('marketplace').value || null,
      };

      const res = await fetch('/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      await selectConversation(data.conversation.id);
    }

    async function sendMessage() {
      if (!currentConversationId) {
        alert('Once bir konusma secin.');
        return;
      }

      const input = document.getElementById('messageInput');
      const content = input.value.trim();
      if (!content) return;

      document.getElementById('sendBtn').disabled = true;
      const res = await fetch(`/conversations/${currentConversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      const data = await res.json();
      input.value = '';
      await selectConversation(currentConversationId);
      document.getElementById('sendBtn').disabled = false;
      if (!res.ok) {
        alert(data.detail || 'Mesaj gonderilemedi');
      }
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    document.getElementById('createBtn').onclick = createConversation;
    document.getElementById('sendBtn').onclick = sendMessage;
    document.getElementById('messageInput').addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        sendMessage();
      }
    });

    loadConversations();
  </script>
</body>
</html>
"""
