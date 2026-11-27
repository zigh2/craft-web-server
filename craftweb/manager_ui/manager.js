"use strict";
(() => {
const T = {
en: {
title:"Craft Web Server", sub:"Manager", running:"Running", stopped:"Stopped", not_installed:"Not installed",
st_running:"Your apps are online.", st_stopped:"The server is installed but not running.", st_not_installed:"The server is not installed yet.",
autostart:"Starts after every restart", yes:"Yes", no:"No", watchdog:"Restarts itself if it stops", apps_addr:"Apps address", dash_addr:"Dashboard address", data_dir:"Your data (kept when you update)", prog_dir:"Program folder", copy:"Copy", copied:"Copied",
need_admin:"Administrator rights are needed to install or change the background service.", as_admin:"Restart as administrator", closing:"A new window is opening: continue there.",
legacy:"Data from an older version was found inside the program folder.", migrate:"Move it to the safe location",
install_h:"Install", install_btn:"Install and start in the background", pw_label:"Choose the dashboard password (at least 10 characters)",
w1:"Runs in the background and starts by itself after every restart of the computer", w2:"Restarts itself if it ever stops", w3:"Keeps your data in a safe folder: updating never asks for the password again", w4:"Allows other devices on your private network to connect (firewall rule)",
start:"Start", stop:"Stop", restart:"Restart", open_dash:"Open dashboard", open_apps:"Open apps", control:"Control",
upd_h:"Updates", version:"Version", check_upd:"Check for updates", update_to:"Update to", up_to_date:"You have the latest version.", upd_unsupported:"Updating from here is not available for this kind of installation.", upd_offline:"Could not reach GitHub (the internet may be off).", upd_staged:"Downloaded: it applies on the next restart.",
upd_note:"Your apps, password and settings are not touched.",
health_h:"Check everything", health_btn:"Check now", health_run:"Checking…", fix_install:"Install", fix_start:"Start", fix_password:"Set password", fix_update:"Update", fix_migrate:"Move data",
logs_h:"Logs", log_server:"Server", log_console:"Crash output", log_audit:"Activity", refresh:"Refresh",
uninstall:"Remove auto-start", uninstall_q:"Remove the background service and the firewall rule? Your apps and data stay.", quit:"Close the Manager", cancel:"Cancel", confirm:"Confirm", close:"Close", save:"Save",
pw_title:"Set the dashboard password", pw_saved:"Password saved", running_job:"Working…", job_done:"Done", job_failed:"Failed", lang:"العربية",
err_need_admin:"Administrator rights are needed.", err_busy:"Another action is still running.", err_weak_password:"The password must be at least 10 characters.", err_auth:"Open the Manager from the program (the link it opens contains a secret)."
},
ar: {
title:"Craft Web Server", sub:"لوحة الإدارة", running:"يعمل", stopped:"متوقف", not_installed:"غير مثبّت",
st_running:"تطبيقاتك تعمل الآن.", st_stopped:"الخادم مثبّت لكنه متوقف.", st_not_installed:"لم يتم تثبيت الخادم بعد.",
autostart:"يبدأ بعد كل إعادة تشغيل", yes:"نعم", no:"لا", watchdog:"يعيد تشغيل نفسه إن توقف", apps_addr:"عنوان التطبيقات", dash_addr:"عنوان لوحة التحكم", data_dir:"بياناتك (تبقى عند التحديث)", prog_dir:"مجلد البرنامج", copy:"نسخ", copied:"تم النسخ",
need_admin:"يلزم تشغيل البرنامج كمسؤول لتثبيت الخدمة أو تغييرها.", as_admin:"إعادة التشغيل كمسؤول", closing:"تُفتح نافذة جديدة: أكمل منها.",
legacy:"وُجدت بيانات من إصدار أقدم داخل مجلد البرنامج.", migrate:"انقلها إلى المكان الآمن",
install_h:"التثبيت", install_btn:"تثبيت وتشغيل في الخلفية", pw_label:"اختر كلمة مرور لوحة التحكم (10 أحرف على الأقل)",
w1:"يعمل في الخلفية ويبدأ تلقائياً بعد كل إعادة تشغيل للحاسوب", w2:"يعيد تشغيل نفسه إن توقف لأي سبب", w3:"يحفظ بياناتك في مجلد آمن: لن تُسأل عن كلمة المرور عند كل تحديث", w4:"يسمح للأجهزة في شبكتك الخاصة بالاتصال (قاعدة جدار ناري)",
start:"تشغيل", stop:"إيقاف", restart:"إعادة تشغيل", open_dash:"فتح لوحة التحكم", open_apps:"فتح التطبيقات", control:"التحكم",
upd_h:"التحديثات", version:"الإصدار", check_upd:"فحص التحديثات", update_to:"التحديث إلى", up_to_date:"لديك أحدث إصدار.", upd_unsupported:"التحديث من هنا غير متاح لهذا النوع من التثبيت.", upd_offline:"تعذّر الوصول إلى GitHub (قد يكون الإنترنت متوقفاً).", upd_staged:"تم التنزيل: يُطبَّق عند إعادة التشغيل القادمة.",
upd_note:"تطبيقاتك وكلمة المرور والإعدادات لا تتأثر.",
health_h:"فحص كل شيء", health_btn:"افحص الآن", health_run:"جارٍ الفحص…", fix_install:"تثبيت", fix_start:"تشغيل", fix_password:"تعيين كلمة المرور", fix_update:"تحديث", fix_migrate:"نقل البيانات",
chk_data:"مجلد البيانات", chk_disk:"مساحة القرص", chk_config:"ملف الإعدادات", chk_password:"كلمة مرور لوحة التحكم", chk_server:"الخادم", chk_ports:"المنافذ", chk_autostart:"التشغيل بعد إعادة التشغيل", chk_supervisor:"المراقب (إعادة التشغيل التلقائي)", chk_firewall:"الجدار الناري", chk_lan:"عنوان الشبكة", chk_https:"HTTPS", chk_apps:"التطبيقات", chk_logs:"الأخطاء الأخيرة", chk_internet:"الإنترنت (GitHub)", chk_update:"إصدار الخادم", logs_h:"السجلات", log_server:"الخادم", log_console:"مخرجات الانهيار", log_audit:"النشاط", refresh:"تحديث",
uninstall:"إزالة التشغيل التلقائي", uninstall_q:"إزالة الخدمة وقاعدة الجدار الناري؟ تبقى تطبيقاتك وبياناتك.", quit:"إغلاق لوحة الإدارة", cancel:"إلغاء", confirm:"تأكيد", close:"إغلاق", save:"حفظ",
pw_title:"تعيين كلمة مرور لوحة التحكم", pw_saved:"تم حفظ كلمة المرور", running_job:"جارٍ التنفيذ…", job_done:"تم", job_failed:"فشل", lang:"English",
err_need_admin:"يلزم تشغيل البرنامج كمسؤول.", err_busy:"إجراء آخر ما زال قيد التنفيذ.", err_weak_password:"يجب ألا تقل كلمة المرور عن 10 أحرف.", err_auth:"افتح لوحة الإدارة من البرنامج (الرابط الذي يفتحه يحتوي على سر)."
}};
const LS = { get(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
let lang = LS.get("cm.lang", "ar"), csrf = null, st = null, doc = null, docBusy = false, logName = "server", logText = "";
const root = document.documentElement;
root.dataset.theme = LS.get("cm.theme", matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
const t = k => (T[lang] && T[lang][k]) || T.en[k] || k;
const applyLang = () => { root.lang = lang; root.dir = lang === "ar" ? "rtl" : "ltr"; };
applyLang();

function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v; else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style") Object.assign(el.style, v); else if (v === true) el.setAttribute(k, ""); else el.setAttribute(k, v);
  }
  const add = k => { if (Array.isArray(k)) k.forEach(add); else if (k != null && k !== false) el.append(k instanceof Node ? k : document.createTextNode(String(k))); };
  kids.forEach(add); return el;
}
const btn = (label, cls, onclick, extra) => h("button", Object.assign({ class: "btn " + (cls || ""), type: "button", onclick }, extra), label);
const toast = (msg, bad) => { const el = h("div", { class: "toast" + (bad ? " bad" : "") }, msg); document.getElementById("toasts").append(el); setTimeout(() => el.remove(), 4500); };

async function api(path, body) {
  const init = { method: body === undefined ? "GET" : "POST", headers: {}, credentials: "same-origin" };
  if (csrf) init.headers["X-CSRF-Token"] = csrf;
  if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  const res = await fetch("/api/" + path, init);
  let out = {}; try { out = await res.json(); } catch (e) {}
  if (!res.ok) { const e = new Error(out.error || res.statusText); e.code = out.code; throw e; }
  return out;
}
const errText = e => (e.code && T[lang]["err_" + e.code]) || e.message;
const fail = e => toast(errText(e), true);

function modal(title, body, actions) {
  const dlg = h("dialog", {});
  dlg.append(h("div", { class: "mh" }, h("span", {}, title)), h("div", { class: "mb" }, body),
    h("div", { class: "mf" }, actions.map(a => btn(a.label, a.kind, async ev => { const b = ev.currentTarget; b.disabled = true; let keep = false; try { keep = (await a.onclick()) === false; } catch (e) { fail(e); keep = true; } if (keep) b.disabled = false; else dlg.close(); }))));
  dlg.addEventListener("close", () => dlg.remove()); document.body.append(dlg); dlg.showModal(); return dlg;
}
const confirmBox = (msg, label) => new Promise(res => { let ok = false; const d = modal(t("confirm"), h("p", { style: { margin: 0 } }, msg), [{ label: t("cancel"), onclick: () => true }, { label, kind: "danger", onclick: () => { ok = true; return true; } }]); d.addEventListener("close", () => res(ok)); });

function showJob(id, title) {
  const pre = h("pre", { class: "log" }, "…"), badge = h("span", { class: "badge" }, t("running_job"));
  const dlg = modal(title, h("div", {}, h("p", { style: { marginTop: 0 } }, badge), pre), [{ label: t("close"), onclick: () => true }]);
  let stop = false; dlg.addEventListener("close", () => { stop = true; doc = null; refresh(); });
  (async function poll() {
    if (stop) return;
    try {
      const { job } = await api("job?id=" + encodeURIComponent(id));
      pre.textContent = job.log.join("\n") || "…"; pre.scrollTop = pre.scrollHeight;
      badge.className = "badge " + (job.status === "done" ? "ok" : job.status === "failed" ? "bad" : ""); badge.textContent = job.status === "running" ? t("running_job") : t(job.status === "done" ? "job_done" : "job_failed");
      if (job.status === "running") setTimeout(poll, 700); else refresh();
    } catch (e) { pre.textContent = errText(e); }
  })();
}
async function action(name, title, extra) { try { const r = await api("action", Object.assign({ name }, extra)); showJob(r.job, title); } catch (e) { fail(e); } }

async function refresh() { try { st = await api("status"); } catch (e) { fail(e); } render(); }
async function runDoctor() { docBusy = true; render(); try { doc = await api("doctor"); } catch (e) { fail(e); } docBusy = false; render(); }
async function loadLog() { try { logText = (await api("log?name=" + logName)).text; } catch (e) { logText = errText(e); } render(); }

function passwordDialog() {
  const pw = h("input", { type: "password", autocomplete: "new-password" });
  modal(t("pw_title"), h("label", { class: "f" }, h("span", {}, t("pw_label")), pw), [{ label: t("cancel"), onclick: () => true }, { label: t("save"), kind: "primary", onclick: async () => { await api("password", { password: pw.value }); toast(t("pw_saved")); await refresh(); return true; } }]);
}
const FIXES = { install: () => document.getElementById("install-card") ? document.getElementById("install-card").scrollIntoView({ behavior: "smooth" }) : action("install", t("install_h")),
  start: () => action("start", t("start")), password: passwordDialog, update: () => doUpdate(), migrate: () => action("migrate", t("migrate")) };
async function doUpdate() { try { const r = await api("update", {}); showJob(r.job, t("upd_h")); } catch (e) { fail(e); } }

const dd = (k, v, cls) => [h("dt", {}, k), h("dd", { class: cls || "" }, v)];
function statusCard() {
  const state = st.running ? "ok" : st.installed ? "bad" : "warn", label = st.running ? "running" : st.installed ? "stopped" : "not_installed";
  const link = u => h("a", { href: u, target: "_blank", rel: "noopener", class: "ltr mono" }, u);
  return h("div", { class: "card" }, h("div", { class: "status" }, h("div", { class: "dot " + state }), h("div", {}, h("b", {}, t(label)), h("span", {}, t("st_" + label)))),
    h("dl", {}, dd(t("autostart"), st.installed ? t("yes") : t("no")), dd(t("watchdog"), st.supervisor ? t("yes") : t("no")),
      st.running ? [dd(t("apps_addr"), link(st.apps_url)), dd(t("dash_addr"), link(st.dashboard_url))] : null,
      dd(t("data_dir"), st.data_dir, "ltr mono"), dd(t("prog_dir"), st.program_dir, "ltr mono")),
    st.legacy && st.legacy.length ? h("div", { class: "note", style: { marginTop: "14px", marginBottom: 0 } }, h("span", {}, t("legacy")), btn(t("migrate"), "sm", () => action("migrate", t("migrate")))) : null);
}
function installCard() {
  const pw = h("input", { type: "password", id: "pw", autocomplete: "new-password" });
  return h("div", { class: "card", id: "install-card" }, h("h2", {}, t("install_h")),
    !st.password_set ? h("label", { class: "f" }, h("span", {}, t("pw_label")), pw) : null,
    btn(t("install_btn"), "primary big", () => action("install", t("install_h"), { password: pw.value || undefined })),
    h("ul", { class: "what" }, ["w1", "w2", "w3", "w4"].map(k => h("li", {}, t(k)))));
}
function controlCard() {
  return h("div", { class: "card" }, h("h2", {}, t("control")), h("div", { class: "row" },
    btn(t("start"), st.running ? "" : "primary", () => action("start", t("start")), { disabled: st.running ? true : null }),
    btn(t("restart"), "", () => action("restart", t("restart"))), btn(t("stop"), "", () => action("stop", t("stop")), { disabled: st.running ? null : true }),
    btn(t("open_dash"), "primary", () => api("open", { what: "dashboard" }).catch(fail), { disabled: st.running ? null : true }),
    btn(t("open_apps"), "", () => api("open", { what: "apps" }).catch(fail), { disabled: st.running ? null : true })));
}
function updateCard() {
  const u = st.update;
  let msg = null, act = null;
  if (st.staged) msg = h("span", { class: "badge warn" }, t("upd_staged") + " (" + st.staged + ")");
  else if (u && u.error) msg = h("span", { class: "badge" }, t("upd_offline"));
  else if (u && u.update) { msg = h("span", { class: "badge warn" }, t("update_to") + " " + u.latest); act = u.supported ? btn(t("update_to") + " " + u.latest, "primary", doUpdate) : h("span", { class: "hint" }, t("upd_unsupported")); }
  else if (u && u.latest) msg = h("span", { class: "badge ok" }, t("up_to_date"));
  return h("div", { class: "card" }, h("h2", {}, t("upd_h")), h("div", { style: { display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" } },
    h("span", { class: "ltr mono" }, t("version") + " " + st.version), msg, h("span", { style: { flex: 1 } }), btn(t("check_upd"), "sm", async () => { try { st.update = await api("update-check", {}); render(); } catch (e) { fail(e); } }), act),
    h("p", { class: "hint" }, t("upd_note")));
}
function healthCard() {
  const mark = { ok: "✓", warn: "!", fail: "✕", info: "•" };
  return h("div", { class: "card" }, h("h2", {}, h("span", { class: "grow" }, t("health_h")), btn(docBusy ? t("health_run") : t("health_btn"), "sm", runDoctor, { disabled: docBusy ? true : null })),
    docBusy ? h("span", { class: "spin" }) : null,
    doc ? h("ul", { class: "checks" }, doc.checks.map(c => h("li", {}, h("span", { class: "mark " + c.status }, mark[c.status]), h("div", { class: "t" }, h("b", {}, (lang === "ar" && T.ar["chk_" + c.id]) || c.title), h("span", { dir: "auto" }, c.detail)),
      c.action && FIXES[c.action] ? btn(t("fix_" + c.action), "sm", FIXES[c.action]) : null))) : null);
}
function logsCard() {
  const sel = h("select", { onchange: ev => { logName = ev.target.value; loadLog(); } }, ["server", "console", "audit"].map(n => h("option", { value: n, selected: n === logName ? true : null }, t("log_" + n))));
  return h("div", { class: "card" }, h("h2", {}, h("span", { class: "grow" }, t("logs_h")), btn(t("refresh"), "sm", loadLog)), sel, h("div", { style: { height: "10px" } }), h("pre", { class: "log" }, logText || "—"));
}
function render() {
  const app = document.getElementById("app"); app.textContent = "";
  document.title = t("title") + " — " + t("sub");
  const head = h("header", {}, h("img", { src: "/favicon.svg", alt: "" }), h("h1", {}, t("title"), h("small", {}, t("sub") + (st ? " · v" + st.version : ""))),
    btn(t("lang"), "sm", () => { lang = lang === "ar" ? "en" : "ar"; LS.set("cm.lang", lang); applyLang(); render(); }),
    btn(root.dataset.theme === "dark" ? "☀" : "☾", "sm", () => { root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark"; LS.set("cm.theme", root.dataset.theme); render(); }));
  if (!st) { app.append(h("div", { class: "wrap" }, head, h("span", { class: "spin" }))); return; }
  const parts = [head];
  if (!st.is_admin && st.platform !== "other") parts.push(h("div", { class: "note" }, h("span", {}, t("need_admin")),
    st.platform === "windows" ? btn(t("as_admin"), "sm", async () => { try { await api("elevate", {}); toast(t("closing")); } catch (e) { fail(e); } }) : null));
  parts.push(statusCard());
  if (!st.installed) parts.push(installCard());
  if (st.installed || st.running) parts.push(controlCard());
  parts.push(updateCard(), healthCard(), logsCard());
  parts.push(h("div", { class: "foot" }, st.installed ? btn(t("uninstall"), "sm danger", async () => { if (await confirmBox(t("uninstall_q"), t("uninstall"))) action("uninstall", t("uninstall")); }) : h("span"),
    btn(t("quit"), "sm", async () => { try { await api("quit", {}); } catch (e) {} document.body.textContent = ""; })));
  app.append(h("div", { class: "wrap" }, parts));
}
(async function init() {
  render();
  try { csrf = (await api("session")).csrf; } catch (e) { document.getElementById("app").append(h("div", { class: "wrap" }, h("div", { class: "note" }, h("span", {}, errText(e))))); return; }
  await refresh(); loadLog();
  setInterval(() => { const typing = document.activeElement && document.activeElement.tagName === "INPUT", pw = document.getElementById("pw"); if (!document.querySelector("dialog[open]") && !typing && !(pw && pw.value)) refresh(); }, 8000);
})();
})();
