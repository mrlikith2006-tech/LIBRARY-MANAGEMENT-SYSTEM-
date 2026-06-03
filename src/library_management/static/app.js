const state = {
  view: "dashboard",
  editing: null,
  search: "",
  issueFilter: "active",
  data: {
    summary: null,
    members: [],
    books: [],
    librarians: [],
    issues: [],
  },
};

const TITLES = {
  dashboard: ["Dashboard", "Schema-backed operations"],
  issues: ["Issue Records", "Borrow and return transactions"],
  books: ["Books", "Catalog and stock"],
  members: ["Members", "Borrower directory"],
  librarians: ["Librarians", "Staff handling issues"],
  schema: ["Schema", "Database architecture"],
};

const content = document.getElementById("content");
const alertRegion = document.getElementById("alert-region");
const sectionTitle = document.getElementById("section-title");
const sectionKicker = document.getElementById("section-kicker");

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  document.getElementById("refresh-button").addEventListener("click", loadAll);
  document.addEventListener("submit", handleSubmit);
  document.addEventListener("click", handleClick);
  document.addEventListener("input", handleInput);
  loadAll();
});

async function loadAll() {
  try {
    const [summary, members, books, librarians, issues] = await Promise.all([
      api("/api/summary"),
      api("/api/members"),
      api("/api/books"),
      api("/api/librarians"),
      api("/api/issues"),
    ]);
    state.data.summary = summary.summary;
    state.data.members = members.members;
    state.data.books = books.books;
    state.data.librarians = librarians.librarians;
    state.data.issues = issues.issues;
    render();
  } catch (error) {
    showAlert(error.message, "error");
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

function setView(view) {
  state.view = view;
  state.editing = null;
  state.search = "";
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  render();
}

function render() {
  const [title, kicker] = TITLES[state.view];
  sectionTitle.textContent = title;
  sectionKicker.textContent = kicker;
  if (state.view === "dashboard") content.innerHTML = renderDashboard();
  if (state.view === "issues") content.innerHTML = renderIssues();
  if (state.view === "books") content.innerHTML = renderBooks();
  if (state.view === "members") content.innerHTML = renderMembers();
  if (state.view === "librarians") content.innerHTML = renderLibrarians();
  if (state.view === "schema") content.innerHTML = renderSchema();
}

function renderDashboard() {
  const summary = state.data.summary || {};
  const activeIssues = state.data.issues.filter((issue) => issue.status === "Issued").slice(0, 6);
  return `
    <div class="dashboard-grid">
      <div class="stack">
        <div class="metric-grid">
          ${metric("Members", summary.member_count, "teal")}
          ${metric("Books", summary.book_count, "green")}
          ${metric("Librarians", summary.librarian_count, "purple")}
          ${metric("Active issues", summary.active_issues, "amber")}
          ${metric("Overdue", summary.overdue_count, "red")}
          ${metric("Available copies", summary.available_copies, "orange")}
        </div>
        <div class="panel">
          <div class="panel-header">
            <h3>Active Issue Queue</h3>
            <button class="secondary-button" type="button" data-view="issues">Open Issues</button>
          </div>
          <div class="panel-body">
            ${renderIssuesTable(activeIssues, false)}
          </div>
        </div>
      </div>
      <div class="stack">
        <div class="visual-band">
          <img src="/static/library-visual.png" alt="Illustrated library shelves and reading desk" />
          <div class="visual-copy">
            <h3>Schema Driven</h3>
            <p>Every issue connects one member, one book, and one librarian, while available copies update at borrow and return time.</p>
          </div>
        </div>
        <div class="entity-card">
          <h3>Issue a Book</h3>
          ${renderIssueForm("dashboard")}
        </div>
      </div>
    </div>
  `;
}

function metric(label, value, tone) {
  return `
    <div class="metric-card" data-tone="${tone}">
      <p>${escapeHtml(label)}</p>
      <strong>${Number(value || 0)}</strong>
    </div>
  `;
}

function renderMembers() {
  const editing = getEditing("members");
  const rows = filterRows(state.data.members, ["name", "address", "phone"]);
  return `
    <div class="entity-layout">
      <div class="entity-card">
        <h3>${editing ? "Edit Member" : "Add Member"}</h3>
        <form id="member-form" class="form-grid" data-id="${editing ? editing.member_id : ""}">
          <div class="form-field">
            <label for="member-name">Name</label>
            <input id="member-name" name="name" maxlength="50" required value="${escapeAttr(editing?.name || "")}" />
          </div>
          <div class="form-field">
            <label for="member-address">Address</label>
            <input id="member-address" name="address" maxlength="100" required value="${escapeAttr(editing?.address || "")}" />
          </div>
          <div class="form-field">
            <label for="member-phone">Phone</label>
            <input id="member-phone" name="phone" maxlength="15" required value="${escapeAttr(editing?.phone || "")}" />
          </div>
          <div class="button-row">
            <button class="primary-button" type="submit">${editing ? "Save Member" : "Add Member"}</button>
            ${editing ? `<button class="secondary-button" type="button" data-action="cancel-edit">Cancel</button>` : ""}
          </div>
        </form>
      </div>
      <div class="panel">
        ${renderTableTools("Search members")}
        <div class="panel-body">
          ${renderEntityTable(
            ["ID", "Name", "Address", "Phone", ""],
            rows.map((member) => [
              member.member_id,
              member.name,
              member.address,
              member.phone,
              actionButtons("members", member.member_id),
            ])
          )}
        </div>
      </div>
    </div>
  `;
}

function renderBooks() {
  const editing = getEditing("books");
  const rows = filterRows(state.data.books, ["title", "author", "publisher", "year"]);
  return `
    <div class="entity-layout">
      <div class="entity-card">
        <h3>${editing ? "Edit Book" : "Add Book"}</h3>
        <form id="book-form" class="form-grid two" data-id="${editing ? editing.book_id : ""}">
          <div class="form-field full">
            <label for="book-title">Title</label>
            <input id="book-title" name="title" maxlength="50" required value="${escapeAttr(editing?.title || "")}" />
          </div>
          <div class="form-field">
            <label for="book-author">Author</label>
            <input id="book-author" name="author" maxlength="50" required value="${escapeAttr(editing?.author || "")}" />
          </div>
          <div class="form-field">
            <label for="book-publisher">Publisher</label>
            <input id="book-publisher" name="publisher" maxlength="50" required value="${escapeAttr(editing?.publisher || "")}" />
          </div>
          <div class="form-field">
            <label for="book-year">Year</label>
            <input id="book-year" name="year" type="number" min="1400" max="2200" required value="${escapeAttr(editing?.year || new Date().getFullYear())}" />
          </div>
          <div class="form-field">
            <label for="book-copies">Available Copies</label>
            <input id="book-copies" name="available_copies" type="number" min="0" required value="${escapeAttr(editing?.available_copies ?? 1)}" />
          </div>
          <div class="button-row full">
            <button class="primary-button" type="submit">${editing ? "Save Book" : "Add Book"}</button>
            ${editing ? `<button class="secondary-button" type="button" data-action="cancel-edit">Cancel</button>` : ""}
          </div>
        </form>
      </div>
      <div class="panel">
        ${renderTableTools("Search books")}
        <div class="panel-body">
          ${renderEntityTable(
            ["ID", "Title", "Author", "Publisher", "Year", "Copies", ""],
            rows.map((book) => [
              book.book_id,
              book.title,
              book.author,
              book.publisher,
              book.year,
              book.available_copies,
              actionButtons("books", book.book_id),
            ])
          )}
        </div>
      </div>
    </div>
  `;
}

function renderLibrarians() {
  const editing = getEditing("librarians");
  const rows = filterRows(state.data.librarians, ["name"]);
  return `
    <div class="entity-layout">
      <div class="entity-card">
        <h3>${editing ? "Edit Librarian" : "Add Librarian"}</h3>
        <form id="librarian-form" class="form-grid" data-id="${editing ? editing.librarian_id : ""}">
          <div class="form-field">
            <label for="librarian-name">Name</label>
            <input id="librarian-name" name="name" maxlength="50" required value="${escapeAttr(editing?.name || "")}" />
          </div>
          <div class="button-row">
            <button class="primary-button" type="submit">${editing ? "Save Librarian" : "Add Librarian"}</button>
            ${editing ? `<button class="secondary-button" type="button" data-action="cancel-edit">Cancel</button>` : ""}
          </div>
        </form>
      </div>
      <div class="panel">
        ${renderTableTools("Search librarians")}
        <div class="panel-body">
          ${renderEntityTable(
            ["ID", "Name", ""],
            rows.map((librarian) => [
              librarian.librarian_id,
              librarian.name,
              actionButtons("librarians", librarian.librarian_id),
            ])
          )}
        </div>
      </div>
    </div>
  `;
}

function renderIssues() {
  const issues = state.data.issues.filter((issue) => {
    if (state.issueFilter === "active") return issue.status === "Issued";
    if (state.issueFilter === "returned") return issue.status === "Returned";
    if (state.issueFilter === "overdue") return issue.is_overdue;
    return true;
  });
  const rows = filterRows(issues, ["member_name", "book_title", "librarian_name", "status"]);
  return `
    <div class="entity-layout">
      <div class="entity-card">
        <h3>Issue a Book</h3>
        ${renderIssueForm("issues")}
      </div>
      <div class="panel">
        <div class="panel-header">
          <div class="segment-control" aria-label="Issue filters">
            ${segmentButton("active", "Active")}
            ${segmentButton("overdue", "Overdue")}
            ${segmentButton("returned", "Returned")}
            ${segmentButton("all", "All")}
          </div>
          <input class="search-input" type="search" value="${escapeAttr(state.search)}" placeholder="Search issue records" data-action="search" />
        </div>
        <div class="panel-body">
          ${renderIssuesTable(rows, true)}
        </div>
      </div>
    </div>
  `;
}

function renderIssueForm(scope) {
  return `
    <form id="issue-form" class="form-grid" data-scope="${scope}">
      <div class="form-field">
        <label for="issue-member-${scope}">Member</label>
        <select id="issue-member-${scope}" name="member_id" required>
          <option value="">Select member</option>
          ${state.data.members.map((member) => `<option value="${member.member_id}">${escapeHtml(member.name)}</option>`).join("")}
        </select>
      </div>
      <div class="form-field">
        <label for="issue-book-${scope}">Book</label>
        <select id="issue-book-${scope}" name="book_id" required>
          <option value="">Select book</option>
          ${state.data.books
            .map((book) => `<option value="${book.book_id}" ${book.available_copies <= 0 ? "disabled" : ""}>${escapeHtml(book.title)} (${book.available_copies} available)</option>`)
            .join("")}
        </select>
      </div>
      <div class="form-field">
        <label for="issue-librarian-${scope}">Librarian</label>
        <select id="issue-librarian-${scope}" name="librarian_id" required>
          <option value="">Select librarian</option>
          ${state.data.librarians.map((librarian) => `<option value="${librarian.librarian_id}">${escapeHtml(librarian.name)}</option>`).join("")}
        </select>
      </div>
      <div class="form-field">
        <label for="issue-date-${scope}">Issue Date</label>
        <input id="issue-date-${scope}" name="issue_date" type="date" required value="${today()}" />
      </div>
      <button class="primary-button" type="submit">Issue Book</button>
    </form>
  `;
}

function renderSchema() {
  return `
    <div class="schema-grid">
      ${schemaTable("member", "MEMBER", [
        ["PK", "MemberID", "INT"],
        ["", "Name", "VARCHAR(50)"],
        ["", "Address", "VARCHAR(100)"],
        ["", "Phone", "VARCHAR(15)"],
      ])}
      ${schemaTable("issue", "ISSUE", [
        ["PK", "IssueID", "INT"],
        ["FK", "MemberID", "INT"],
        ["FK", "BookID", "INT"],
        ["FK", "LibrarianID", "INT"],
        ["", "IssueDate", "DATE"],
        ["", "ReturnDate", "DATE"],
      ])}
      ${schemaTable("book", "BOOK", [
        ["PK", "BookID", "INT"],
        ["", "Title", "VARCHAR(50)"],
        ["", "Author", "VARCHAR(50)"],
        ["", "Publisher", "VARCHAR(50)"],
        ["", "Year", "INT"],
        ["", "Available_Copies", "INT"],
      ])}
      ${schemaTable("librarian", "LIBRARIAN", [
        ["PK", "LibrarianID", "INT"],
        ["", "Name", "VARCHAR(50)"],
      ])}
      <div class="schema-legend">
        <h3>Relationships</h3>
        <ul class="relationship-list">
          <li>A member can issue many books through Issue records. (1:M)</li>
          <li>A book can be issued many times through Issue records. (1:M)</li>
          <li>A librarian can handle many issue and return records. (1:M)</li>
        </ul>
      </div>
      <div class="schema-legend">
        <h3>Table Summary</h3>
        <ul class="summary-list">
          <li>Member stores borrower details.</li>
          <li>Book stores catalog and copy information.</li>
          <li>Librarian stores staff details.</li>
          <li>Issue links member, book, librarian, issue date, and return date.</li>
        </ul>
      </div>
    </div>
  `;
}

function schemaTable(tone, title, rows) {
  return `
    <div class="schema-table">
      <div class="schema-title ${tone}">${title}</div>
      ${rows.map(([key, name, type]) => `
        <div class="schema-row">
          <span class="schema-key">${key}</span>
          <strong>${name}</strong>
          <span>${type}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderTableTools(placeholder) {
  return `
    <div class="panel-header">
      <input class="search-input" type="search" value="${escapeAttr(state.search)}" placeholder="${escapeAttr(placeholder)}" data-action="search" />
      <button class="secondary-button" type="button" data-action="clear-search">Clear</button>
    </div>
  `;
}

function renderEntityTable(headers, rows) {
  if (!rows.length) {
    return `<div class="empty-state">No records found.</div>`;
  }
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>${row.map((cell, index) => {
              const isActionCell = index === row.length - 1 && headers[index] === "";
              return `<td${isActionCell ? ` class="row-actions"` : ""}>${isActionCell ? cell : escapeHtml(cell)}</td>`;
            }).join("")}</tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderIssuesTable(issues, includeActions) {
  if (!issues.length) {
    return `<div class="empty-state">No issue records found.</div>`;
  }
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Member</th>
            <th>Book</th>
            <th>Librarian</th>
            <th>Issue Date</th>
            <th>Due Date</th>
            <th>Return Date</th>
            <th>Status</th>
            ${includeActions ? "<th></th>" : ""}
          </tr>
        </thead>
        <tbody>
          ${issues.map((issue) => `
            <tr>
              <td>${issue.issue_id}</td>
              <td>${escapeHtml(issue.member_name)}</td>
              <td>${escapeHtml(issue.book_title)}</td>
              <td>${escapeHtml(issue.librarian_name)}</td>
              <td>${escapeHtml(issue.issue_date)}</td>
              <td>${escapeHtml(issue.due_date)}</td>
              <td>${escapeHtml(issue.return_date || "-")}</td>
              <td>${issueStatus(issue)}</td>
              ${includeActions ? `<td class="row-actions">${issue.status === "Issued" ? `<button class="small-icon" type="button" title="Return book" data-action="return-issue" data-id="${issue.issue_id}">RT</button>` : ""}</td>` : ""}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function issueStatus(issue) {
  if (issue.is_overdue) return `<span class="status-pill overdue">Overdue</span>`;
  if (issue.status === "Issued") return `<span class="status-pill issued">Issued</span>`;
  return `<span class="status-pill returned">Returned</span>`;
}

function segmentButton(value, label) {
  return `<button type="button" data-action="filter-issues" data-filter="${value}" class="${state.issueFilter === value ? "active" : ""}">${label}</button>`;
}

function actionButtons(table, id) {
  return `
    <button class="small-icon" type="button" title="Edit" data-action="edit" data-table="${table}" data-id="${id}">ED</button>
    <button class="small-icon" type="button" title="Delete" data-action="delete" data-table="${table}" data-id="${id}">DL</button>
  `;
}

async function handleSubmit(event) {
  if (!event.target.matches("form")) return;
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form).entries());
  try {
    if (form.id === "member-form") {
      await saveEntity("members", form.dataset.id, data);
      showAlert("Member saved.", "success");
    }
    if (form.id === "book-form") {
      data.year = Number(data.year);
      data.available_copies = Number(data.available_copies);
      await saveEntity("books", form.dataset.id, data);
      showAlert("Book saved.", "success");
    }
    if (form.id === "librarian-form") {
      await saveEntity("librarians", form.dataset.id, data);
      showAlert("Librarian saved.", "success");
    }
    if (form.id === "issue-form") {
      await api("/api/issues", {
        method: "POST",
        body: JSON.stringify({
          member_id: Number(data.member_id),
          book_id: Number(data.book_id),
          librarian_id: Number(data.librarian_id),
          issue_date: data.issue_date,
        }),
      });
      showAlert("Book issued.", "success");
    }
    state.editing = null;
    await loadAll();
  } catch (error) {
    showAlert(error.message, "error");
  }
}

async function saveEntity(table, id, data) {
  const path = id ? `/api/${table}/${id}` : `/api/${table}`;
  await api(path, {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(data),
  });
}

async function handleClick(event) {
  const viewButton = event.target.closest("[data-view]");
  if (viewButton) {
    setView(viewButton.dataset.view);
    return;
  }
  const action = event.target.closest("[data-action]");
  if (!action) return;
  const kind = action.dataset.action;
  if (kind === "cancel-edit") {
    state.editing = null;
    render();
  }
  if (kind === "clear-search") {
    state.search = "";
    render();
  }
  if (kind === "filter-issues") {
    state.issueFilter = action.dataset.filter;
    render();
  }
  if (kind === "edit") {
    state.editing = { table: action.dataset.table, id: Number(action.dataset.id) };
    render();
  }
  if (kind === "delete") {
    await deleteEntity(action.dataset.table, Number(action.dataset.id));
  }
  if (kind === "return-issue") {
    await returnIssue(Number(action.dataset.id));
  }
}

function handleInput(event) {
  if (!event.target.matches("[data-action='search']")) return;
  state.search = event.target.value;
  render();
  const search = document.querySelector("[data-action='search']");
  if (search) search.focus();
}

async function deleteEntity(table, id) {
  const label = table.slice(0, -1);
  if (!confirm(`Delete this ${label}? Issue history can prevent deletion.`)) return;
  try {
    await api(`/api/${table}/${id}`, { method: "DELETE" });
    showAlert("Record deleted.", "success");
    state.editing = null;
    await loadAll();
  } catch (error) {
    showAlert(error.message, "error");
  }
}

async function returnIssue(issueId) {
  if (!confirm("Mark this book as returned today?")) return;
  try {
    await api(`/api/issues/${issueId}/return`, {
      method: "POST",
      body: JSON.stringify({ return_date: today() }),
    });
    showAlert("Book returned and copy count updated.", "success");
    await loadAll();
  } catch (error) {
    showAlert(error.message, "error");
  }
}

function getEditing(table) {
  if (!state.editing || state.editing.table !== table) return null;
  const key = table.slice(0, -1) + "_id";
  return state.data[table].find((item) => Number(item[key]) === Number(state.editing.id)) || null;
}

function filterRows(rows, fields) {
  const query = state.search.trim().toLowerCase();
  if (!query) return rows;
  return rows.filter((row) => fields.some((field) => String(row[field] ?? "").toLowerCase().includes(query)));
}

function today() {
  const current = new Date();
  current.setMinutes(current.getMinutes() - current.getTimezoneOffset());
  return current.toISOString().slice(0, 10);
}

function showAlert(message, type) {
  alertRegion.innerHTML = `<div class="alert ${type}">${escapeHtml(message)}</div>`;
  window.clearTimeout(showAlert.timer);
  showAlert.timer = window.setTimeout(() => {
    alertRegion.innerHTML = "";
  }, 3600);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}
