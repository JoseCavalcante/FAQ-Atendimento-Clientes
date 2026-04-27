// ========================================
// Atendimento & Suporte — SaaS Frontend
// ========================================

const API_BASE = window.location.origin;
const MAX_HISTORY = 100;

// ── State ──
let authToken = localStorage.getItem('auth_token');
let refreshToken = localStorage.getItem('refresh_token');
let currentUser = null;
let currentTenant = null;
let isLoading = false;
let currentView = 'chat';

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  if (authToken) {
    showMainApp();
  } else {
    showAuthScreen();
  }
  setupEventListeners();
});

// ══════════════════════════════════════
// AUTH
// ══════════════════════════════════════

function setupEventListeners() {
  // Auth forms
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('register-form').addEventListener('submit', handleRegister);
  document.getElementById('switch-to-register').addEventListener('click', () => toggleAuthForm('register'));
  document.getElementById('switch-to-login').addEventListener('click', () => toggleAuthForm('login'));
  document.getElementById('logout-btn').addEventListener('click', handleLogout);

  // Navigation
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  // Chat
  document.getElementById('send-btn').addEventListener('click', handleSend);
  document.getElementById('clear-chat-btn')?.addEventListener('click', clearChat);
  document.getElementById('question-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });
  document.getElementById('question-input').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
  });

  // Quick actions
  document.querySelectorAll('.quick-action-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.question;
      if (q) { document.getElementById('question-input').value = q; handleSend(); }
    });
  });

  // File upload
  document.getElementById('file-upload').addEventListener('change', handleFileUpload);
}

function toggleAuthForm(form) {
  const login = document.getElementById('login-form');
  const register = document.getElementById('register-form');
  const switchReg = document.getElementById('switch-to-register');
  const switchLog = document.getElementById('switch-to-login');

  if (form === 'register') {
    login.style.display = 'none'; register.style.display = 'block';
    switchReg.style.display = 'none'; switchLog.style.display = 'block';
  } else {
    login.style.display = 'block'; register.style.display = 'none';
    switchReg.style.display = 'block'; switchLog.style.display = 'none';
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  const errorEl = document.getElementById('login-error');
  const btn = document.getElementById('login-btn');

  btn.disabled = true; btn.textContent = 'Entrando...';
  errorEl.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Erro ao fazer login');

    saveAuth(data);
    showMainApp();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
  } finally {
    btn.disabled = false; btn.textContent = 'Entrar';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById('register-name').value;
  const company_name = document.getElementById('register-company').value;
  const email = document.getElementById('register-email').value;
  const password = document.getElementById('register-password').value;
  const errorEl = document.getElementById('register-error');
  const btn = document.getElementById('register-btn');

  btn.disabled = true; btn.textContent = 'Criando...';
  errorEl.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name, company_name }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Erro ao criar conta');

    saveAuth(data);
    showMainApp();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
  } finally {
    btn.disabled = false; btn.textContent = 'Criar conta';
  }
}

function saveAuth(data) {
  authToken = data.access_token;
  refreshToken = data.refresh_token;
  currentUser = data.user;
  currentTenant = data.tenant;
  localStorage.setItem('auth_token', authToken);
  if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
}

function handleLogout() {
  authToken = null; refreshToken = null; currentUser = null; currentTenant = null;
  localStorage.removeItem('auth_token');
  localStorage.removeItem('refresh_token');
  showAuthScreen();
}

function showAuthScreen() {
  document.getElementById('auth-screen').style.display = 'flex';
  document.getElementById('main-app').style.display = 'none';
}

async function showMainApp() {
  document.getElementById('auth-screen').style.display = 'none';
  document.getElementById('main-app').style.display = 'flex';

  // Carregar dados do usuário
  try {
    const me = await apiFetch('/auth/me');
    currentUser = me;
    document.getElementById('user-name').textContent = me.full_name;

    const info = await apiFetch('/api/v1/tenant/info');
    currentTenant = info.tenant;
    document.getElementById('header-tenant-name').textContent = info.tenant.name;
    document.getElementById('user-plan').textContent = info.tenant.plan.toUpperCase();
    document.getElementById('user-plan').className = `plan-badge plan-${info.tenant.plan}`;
  } catch {
    handleLogout();
    return;
  }

  loadDocumentsForChat();
  document.getElementById('question-input').focus();
}

// ══════════════════════════════════════
// API Helper
// ══════════════════════════════════════

async function apiFetch(url, options = {}) {
  const headers = { 'Accept': 'application/json', ...options.headers };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

  const res = await fetch(`${API_BASE}${url}`, { ...options, headers });

  if (res.status === 401) {
    // Tentar refresh
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          authToken = data.access_token;
          localStorage.setItem('auth_token', authToken);
          headers['Authorization'] = `Bearer ${authToken}`;
          const retry = await fetch(`${API_BASE}${url}`, { ...options, headers });
          if (!retry.ok) throw new Error('Sessão expirada');
          return retry.json();
        }
      } catch { /* fall through to logout */ }
    }
    handleLogout();
    throw new Error('Sessão expirada. Faça login novamente.');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Erro HTTP ${res.status}` }));
    throw new Error(err.detail || `Erro HTTP ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ══════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════

function switchView(view) {
  currentView = view;
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  document.getElementById(`view-${view}`).style.display = 'flex';
  document.querySelector(`[data-view="${view}"]`).classList.add('active');

  if (view === 'documents') loadDocuments();
  if (view === 'dashboard') loadDashboard();
}

// ══════════════════════════════════════
// CHAT
// ══════════════════════════════════════

async function loadDocumentsForChat() {
  try {
    const data = await apiFetch('/api/v1/documents');
    const select = document.getElementById('doc-select');
    select.innerHTML = '<option value="">Todos os documentos</option>';
    data.documents.filter(d => d.is_processed).forEach(doc => {
      const opt = document.createElement('option');
      opt.value = doc.id;
      opt.textContent = `${doc.original_name} (${doc.page_count} pág.)`;
      select.appendChild(opt);
    });
  } catch { /* fallback silencioso */ }
}

async function handleSend() {
  const input = document.getElementById('question-input');
  const question = input.value.trim();
  if (!question || isLoading) return;

  const welcome = document.getElementById('welcome-section');
  if (welcome) welcome.style.display = 'none';

  addMessage('user', question);
  input.value = ''; input.style.height = 'auto';

  const loadingId = showLoading();
  isLoading = true;
  document.getElementById('send-btn').disabled = true;

  try {
    const docId = document.getElementById('doc-select').value || undefined;
    const data = await apiFetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, document_id: docId, top_k: 5 }),
    });

    removeLoading(loadingId);
    addMessage('ai', data.response, {
      sources: data.sources,
      usage: data.usage,
    });
  } catch (err) {
    removeLoading(loadingId);
    addMessage('ai', `⚠️ **Erro:** ${err.message}`, null, true);
  } finally {
    isLoading = false;
    document.getElementById('send-btn').disabled = false;
    input.focus();
  }
}

function addMessage(role, text, meta = null, isError = false) {
  const chatArea = document.getElementById('chat-area');
  const div = document.createElement('div');
  div.classList.add('message', `message-${role}`);

  const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const avatar = role === 'user' ? '👤' : '🤖';
  const formatted = role === 'ai' ? formatMarkdown(text) : escapeHtml(text);

  let metaHtml = `<span class="message-time">${time}</span>`;
  if (meta && meta.sources && meta.sources.length > 0) {
    metaHtml += `<span class="pages-badge">📑 ${meta.sources.length} fontes</span>`;
  }
  if (meta && meta.usage) {
    metaHtml += `<span class="usage-badge">${meta.usage.queries_this_month}/${meta.usage.max_queries > 0 ? meta.usage.max_queries : '∞'}</span>`;
  }

  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content">
      <div class="message-bubble${isError ? ' error-bubble' : ''}">${formatted}</div>
      <div class="message-meta">${metaHtml}</div>
    </div>
  `;

  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function clearChat() {
  document.getElementById('chat-area').innerHTML = '';
  const welcome = document.getElementById('welcome-section');
  if (welcome) welcome.style.display = 'flex';
}

function showLoading() {
  const id = 'loading-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.classList.add('message', 'message-ai', 'message-loading');
  div.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="message-content">
      <div class="message-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('chat-area').appendChild(div);
  document.getElementById('chat-area').scrollTop = document.getElementById('chat-area').scrollHeight;
  return id;
}

function removeLoading(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ══════════════════════════════════════
// DOCUMENTS
// ══════════════════════════════════════

async function loadDocuments() {
  const list = document.getElementById('documents-list');
  try {
    const data = await apiFetch('/api/v1/documents');
    if (!data.documents.length) {
      list.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📁</span>
          <p>Nenhum documento enviado ainda.</p>
          <p class="empty-hint">Faça upload de um PDF para começar.</p>
        </div>`;
      return;
    }

    list.innerHTML = data.documents.map(doc => `
      <div class="doc-card" data-id="${doc.id}">
        <div class="doc-icon">${doc.is_processed ? '✅' : '⏳'}</div>
        <div class="doc-info">
          <div class="doc-name">${escapeHtml(doc.original_name)}</div>
          <div class="doc-meta">${doc.page_count} págs. • ${doc.file_size_kb} KB • ${doc.chunk_count} chunks</div>
        </div>
        <div class="doc-actions">
          ${!doc.is_processed ? `<button class="btn-sm btn-process" onclick="processDocument('${doc.id}')">⚙️ Processar</button>` : '<span class="status-ok">Pronto</span>'}
          <button class="btn-sm btn-delete" onclick="deleteDocument('${doc.id}')">🗑️</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    list.innerHTML = `<div class="empty-state"><p>Erro ao carregar: ${err.message}</p></div>`;
  }
}

async function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const progressEl = document.getElementById('upload-progress');
  const statusEl = document.getElementById('upload-status');
  progressEl.style.display = 'flex';
  statusEl.textContent = `Enviando ${file.name}...`;

  const formData = new FormData();
  formData.append('file', file);

  try {
    await apiFetch('/api/v1/documents', {
      method: 'POST',
      headers: {}, // Remove Content-Type para FormData
      body: formData,
    });
    statusEl.textContent = '✅ Upload concluído!';
    setTimeout(() => { progressEl.style.display = 'none'; }, 2000);
    loadDocuments();
    loadDocumentsForChat();
  } catch (err) {
    statusEl.textContent = `❌ Erro: ${err.message}`;
    setTimeout(() => { progressEl.style.display = 'none'; }, 4000);
  }

  e.target.value = '';
}

async function processDocument(docId) {
  const btn = document.querySelector(`[onclick="processDocument('${docId}')"]`);
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Processando...'; }

  try {
    await apiFetch('/api/v1/chat/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: docId }),
    });
    loadDocuments();
    loadDocumentsForChat();
  } catch (err) {
    alert(`Erro ao processar: ${err.message}`);
    if (btn) { btn.disabled = false; btn.textContent = '⚙️ Processar'; }
  }
}

async function deleteDocument(docId) {
  if (!confirm('Tem certeza que deseja excluir este documento?')) return;
  try {
    await apiFetch(`/api/v1/documents/${docId}`, { method: 'DELETE' });
    loadDocuments();
    loadDocumentsForChat();
  } catch (err) {
    alert(`Erro ao excluir: ${err.message}`);
  }
}

// ══════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════

async function loadDashboard() {
  const container = document.getElementById('dashboard-content');
  try {
    const usage = await apiFetch('/api/v1/tenant/usage');
    const plans = await apiFetch('/api/v1/tenant/plans');

    const queryPct = usage.queries.limit > 0
      ? Math.round((usage.queries.used / usage.queries.limit) * 100)
      : 0;
    const docPct = usage.documents.limit > 0
      ? Math.round((usage.documents.used / usage.documents.limit) * 100)
      : 0;

    container.innerHTML = `
      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-icon">📊</span>
          <h3>Plano Atual</h3>
        </div>
        <div class="dash-plan-name">${usage.plan.name}</div>
        <p class="dash-plan-price">R$ ${plans.plans.find(p => p.slug === usage.plan.slug)?.price_monthly?.toFixed(2) || '0,00'}/mês</p>
      </div>

      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-icon">💬</span>
          <h3>Consultas</h3>
        </div>
        <div class="dash-metric">${usage.queries.used} <span class="dash-limit">/ ${usage.queries.limit > 0 ? usage.queries.limit : '∞'}</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${queryPct}%"></div></div>
      </div>

      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-icon">📄</span>
          <h3>Documentos</h3>
        </div>
        <div class="dash-metric">${usage.documents.used} <span class="dash-limit">/ ${usage.documents.limit > 0 ? usage.documents.limit : '∞'}</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:${docPct}%"></div></div>
      </div>

      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-icon">💾</span>
          <h3>Armazenamento</h3>
        </div>
        <div class="dash-metric">${usage.storage.used_mb} MB</div>
        <p class="dash-hint">Max por arquivo: ${usage.storage.max_file_size_mb} MB</p>
      </div>

      <div class="dash-card dash-card-wide">
        <div class="dash-card-header">
          <span class="dash-card-icon">🚀</span>
          <h3>Planos Disponíveis</h3>
        </div>
        <div class="plans-grid">
          ${plans.plans.map(p => `
            <div class="plan-option ${p.slug === usage.plan.slug ? 'plan-current' : ''}">
              <h4>${p.name}</h4>
              <div class="plan-price">R$ ${p.price_monthly.toFixed(2)}<span>/mês</span></div>
              <ul>
                <li>${p.max_documents > 0 ? p.max_documents : '∞'} documentos</li>
                <li>${p.max_queries_per_month > 0 ? p.max_queries_per_month.toLocaleString() : '∞'} consultas/mês</li>
                <li>${p.max_file_size_mb} MB/arquivo</li>
                <li>${p.max_users > 0 ? p.max_users : '∞'} usuários</li>
              </ul>
              ${p.slug !== usage.plan.slug && p.slug !== 'free' ? `<button class="btn-sm btn-upgrade" onclick="upgradePlan('${p.slug}')">Upgrade</button>` : ''}
              ${p.slug === usage.plan.slug ? '<span class="plan-current-badge">Plano atual</span>' : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p>Erro: ${err.message}</p></div>`;
  }
}

async function upgradePlan(plan) {
  if (!confirm(`Deseja atualizar para o plano ${plan.toUpperCase()}?`)) return;
  try {
    await apiFetch('/api/v1/tenant/upgrade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan }),
    });
    loadDashboard();
    // Atualizar badge no header
    document.getElementById('user-plan').textContent = plan.toUpperCase();
    document.getElementById('user-plan').className = `plan-badge plan-${plan}`;
  } catch (err) {
    alert(`Erro: ${err.message}`);
  }
}

// ══════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════

function formatMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p>\s*<\/p>/g, '');
  return html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
