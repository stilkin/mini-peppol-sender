/* ============================================================
   PEPPOL Invoice Composer — client-side logic
   Vanilla JS. State lives in the DOM and localStorage.
   ============================================================ */

// ---------- Constants ----------

const LS_KEYS = {
  defaults: "peppol_defaults",
  customers: "peppol_customers",
  templates: "peppol_line_templates",
  lastNumber: "peppol_last_invoice_number",
};

const DEFAULT_DEFAULTS = {
  currency: "EUR",
  payment_terms: "Net 30 days",
  due_days: 30,
  tax_category: "E",
  tax_percent: 0,
};

const TAX_CATEGORIES = ["S", "E", "O", "Z", "AE", "K", "G", "L", "M"];

// ---------- Tiny helpers ----------

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const lsGet = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
};

const lsSet = (key, value) => localStorage.setItem(key, JSON.stringify(value));

const todayISO = () => new Date().toISOString().slice(0, 10);

const addDays = (isoDate, days) => {
  const d = new Date(isoDate);
  d.setDate(d.getDate() + Number(days || 0));
  return d.toISOString().slice(0, 10);
};

const fmt = (n) => Number(n || 0).toFixed(2);

// ---------- Defaults ----------

function getDefaults() {
  return { ...DEFAULT_DEFAULTS, ...lsGet(LS_KEYS.defaults, {}) };
}

function saveDefaults(defaults) {
  lsSet(LS_KEYS.defaults, defaults);
}

// ---------- Invoice number ----------

function nextInvoiceNumber() {
  const last = lsGet(LS_KEYS.lastNumber, null);
  if (!last) return `INV-${new Date().getFullYear()}-001`;
  const m = String(last).match(/^(.*?)(\d+)$/);
  if (!m) return `${last}-1`;
  const prefix = m[1];
  const width = m[2].length;
  const next = String(Number(m[2]) + 1).padStart(width, "0");
  return prefix + next;
}

// ---------- Customers ----------

function loadCustomers() { return lsGet(LS_KEYS.customers, []); }

function saveCustomer(buyer) {
  if (!buyer.name && !buyer.endpoint_id) return;
  const customers = loadCustomers();
  const key = (buyer.endpoint_id || "") + "|" + (buyer.name || "");
  const existing = customers.findIndex(
    (c) => (c.endpoint_id || "") + "|" + (c.name || "") === key,
  );
  if (existing >= 0) customers.splice(existing, 1);
  customers.unshift(buyer);
  // Keep last 50
  lsSet(LS_KEYS.customers, customers.slice(0, 50));
}

function renderCustomerDropdown() {
  const select = $("#recent-customers");
  select.innerHTML = '<option value="">— select customer —</option>';
  loadCustomers().forEach((c, i) => {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = c.name || c.endpoint_id || "(unnamed)";
    select.appendChild(opt);
  });
}

// ---------- Line templates ----------

function loadTemplates() { return lsGet(LS_KEYS.templates, []); }

function saveTemplate(line) {
  if (!line.description) return;
  const templates = loadTemplates();
  const existing = templates.findIndex((t) => t.description === line.description);
  if (existing >= 0) templates.splice(existing, 1);
  templates.unshift(line);
  lsSet(LS_KEYS.templates, templates.slice(0, 50));
}

function renderTemplateDropdown() {
  const select = $("#template-select");
  select.innerHTML = '<option value="">— load template —</option>';
  loadTemplates().forEach((t, i) => {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = t.description;
    select.appendChild(opt);
  });
}

// ---------- Seller (read from /api/org-info) ----------

let sellerCache = null;

async function loadSeller() {
  const card = $("#seller-card");
  try {
    const resp = await fetch("/api/org-info");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const info = await resp.json();
    sellerCache = {
      name: info.name || "",
      registration_name: info.name || "",
      vat: info.VAT || "",
      endpoint_id: (info.VAT || "").replace(/^[A-Z]{2}/, ""),
      endpoint_scheme: "0208",
      country: (info.country || "").slice(0, 2).toUpperCase() === "BE" ? "BE" : "",
      street: [info.street, info.houseNumber].filter(Boolean).join(" "),
      city: info.city || "",
      postal_code: info.zipCode || "",
    };
    card.querySelector(".seller-name").textContent = info.name || "—";
    card.querySelector(".seller-address").textContent =
      [sellerCache.street, [sellerCache.postal_code, sellerCache.city].filter(Boolean).join(" "), info.country]
        .filter(Boolean)
        .join(" · ");
    card.querySelector(".seller-id").textContent =
      `VAT ${info.VAT || "—"}  ·  Endpoint ${sellerCache.endpoint_scheme}:${sellerCache.endpoint_id || "—"}`;
  } catch (err) {
    card.querySelector(".seller-name").textContent = "Could not load seller info";
    card.querySelector(".seller-address").textContent = String(err);
  }
}

// ---------- Buyer fields ----------

function setBuyer(buyer) {
  $$("[data-buyer]").forEach((input) => {
    const key = input.dataset.buyer;
    input.value = buyer[key] ?? "";
  });
}

function getBuyer() {
  const buyer = {};
  $$("[data-buyer]").forEach((input) => {
    const v = input.value.trim();
    if (v) buyer[input.dataset.buyer] = v;
  });
  return buyer;
}

async function lookupBuyer() {
  const vat = $("#lookup-vat").value.trim();
  const country = $("#lookup-country").value.trim().toUpperCase();
  if (!vat || !country) return;
  const btn = $("#lookup-btn");
  btn.disabled = true;
  btn.textContent = "Looking up…";
  try {
    const resp = await fetch(`/api/lookup?vatNumber=${encodeURIComponent(vat)}&countryCode=${encodeURIComponent(country)}`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "HTTP " + resp.status);
    const participantId = data.participantId || "";
    const [scheme, id] = participantId.includes(":") ? participantId.split(":") : ["0208", vat];
    const buyer = getBuyer();
    buyer.vat = country + vat;
    buyer.country = country;
    buyer.endpoint_id = id;
    buyer.endpoint_scheme = scheme;
    setBuyer(buyer);
    showResult({
      kind: "success",
      title: "Lookup successful",
      summary: `Participant <strong>${participantId}</strong> ${data.services && data.services.length ? "(can receive invoices)" : ""}`,
    });
  } catch (err) {
    showResult({ kind: "error", title: "Lookup failed", summary: String(err.message || err) });
  } finally {
    btn.disabled = false;
    btn.textContent = "Look up";
  }
}

// ---------- Line items ----------

function makeLineRow(line = {}) {
  const tr = document.createElement("tr");
  tr.className = "line-row";
  tr.innerHTML = `
    <td class="col-desc"><input type="text" data-line="description" placeholder="Item description"></td>
    <td class="col-num"><input type="number" data-line="quantity" class="mono" min="0" step="0.01" value="1"></td>
    <td class="col-unit"><input type="text" data-line="unit" class="mono" value="EA" maxlength="3"></td>
    <td class="col-num"><input type="number" data-line="unit_price" class="mono" min="0" step="0.01" value="0.00"></td>
    <td class="col-cat">
      <select data-line="tax_category">
        ${TAX_CATEGORIES.map((c) => `<option value="${c}">${c}</option>`).join("")}
      </select>
    </td>
    <td class="col-num"><input type="number" data-line="tax_percent" class="mono" min="0" step="1" value="0"></td>
    <td class="col-num line-total-cell">0.00</td>
    <td class="col-actions">
      <button type="button" class="remove-line" title="Remove line">×</button>
    </td>
  `;
  // Populate from line object
  Object.entries(line).forEach(([k, v]) => {
    const el = tr.querySelector(`[data-line="${k}"]`);
    if (el) el.value = v;
  });
  // Apply defaults if line is empty
  if (Object.keys(line).length === 0) {
    const d = getDefaults();
    tr.querySelector('[data-line="tax_category"]').value = d.tax_category;
    tr.querySelector('[data-line="tax_percent"]').value = d.tax_percent;
  }
  // Wire events
  tr.querySelectorAll("input, select").forEach((el) => {
    el.addEventListener("input", recalcTotals);
  });
  tr.querySelector(".remove-line").addEventListener("click", () => {
    if ($$(".line-row").length > 1) tr.remove();
    else clearLineRow(tr);
    recalcTotals();
  });
  return tr;
}

function clearLineRow(tr) {
  tr.querySelectorAll("input").forEach((el) => {
    if (el.dataset.line === "quantity") el.value = "1";
    else if (el.dataset.line === "unit") el.value = "EA";
    else if (el.dataset.line === "unit_price") el.value = "0.00";
    else if (el.dataset.line === "tax_percent") el.value = "0";
    else el.value = "";
  });
  tr.querySelector('[data-line="tax_category"]').value = "E";
  tr.querySelector(".line-total-cell").textContent = "0.00";
}

function readLine(tr) {
  const line = {};
  tr.querySelectorAll("[data-line]").forEach((el) => {
    const key = el.dataset.line;
    line[key] = key === "quantity" || key === "unit_price" || key === "tax_percent" ? Number(el.value || 0) : el.value;
  });
  return line;
}

function recalcTotals() {
  const groups = new Map(); // key: cat|pct -> taxable
  let lineSum = 0;
  $$(".line-row").forEach((tr) => {
    const line = readLine(tr);
    const ext = (line.quantity || 0) * (line.unit_price || 0);
    tr.querySelector(".line-total-cell").textContent = fmt(ext);
    lineSum += ext;
    const key = `${line.tax_category}|${line.tax_percent}`;
    groups.set(key, (groups.get(key) || 0) + ext);
  });
  let taxTotal = 0;
  groups.forEach((taxable, key) => {
    const pct = Number(key.split("|")[1] || 0);
    taxTotal += (taxable * pct) / 100;
  });
  const currency = $("#currency").value || "EUR";
  $("#subtotal-display").textContent = fmt(lineSum);
  $("#tax-display").textContent = fmt(taxTotal);
  $("#grand-display").textContent = `${fmt(lineSum + taxTotal)} ${currency}`;
}

// ---------- Form collection ----------

function collectInvoice() {
  const lines = $$(".line-row").map((tr, i) => {
    const l = readLine(tr);
    return { id: String(i + 1), ...l };
  }).filter((l) => l.description || l.unit_price);

  const buyer = getBuyer();
  // The seller may have been filled from Peppyrus; fall back to cache.
  const seller = sellerCache || {};

  return {
    invoice_number: $("#invoice_number").value,
    issue_date: $("#issue_date").value,
    due_date: $("#due_date").value || undefined,
    invoice_type_code: "380",
    currency: $("#currency").value || "EUR",
    payment_terms: $("#payment_terms").value || undefined,
    seller,
    buyer,
    lines,
  };
}

// ---------- Validate / Send ----------

async function doValidate() {
  const invoice = collectInvoice();
  setBusy("#validate-btn", "Validating…");
  try {
    const resp = await fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(invoice),
    });
    const data = await resp.json();
    renderRules(data.rules || []);
  } catch (err) {
    showResult({ kind: "error", title: "Validation failed", summary: String(err) });
  } finally {
    clearBusy("#validate-btn", "Validate");
  }
}

async function doSend() {
  const invoice = collectInvoice();
  const recipient = $("#recipient").value.trim();
  if (!recipient) {
    showResult({ kind: "error", title: "Missing recipient", summary: "Enter a participant ID before sending." });
    return;
  }
  setBusy("#send-btn", "Sending…");
  try {
    const resp = await fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invoice, recipient }),
    });
    const data = await resp.json();
    if (resp.status === 422) {
      renderRules(data.rules || [], "Validation failed — invoice not sent");
      return;
    }
    if (!resp.ok) {
      showResult({ kind: "error", title: `HTTP ${resp.status}`, summary: JSON.stringify(data.response || data, null, 2) });
      return;
    }
    const r = data.response || {};
    const msgId = r.id || "(no id)";
    showResult({
      kind: "success",
      title: "Invoice sent",
      summary: `Message ID <strong>${msgId}</strong> · Folder <strong>${r.folder || "—"}</strong>`,
    });
    // On success: persist customer + advance invoice number
    saveCustomer(invoice.buyer);
    renderCustomerDropdown();
    lsSet(LS_KEYS.lastNumber, invoice.invoice_number);
    $("#invoice_number").value = nextInvoiceNumber();
  } catch (err) {
    showResult({ kind: "error", title: "Send failed", summary: String(err) });
  } finally {
    clearBusy("#send-btn", "Send invoice");
  }
}

function setBusy(sel, label) {
  const btn = $(sel);
  btn.disabled = true;
  btn.dataset.originalLabel = btn.textContent;
  btn.textContent = label;
}

function clearBusy(sel, label) {
  const btn = $(sel);
  btn.disabled = false;
  btn.textContent = label;
}

// ---------- Result panel rendering ----------

function showResult({ kind, title, summary }) {
  const panel = $("#result-panel");
  panel.hidden = false;
  panel.className = "result-panel " + kind;
  panel.innerHTML = `
    <h3>${title}</h3>
    <p class="summary">${summary}</p>
  `;
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderRules(rules, titleOverride) {
  const panel = $("#result-panel");
  panel.hidden = false;
  if (rules.length === 0) {
    panel.className = "result-panel success";
    panel.innerHTML = `
      <h3>Validation passed</h3>
      <p class="summary">No structural or XSD errors detected.</p>
    `;
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return;
  }
  const fatal = rules.filter((r) => r.type === "FATAL").length;
  const warn = rules.filter((r) => r.type === "WARNING").length;
  panel.className = "result-panel " + (fatal > 0 ? "error" : "success");
  panel.innerHTML = `
    <h3>${titleOverride || "Validation results"}</h3>
    <p class="meta">${fatal} fatal · ${warn} warning</p>
    <ul>
      ${rules.map((r) => `
        <li class="rule ${r.type === "WARNING" ? "warning" : ""}">
          <span class="badge">${r.type}</span>
          <span class="rule-id">${escape(r.id)}</span>
          <span class="rule-msg">${escape(r.message)}</span>
          <span class="rule-loc">${escape(r.location)}</span>
        </li>
      `).join("")}
    </ul>
  `;
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function escape(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

// ---------- Settings modal ----------

function openSettings() {
  const d = getDefaults();
  $("#default-currency").value = d.currency;
  $("#default-payment-terms").value = d.payment_terms;
  $("#default-due-days").value = d.due_days;
  $("#default-tax-category").value = d.tax_category;
  $("#default-tax-percent").value = d.tax_percent;
  $("#settings-modal").showModal();
}

function saveSettingsFromModal() {
  saveDefaults({
    currency: $("#default-currency").value || "EUR",
    payment_terms: $("#default-payment-terms").value,
    due_days: Number($("#default-due-days").value || 30),
    tax_category: $("#default-tax-category").value || "E",
    tax_percent: Number($("#default-tax-percent").value || 0),
  });
  $("#settings-modal").close();
  applyDefaultsToForm();
}

function applyDefaultsToForm() {
  const d = getDefaults();
  if (!$("#currency").value) $("#currency").value = d.currency;
  if (!$("#payment_terms").value) $("#payment_terms").value = d.payment_terms;
  if (!$("#due_date").value && $("#issue_date").value) {
    $("#due_date").value = addDays($("#issue_date").value, d.due_days);
  }
}

// ---------- Initialization ----------

function init() {
  // Populate header form fields
  $("#invoice_number").value = nextInvoiceNumber();
  $("#issue_date").value = todayISO();

  applyDefaultsToForm();

  // Update due date when issue date changes
  $("#issue_date").addEventListener("change", () => {
    const d = getDefaults();
    $("#due_date").value = addDays($("#issue_date").value, d.due_days);
  });

  // Currency drives totals display
  $("#currency").addEventListener("input", recalcTotals);

  // Initial empty line
  $("#line-items-body").appendChild(makeLineRow());
  recalcTotals();

  // Add line button
  $("#add-line-btn").addEventListener("click", () => {
    $("#line-items-body").appendChild(makeLineRow());
    recalcTotals();
  });

  // Recent customers
  renderCustomerDropdown();
  $("#recent-customers").addEventListener("change", (e) => {
    const i = e.target.value;
    if (i === "") return;
    const customer = loadCustomers()[Number(i)];
    if (customer) setBuyer(customer);
  });

  // Templates
  renderTemplateDropdown();
  $("#template-select").addEventListener("change", (e) => {
    const i = e.target.value;
    if (i === "") return;
    const tpl = loadTemplates()[Number(i)];
    if (tpl) {
      const tr = makeLineRow(tpl);
      $("#line-items-body").appendChild(tr);
      recalcTotals();
    }
    e.target.value = "";
  });

  // Lookup
  $("#lookup-btn").addEventListener("click", lookupBuyer);
  $("#lookup-vat").addEventListener("keydown", (e) => { if (e.key === "Enter") lookupBuyer(); });

  // Validate / Send
  $("#validate-btn").addEventListener("click", doValidate);
  $("#send-btn").addEventListener("click", doSend);

  // Settings modal
  $("#settings-btn").addEventListener("click", openSettings);
  $("#settings-cancel").addEventListener("click", () => $("#settings-modal").close());
  $("#settings-save").addEventListener("click", saveSettingsFromModal);

  // Seller info
  loadSeller();
}

document.addEventListener("DOMContentLoaded", init);
