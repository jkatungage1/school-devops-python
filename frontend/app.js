/* Campus dashboard — vanilla JS client for the two microservices.
 *
 * Service A (Students) is reached on :8001, Service B (Courses) on :8002.
 * When opened from a non-localhost host the same hostname is reused so the
 * page also works when served by nginx in docker-compose.
 */

const HOST = window.location.hostname || "localhost";
const STUDENTS_API = `http://${HOST}:8001`;
const COURSES_API = `http://${HOST}:8002`;

const $ = (sel) => document.querySelector(sel);

// State caches used to populate dropdowns and stats.
let students = [];
let courses = [];

/* ---------------------------------------------------------------- helpers */
function toast(message, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || `${res.status} ${res.statusText}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function gradeClass(value) {
  if (value == null) return "g-none";
  if (value >= 14) return "g-good";
  if (value >= 10) return "g-mid";
  return "g-bad";
}

/* --------------------------------------------------------- health + addrs */
function setAddresses() {
  $("#addr-students").textContent = STUDENTS_API.replace("http://", "");
  $("#addr-courses").textContent = COURSES_API.replace("http://", "");
}

async function pingService(api_base, pillId) {
  const pill = $(pillId);
  try {
    await api(`${api_base}/health`);
    pill.classList.add("online");
    pill.classList.remove("offline");
  } catch {
    pill.classList.add("offline");
    pill.classList.remove("online");
  }
}

/* ----------------------------------------------------------- render lists */
function renderStudents() {
  const body = $("#students-body");
  $("#stat-students").textContent = students.length;
  if (!students.length) {
    body.innerHTML = `<tr><td colspan="4" class="muted">No students yet.</td></tr>`;
    return;
  }
  body.innerHTML = students
    .map(
      (s) => `
      <tr>
        <td>${s.id}</td>
        <td><strong>${s.first_name} ${s.last_name}</strong></td>
        <td class="muted">${s.email}</td>
        <td>
          <div class="row-actions">
            <button class="btn tiny outline" data-transcript="${s.id}" data-name="${s.first_name} ${s.last_name}">Transcript</button>
            <button class="btn tiny danger" data-delete="${s.id}">Delete</button>
          </div>
        </td>
      </tr>`
    )
    .join("");
}

function renderCourses() {
  const list = $("#course-list");
  $("#stat-courses").textContent = courses.length;
  if (!courses.length) {
    list.innerHTML = `<li class="muted">No courses yet.</li>`;
    return;
  }
  list.innerHTML = courses
    .map(
      (c) => `
      <li>
        <span class="ccode">${c.code}</span>
        <span class="ctitle">${c.title}</span>
        <span class="badge">${c.credits} cr</span>
      </li>`
    )
    .join("");
}

function fillStudentSelects() {
  const opts = students
    .map((s) => `<option value="${s.id}">${s.first_name} ${s.last_name} (#${s.id})</option>`)
    .join("");
  $("#enroll-student").innerHTML = opts;
  $("#grade-student").innerHTML = opts;
}

function fillCourseSelects() {
  const opts = courses
    .map((c) => `<option value="${c.code}">${c.code} — ${c.title}</option>`)
    .join("");
  $("#enroll-course").innerHTML = opts;
  $("#grade-course").innerHTML = opts;
}

async function refreshStats() {
  // Enrollments + GPA aggregated from the grades endpoint of Service B.
  try {
    const grades = await api(`${COURSES_API}/grades`);
    if (grades.length) {
      const avg = grades.reduce((a, g) => a + g.value, 0) / grades.length;
      $("#stat-gpa").textContent = avg.toFixed(1);
    } else {
      $("#stat-gpa").textContent = "—";
    }
  } catch {
    $("#stat-gpa").textContent = "—";
  }
}

/* ----------------------------------------------------------------- loaders */
async function loadStudents() {
  try {
    students = await api(`${STUDENTS_API}/students`);
    renderStudents();
    fillStudentSelects();
  } catch (e) {
    toast(`Students: ${e.message}`, "err");
  }
}

async function loadCourses() {
  try {
    courses = await api(`${COURSES_API}/courses`);
    renderCourses();
    fillCourseSelects();
  } catch (e) {
    toast(`Courses: ${e.message}`, "err");
  }
}

async function loadEnrollmentCount() {
  // Sum transcript lines across students for the enrollments stat.
  let total = 0;
  for (const s of students) {
    try {
      const t = await api(`${STUDENTS_API}/students/${s.id}/transcript`);
      total += t.lines.length;
    } catch {
      /* ignore individual failures */
    }
  }
  $("#stat-enrollments").textContent = total;
}

async function refreshAll() {
  await Promise.all([loadStudents(), loadCourses()]);
  await Promise.all([refreshStats(), loadEnrollmentCount()]);
}

/* ----------------------------------------------------------- transcript */
async function openTranscript(studentId, name) {
  try {
    const t = await api(`${STUDENTS_API}/students/${studentId}/transcript`);
    $("#modal-title").textContent = `Transcript — ${name}`;
    $("#modal-gpa").textContent = t.gpa != null ? t.gpa.toFixed(2) : "—";
    const body = $("#modal-body");
    if (!t.lines.length) {
      body.innerHTML = `<tr><td colspan="3" class="muted">No enrollments yet.</td></tr>`;
    } else {
      body.innerHTML = t.lines
        .map(
          (l) => `
          <tr>
            <td><code>${l.course_code}</code></td>
            <td>${l.course_title || "—"}</td>
            <td class="right"><span class="${gradeClass(l.grade)}">${
            l.grade != null ? l.grade.toFixed(1) : "n/a"
          }</span></td>
          </tr>`
        )
        .join("");
    }
    $("#modal").hidden = false;
  } catch (e) {
    toast(`Transcript: ${e.message}`, "err");
  }
}

/* --------------------------------------------------------------- handlers */
$("#form-student").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api(`${STUDENTS_API}/students`, {
      method: "POST",
      body: JSON.stringify({
        first_name: f.get("first_name"),
        last_name: f.get("last_name"),
        email: f.get("email"),
      }),
    });
    e.target.reset();
    toast("Student added", "ok");
    await refreshAll();
  } catch (err) {
    toast(err.message, "err");
  }
});

$("#form-course").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api(`${COURSES_API}/courses`, {
      method: "POST",
      body: JSON.stringify({
        code: f.get("code"),
        title: f.get("title"),
        credits: Number(f.get("credits")) || 3,
      }),
    });
    e.target.reset();
    toast("Course added", "ok");
    await loadCourses();
  } catch (err) {
    toast(err.message, "err");
  }
});

$("#form-enroll").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api(`${STUDENTS_API}/students/${f.get("student_id")}/enroll`, {
      method: "POST",
      body: JSON.stringify({ course_code: f.get("course_code") }),
    });
    toast("Enrolled (course validated via Courses API)", "ok");
    await loadEnrollmentCount();
  } catch (err) {
    toast(err.message, "err");
  }
});

$("#form-grade").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api(`${COURSES_API}/grades`, {
      method: "POST",
      body: JSON.stringify({
        student_id: Number(f.get("student_id")),
        course_code: f.get("course_code"),
        value: Number(f.get("value")),
      }),
    });
    e.target.reset();
    toast("Grade recorded", "ok");
    await refreshStats();
  } catch (err) {
    toast(err.message, "err");
  }
});

$("#students-body").addEventListener("click", async (e) => {
  const t = e.target.closest("button");
  if (!t) return;
  if (t.dataset.transcript) {
    openTranscript(t.dataset.transcript, t.dataset.name);
  } else if (t.dataset.delete) {
    if (!confirm("Delete this student?")) return;
    try {
      await api(`${STUDENTS_API}/students/${t.dataset.delete}`, { method: "DELETE" });
      toast("Student deleted", "ok");
      await refreshAll();
    } catch (err) {
      toast(err.message, "err");
    }
  }
});

$("#modal-close").addEventListener("click", () => ($("#modal").hidden = true));
$("#modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") $("#modal").hidden = true;
});
$("#btn-refresh").addEventListener("click", refreshAll);

/* ------------------------------------------------------------------- boot */
setAddresses();
pingService(STUDENTS_API, "#pill-students");
pingService(COURSES_API, "#pill-courses");
refreshAll();
setInterval(() => {
  pingService(STUDENTS_API, "#pill-students");
  pingService(COURSES_API, "#pill-courses");
}, 8000);
