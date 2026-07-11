const state = {
  authMode: "login",
  owner: null,
  analytics: null,
  customers: [],
  dueToday: [],
  overdue: [],
  filteredCustomers: [],
  history: [],
  chart: null,
  selectedCustomer: null,
  chatBusy: false,
  refreshInProgress: false,
};

const AUTH_TOKEN_KEY = "digital-khata-token";

const elements = {};

function money(value) {
  const amount = Number(value || 0);
  return `PKR ${amount.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function integer(value) {
  return Number(value || 0).toLocaleString("en-PK");
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function trustSlug(label) {
  return String(label || "").toLowerCase().replace(/\s+/g, "-");
}

function trustBadge(label, score) {
  const slug = trustSlug(label);
  return `<span class="customer-badge badge--${slug}">${escapeHtml(label || "Not rated")} ${score !== undefined ? `· ${score}` : ""}</span>`;
}

function formatDate(dateValue) {
  if (!dateValue) return "—";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return String(dateValue);
  return date.toLocaleDateString("en-PK", { day: "2-digit", month: "short", year: "numeric" });
}

function formatToday() {
  const now = new Date();
  return now.toLocaleDateString("en-PK", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function showToast(message, type = "error") {
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  elements.toastStack.appendChild(toast);
  window.setTimeout(() => {
    toast.remove();
  }, 3200);
}

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function setAuthToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

function setSignedOutState() {
  state.owner = null;
  state.analytics = null;
  state.customers = [];
  state.dueToday = [];
  state.overdue = [];
  state.filteredCustomers = [];
  state.history = [];
  state.selectedCustomer = null;
}

function setAppVisibility(isAuthed) {
  elements.authShell.hidden = isAuthed;
  elements.appShell.hidden = !isAuthed;
}

function renderSessionPill() {
  if (state.owner) {
    elements.ownerSessionPill.textContent = `${state.owner.shop_name} · ${state.owner.email}`;
    elements.logoutButton.hidden = false;
  } else {
    elements.ownerSessionPill.textContent = "Signed out";
    elements.logoutButton.hidden = true;
  }
}

function setAuthMode(mode) {
  state.authMode = mode;
  const isLogin = mode === "login";
  elements.loginTab.classList.toggle("is-active", isLogin);
  elements.registerTab.classList.toggle("is-active", !isLogin);
  elements.loginTab.setAttribute("aria-selected", String(isLogin));
  elements.registerTab.setAttribute("aria-selected", String(!isLogin));
  elements.loginForm.hidden = !isLogin;
  elements.registerForm.hidden = isLogin;
  elements.authStatus.textContent = isLogin
    ? "Sign in to open your dashboard."
    : "Create a new shop owner account to get started.";
}

function handleUnauthorized() {
  clearAuthToken();
  setSignedOutState();
  renderSessionPill();
  setAppVisibility(false);
  setAuthMode(state.authMode || "login");
}

async function fetchJSON(url, options = {}) {
  const requestOptions = { ...options };
  const headers = new Headers(requestOptions.headers || {});
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  requestOptions.headers = headers;

  const response = await fetch(url, requestOptions);
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!response.ok) {
    const message = data && typeof data === "object" && data.error ? data.error : `Request failed: ${response.status}`;
    if (response.status === 401) {
      handleUnauthorized();
    }
    const error = new Error(message);
    error.authRequired = response.status === 401;
    throw error;
  }
  return data;
}

function renderSummaryCards() {
  const analytics = state.analytics || {
    total_outstanding: 0,
    customers_with_balance: 0,
    average_debt: 0,
    overdue_customer_count: 0,
  };
  elements.totalOutstanding.textContent = money(analytics.total_outstanding);
  elements.customersWithBalance.textContent = integer(analytics.customers_with_balance);
  elements.averageDebt.textContent = money(analytics.average_debt);
  elements.overdueCount.textContent = integer(analytics.overdue_customer_count);
}

function renderTrustChart() {
  const labels = ["Excellent", "Good", "Fair", "Poor", "High Risk", "New Customer"];
  const counts = labels.map((label) => state.customers.filter((customer) => customer.trust_label === label).length);
  const colors = ["#0f766e", "#1b9a8f", "#c0841a", "#c2410c", "#8b1e1e", "#64748b"];

  if (window.Chart) {
    if (state.chart) {
      state.chart.destroy();
    }
    state.chart = new Chart(elements.trustChart, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: counts,
          backgroundColor: colors,
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
              boxWidth: 10,
              padding: 16,
            },
          },
          tooltip: {
            callbacks: {
              label(context) {
                const label = context.label || "";
                const value = context.raw || 0;
                return `${label}: ${value}`;
              },
            },
          },
        },
      },
    });
  }
}

function renderCustomers() {
  const customers = state.filteredCustomers;
  if (!state.customers.length) {
    elements.customerCountLabel.textContent = "No customers yet";
    elements.customerList.innerHTML = '<div class="compact-item"><div class="compact-item__meta"><span class="compact-item__name">No customers found</span><span class="compact-item__subline">Use chat to add the first customer.</span></div></div>';
    return;
  }

  if (!customers.length) {
    elements.customerCountLabel.textContent = `No matches for "${elements.customerSearch.value.trim()}"`;
    elements.customerList.innerHTML = '<div class="compact-item"><div class="compact-item__meta"><span class="compact-item__name">No matching customers</span><span class="compact-item__subline">Try a different search term.</span></div></div>';
    return;
  }

  elements.customerCountLabel.textContent = `${integer(customers.length)} shown of ${integer(state.customers.length)} customers`;
  elements.customerList.innerHTML = customers.map((customer) => {
    const activeClass = state.selectedCustomer && state.selectedCustomer.name === customer.name ? " customer-row--active" : "";
    return `
      <button type="button" class="customer-row${activeClass}" data-name="${escapeHtml(customer.name)}">
        <div class="customer-meta">
          <span class="customer-name">${escapeHtml(customer.name)}</span>
          <span class="customer-subline">Overdue rows: ${integer(customer.overdue_count || 0)}</span>
        </div>
        <div class="customer-summary">
          <span class="amount ${Number(customer.balance) > 0 ? "amount--warning" : "amount--positive"}">${money(customer.balance)}</span>
          ${trustBadge(customer.trust_label, customer.trust_score)}
        </div>
      </button>
    `;
  }).join("");
}

function renderCompactList(element, items, kind) {
  if (!items.length) {
    element.innerHTML = kind === "due"
      ? '<div class="compact-item"><div class="compact-item__meta"><span class="compact-item__name">No one is due today</span><span class="compact-item__subline">The ledger looks clear.</span></div></div>'
      : '<div class="compact-item"><div class="compact-item__meta"><span class="compact-item__name">No one is overdue</span><span class="compact-item__subline">Great job keeping the ledger current.</span></div></div>';
    return;
  }

  element.innerHTML = items.map((item) => {
    const meta = kind === "overdue" ? `${integer(item.days_overdue)} days overdue` : "Due today";
    return `
      <div class="compact-item">
        <div class="compact-item__meta">
          <span class="compact-item__name">${escapeHtml(item.name)}</span>
          <span class="compact-item__subline">${escapeHtml(meta)}</span>
        </div>
        <strong class="amount ${kind === "overdue" ? "amount--warning" : "amount--positive"}">${money(item.balance)}</strong>
      </div>
    `;
  }).join("");
}

function renderChatHistory() {
  if (!state.history.length) {
    elements.chatHistory.innerHTML = `
      <div class="message message--assistant">
        <div class="message-content">Ask me about customers, due amounts, overdue accounts, or summary analytics.</div>
      </div>
    `;
    return;
  }

  const messages = state.history.map((item) => {
    const roleClass = item.role === "user" ? "message--user" : "message--assistant";
    return `
      <div class="message ${roleClass}">
        <div class="message-content">${escapeHtml(item.content).replaceAll("\n", "<br>")}</div>
      </div>
    `;
  });

  if (state.chatBusy) {
    messages.push(`
      <div class="message message--assistant message--thinking">
        <div class="thinking-dots" aria-label="Assistant is thinking">
          <span></span><span></span><span></span>
        </div>
      </div>
    `);
  }

  elements.chatHistory.innerHTML = messages.join("");
  elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
}

function renderDrawer(customerHistory) {
  const customer = customerHistory.customer;
  const history = customerHistory.transactions || [];
  elements.drawerName.textContent = customer.name;

  const selfViewUrl = customer.self_view_link || customerHistory.customer?.self_view_link || "";
  const rows = history.length
    ? history.map((txn) => {
        const isPayment = txn.type === "payment_received";
        const amountClass = isPayment ? "transaction-row__amount--payment" : "transaction-row__amount--credit";
        const label = isPayment ? "Payment" : "Credit";
        const prefix = isPayment ? "+" : "-";
        return `
          <tr>
            <td>${escapeHtml(formatDate(txn.created_at))}</td>
            <td>${label}</td>
            <td class="${amountClass}">${prefix}${money(txn.amount)}</td>
            <td>${escapeHtml(txn.note || "—")}</td>
          </tr>
        `;
      }).join("")
    : '<tr><td colspan="4" class="empty-state">No transactions yet.</td></tr>';

  elements.drawerBody.innerHTML = `
    <div class="drawer-summary">
      <div class="drawer-stat">
        <span>Phone</span>
        <strong>${escapeHtml(customer.phone || "Not provided")}</strong>
      </div>
      <div class="drawer-stat">
        <span>Outstanding balance</span>
        <strong>${money(customerHistory.balance)}</strong>
      </div>
      <div class="drawer-stat">
        <span>Trust score</span>
        <strong>${customerHistory.trust_score} · ${escapeHtml(customerHistory.trust_label)}</strong>
      </div>
      <div class="drawer-stat">
        <span>Overdue rows</span>
        <strong>${integer(customerHistory.overdue_count)}</strong>
      </div>
    </div>
    <div class="copy-row">
      <button type="button" class="small-button" id="copySelfViewButton">Copy self-view link</button>
      <button type="button" class="small-button" id="placeholderReminderButton" disabled>Send reminder</button>
    </div>
    <div class="table-wrap">
      <table class="self-view-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    </div>
  `;

  const copyButton = document.getElementById("copySelfViewButton");
  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(selfViewUrl);
      showToast("Self-view link copied.", "success");
    } catch {
      showToast("Could not copy the self-view link.", "error");
    }
  });

  openDrawer();
}

function openDrawer() {
  elements.drawer.hidden = false;
  elements.drawerOverlay.hidden = false;
  requestAnimationFrame(() => {
    elements.drawer.classList.add("is-open");
  });
}

function closeDrawer() {
  elements.drawer.classList.remove("is-open");
  window.setTimeout(() => {
    elements.drawer.hidden = true;
    elements.drawerOverlay.hidden = true;
  }, 220);
}

async function openCustomer(name) {
  try {
    const data = await fetchJSON(`/api/customers/${encodeURIComponent(name)}/history`);
    state.selectedCustomer = data.customer;
    renderCustomers();
    renderDrawer(data);
  } catch (error) {
    showToast(error.message || "Could not load customer history.", "error");
  }
}

function updateCustomerState(customers) {
  state.customers = customers || [];
  const query = elements.customerSearch.value.trim().toLowerCase();
  state.filteredCustomers = query
    ? state.customers.filter((customer) => customer.name.toLowerCase().includes(query))
    : [...state.customers];
  renderCustomers();
  renderTrustChart();
}

function updatePanels() {
  renderSummaryCards();
  renderCompactList(elements.dueTodayList, state.dueToday, "due");
  renderCompactList(elements.overdueList, state.overdue, "overdue");
  elements.dueTodayCount.textContent = integer(state.dueToday.length);
  elements.overduePanelCount.textContent = integer(state.overdue.length);
}

async function refreshDashboard({ silent = false } = {}) {
  state.refreshInProgress = true;
  try {
    const [analytics, customers, dueToday, overdue] = await Promise.all([
      fetchJSON("/api/analytics"),
      fetchJSON("/api/customers/"),
      fetchJSON("/api/due-today"),
      fetchJSON("/api/overdue"),
    ]);

    state.analytics = analytics;
    state.customers = customers.customers || [];
    state.dueToday = dueToday.due_today || [];
    state.overdue = overdue.overdue || [];
    updateCustomerState(state.customers);
    updatePanels();
    if (state.selectedCustomer && state.selectedCustomer.name) {
      try {
        const selected = await fetchJSON(`/api/customers/${encodeURIComponent(state.selectedCustomer.name)}/history`);
        state.selectedCustomer = selected.customer;
        renderDrawer(selected);
      } catch (drawerError) {
        showToast(drawerError.message || "Could not refresh customer detail.", "error");
      }
    }
    if (!silent) {
      showToast("Dashboard refreshed.", "success");
    }
  } catch (error) {
    if (error.authRequired) {
      return;
    }
    showToast(error.message || "Could not refresh dashboard.", "error");
  } finally {
    state.refreshInProgress = false;
  }
}

function setChatBusy(isBusy) {
  state.chatBusy = isBusy;
  elements.chatInput.disabled = isBusy;
  elements.sendChatButton.disabled = isBusy;
  elements.clearChatButton.disabled = isBusy;
  renderChatHistory();
}

async function sendChat(message) {
  const cleanMessage = message.trim();
  if (!cleanMessage || state.chatBusy) return;

  state.history.push({ role: "user", content: cleanMessage });
  renderChatHistory();
  elements.chatInput.value = "";
  setChatBusy(true);

  try {
    const response = await fetchJSON("/api/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: cleanMessage,
        history: state.history.slice(0, -1),
      }),
    });

    state.history = response.history || [];
    renderChatHistory();
    await refreshDashboard({ silent: true });
  } catch (error) {
    if (error.authRequired) {
      return;
    }
    state.history.push({ role: "assistant", content: error.message || "Something went wrong." });
    renderChatHistory();
    showToast(error.message || "Something went wrong.", "error");
  } finally {
    setChatBusy(false);
  }
}

async function submitAuth(mode) {
  const isLogin = mode === "login";
  const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
  const payload = isLogin
    ? {
        email: elements.loginEmail.value.trim(),
        password: elements.loginPassword.value,
      }
    : {
        shop_name: elements.registerShopName.value.trim(),
        email: elements.registerEmail.value.trim(),
        password: elements.registerPassword.value,
      };

  const button = isLogin ? elements.loginButton : elements.registerButton;
  button.disabled = true;
  try {
    const response = await fetchJSON(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setAuthToken(response.access_token);
    state.owner = {
      shop_name: response.shop_name,
      email: response.email,
    };
    renderSessionPill();
    setAppVisibility(true);
    await refreshDashboard({ silent: true });
    showToast(isLogin ? "Welcome back." : "Account created.", "success");
  } catch (error) {
    elements.authStatus.textContent = error.message || "Authentication failed.";
    showToast(error.message || "Authentication failed.", "error");
  } finally {
    button.disabled = false;
  }
}

function logout() {
  clearAuthToken();
  setSignedOutState();
  renderChatHistory();
  renderSessionPill();
  setAppVisibility(false);
  setAuthMode("login");
}

function wireEvents() {
  elements.loginTab.addEventListener("click", () => setAuthMode("login"));
  elements.registerTab.addEventListener("click", () => setAuthMode("register"));
  elements.loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuth("login");
  });
  elements.registerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAuth("register");
  });
  elements.logoutButton.addEventListener("click", logout);

  elements.customerSearch.addEventListener("input", () => {
    const query = elements.customerSearch.value.trim().toLowerCase();
    state.filteredCustomers = query
      ? state.customers.filter((customer) => customer.name.toLowerCase().includes(query))
      : [...state.customers];
    renderCustomers();
  });

  elements.customerList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-name]");
    if (!button) return;
    openCustomer(button.dataset.name);
  });

  elements.chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    sendChat(elements.chatInput.value);
  });

  elements.chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendChat(elements.chatInput.value);
    }
  });

  elements.clearChatButton.addEventListener("click", () => {
    state.history = [];
    renderChatHistory();
  });

  elements.suggestionChips.addEventListener("click", (event) => {
    const chip = event.target.closest("button.chip");
    if (!chip) return;
    sendChat(chip.textContent || "");
  });

  elements.closeDrawerButton.addEventListener("click", closeDrawer);
  elements.drawerOverlay.addEventListener("click", closeDrawer);
}

function cacheElements() {
  elements.authShell = document.getElementById("authShell");
  elements.appShell = document.querySelector(".app-shell");
  elements.loginTab = document.getElementById("loginTab");
  elements.registerTab = document.getElementById("registerTab");
  elements.authStatus = document.getElementById("authStatus");
  elements.loginForm = document.getElementById("loginForm");
  elements.registerForm = document.getElementById("registerForm");
  elements.loginEmail = document.getElementById("loginEmail");
  elements.loginPassword = document.getElementById("loginPassword");
  elements.loginButton = document.getElementById("loginButton");
  elements.registerShopName = document.getElementById("registerShopName");
  elements.registerEmail = document.getElementById("registerEmail");
  elements.registerPassword = document.getElementById("registerPassword");
  elements.registerButton = document.getElementById("registerButton");
  elements.todayDate = document.getElementById("todayDate");
  elements.totalOutstanding = document.getElementById("totalOutstanding");
  elements.customersWithBalance = document.getElementById("customersWithBalance");
  elements.averageDebt = document.getElementById("averageDebt");
  elements.overdueCount = document.getElementById("overdueCount");
  elements.trustChart = document.getElementById("trustChart");
  elements.customerCountLabel = document.getElementById("customerCountLabel");
  elements.customerSearch = document.getElementById("customerSearch");
  elements.customerList = document.getElementById("customerList");
  elements.dueTodayList = document.getElementById("dueTodayList");
  elements.overdueList = document.getElementById("overdueList");
  elements.dueTodayCount = document.getElementById("dueTodayCount");
  elements.overduePanelCount = document.getElementById("overduePanelCount");
  elements.chatHistory = document.getElementById("chatHistory");
  elements.chatForm = document.getElementById("chatForm");
  elements.chatInput = document.getElementById("chatInput");
  elements.sendChatButton = document.getElementById("sendChatButton");
  elements.clearChatButton = document.getElementById("clearChatButton");
  elements.suggestionChips = document.getElementById("suggestionChips");
  elements.ownerSessionPill = document.getElementById("ownerSessionPill");
  elements.logoutButton = document.getElementById("logoutButton");
  elements.drawer = document.getElementById("customerDrawer");
  elements.drawerOverlay = document.getElementById("drawerOverlay");
  elements.drawerBody = document.getElementById("drawerBody");
  elements.drawerName = document.getElementById("drawerName");
  elements.closeDrawerButton = document.getElementById("closeDrawerButton");
  elements.toastStack = document.getElementById("toastStack");
}

async function init() {
  cacheElements();
  elements.todayDate.textContent = formatToday();
  renderChatHistory();
  renderSummaryCards();
  wireEvents();

  const token = getAuthToken();
  if (!token) {
    setSignedOutState();
    renderSessionPill();
    setAppVisibility(false);
    setAuthMode("login");
    return;
  }

  try {
    const me = await fetchJSON("/api/auth/me");
    state.owner = me;
    renderSessionPill();
    setAppVisibility(true);
    await refreshDashboard({ silent: true });
  } catch {
    logout();
  }
}

document.addEventListener("DOMContentLoaded", init);
