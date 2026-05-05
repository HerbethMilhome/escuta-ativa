"""Frontend HTML/CSS/JS para o Interview Assistant GUI."""


def get_html():
    """Retorna o HTML completo da interface do chat."""
    return r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Interview Assistant</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github-dark.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/highlight.js@11/highlight.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0d1117;
    color: #e6edf3;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #header {
    padding: 12px 20px;
    background: #161b22;
    border-bottom: 1px solid #30363d;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    -webkit-app-region: drag;
  }

  #header h1 {
    font-size: 16px;
    font-weight: 600;
    color: #58a6ff;
  }

  #status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 500;
  }

  #status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6e7681;
    transition: background 0.3s;
  }

  #status-dot.listening { background: #3fb950; }
  #status-dot.transcribing { background: #d29922; }
  #status-dot.answering { background: #58a6ff; }
  #status-dot.initializing { background: #6e7681; animation: pulse 1.5s infinite; }
  #status-dot.error { background: #f85149; }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  #status-text { color: #8b949e; }

  #toggle-btn {
    -webkit-app-region: no-drag;
    background: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    margin-left: 12px;
  }
  #toggle-btn:hover { background: #30363d; }
  #toggle-btn.paused { background: #f85149; border-color: #f85149; }
  #toggle-btn.paused:hover { background: #da3633; }

  #print-btn {
    -webkit-app-region: no-drag;
    background: #1f6feb;
    color: #ffffff;
    border: 1px solid #1f6feb;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    margin-left: 8px;
  }
  #print-btn:hover { background: #388bfd; }
  #print-btn:disabled { opacity: 0.5; cursor: wait; }

  #chat {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    scroll-behavior: smooth;
  }

  #chat::-webkit-scrollbar { width: 6px; }
  #chat::-webkit-scrollbar-track { background: transparent; }
  #chat::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
  #chat::-webkit-scrollbar-thumb:hover { background: #484f58; }

  .message {
    max-width: 85%;
    padding: 12px 16px;
    border-radius: 12px;
    line-height: 1.6;
    font-size: 14px;
    animation: fadeIn 0.2s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .question {
    align-self: flex-start;
    background: #1c2333;
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    color: #c9d1d9;
  }

  .question .label {
    font-size: 11px;
    font-weight: 600;
    color: #58a6ff;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .answer {
    align-self: flex-end;
    background: #161b22;
    border: 1px solid #30363d;
    border-right: 3px solid #3fb950;
    color: #e6edf3;
  }

  .answer .label {
    font-size: 11px;
    font-weight: 600;
    color: #3fb950;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .answer .content p { margin-bottom: 8px; }
  .answer .content p:last-child { margin-bottom: 0; }

  .answer .content pre {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 12px;
    margin: 8px 0;
    overflow-x: auto;
  }

  .answer .content code {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
  }

  .answer .content :not(pre) > code {
    background: #1c2333;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }

  .answer .content ul, .answer .content ol {
    padding-left: 20px;
    margin: 6px 0;
  }

  .answer .content li { margin: 3px 0; }

  .answer .content blockquote {
    border-left: 3px solid #30363d;
    padding-left: 12px;
    color: #8b949e;
    margin: 8px 0;
  }

  .cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background: #58a6ff;
    animation: blink 0.8s infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  #empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #484f58;
    font-size: 14px;
    text-align: center;
  }
</style>
</head>
<body>

<div id="header">
  <h1>Interview Assistant</h1>
  <div id="status">
    <span id="status-dot" class="initializing"></span>
    <span id="status-text">Inicializando...</span>
    <button id="toggle-btn" onclick="toggleListening()">Pausar</button>
    <button id="print-btn" onclick="takeScreenshot()">Print</button>
  </div>
</div>

<div id="chat">
  <div id="empty-state">Aguardando audio...</div>
</div>

<script>
  // Configurar marked com highlight.js
  marked.setOptions({
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
  });

  const chat = document.getElementById('chat');
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const emptyState = document.getElementById('empty-state');

  let questionCount = 0;
  let currentAnswerContent = null;
  let tokenBuffer = '';
  let renderTimer = null;

  function setStatus(status, text) {
    statusDot.className = status;
    statusText.textContent = text;
  }

  function scrollToBottom() {
    chat.scrollTop = chat.scrollHeight;
  }

  function addQuestion(text) {
    if (emptyState) {
      emptyState.remove();
    }
    questionCount++;
    const div = document.createElement('div');
    div.className = 'message question';
    div.innerHTML = '<div class="label">Pergunta #' + questionCount + '</div>' +
                    '<div class="content">' + escapeHtml(text) + '</div>';
    chat.appendChild(div);
    scrollToBottom();
  }

  function startAnswer() {
    const div = document.createElement('div');
    div.className = 'message answer';
    div.innerHTML = '<div class="label">Resposta</div>' +
                    '<div class="content"></div>';
    chat.appendChild(div);
    currentAnswerContent = div.querySelector('.content');
    tokenBuffer = '';
    scrollToBottom();
  }

  function appendToken(token) {
    tokenBuffer += token;
    if (!renderTimer) {
      renderTimer = setTimeout(flushTokens, 50);
    }
  }

  function flushTokens() {
    renderTimer = null;
    if (currentAnswerContent) {
      currentAnswerContent.innerHTML = marked.parse(tokenBuffer) + '<span class="cursor"></span>';
      scrollToBottom();
    }
  }

  function finishAnswer() {
    if (renderTimer) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }
    if (currentAnswerContent) {
      currentAnswerContent.innerHTML = marked.parse(tokenBuffer);
      // Re-highlight all code blocks
      currentAnswerContent.querySelectorAll('pre code').forEach(function(block) {
        hljs.highlightElement(block);
      });
      currentAnswerContent = null;
      tokenBuffer = '';
      scrollToBottom();
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  const toggleBtn = document.getElementById('toggle-btn');

  function setPausedUi(paused) {
    if (paused) {
      toggleBtn.textContent = 'Retomar';
      toggleBtn.classList.add('paused');
    } else {
      toggleBtn.textContent = 'Pausar';
      toggleBtn.classList.remove('paused');
    }
  }

  async function toggleListening() {
    try {
      const paused = await window.pywebview.api.toggle_listening();
      setPausedUi(paused);
    } catch (e) {
      console.error(e);
    }
  }

  async function takeScreenshot() {
    const btn = document.getElementById('print-btn');
    btn.disabled = true;
    try {
      await window.pywebview.api.take_screenshot();
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(function() { btn.disabled = false; }, 1500);
    }
  }

  // API exposta para Python chamar via evaluate_js
  window.appApi = {
    setStatus: setStatus,
    addQuestion: addQuestion,
    startAnswer: startAnswer,
    appendToken: appendToken,
    finishAnswer: finishAnswer,
    setPausedUi: setPausedUi
  };
</script>
</body>
</html>"""
