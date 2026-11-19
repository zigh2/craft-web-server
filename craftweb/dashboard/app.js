"use strict";
(() => {
/* ------------------------------------------------------------ i18n */
const T = {
en: {
admin:"Admin console", nav_overview:"Overview", nav_apps:"Applications", nav_activity:"Activity", nav_settings:"Settings",
login_title:"Sign in", password:"Password", sign_in:"Sign in", sign_out:"Sign out",
setup_title:"Admin password is not set", setup_body:"Run this command on the server, then reload this page:",
err_bad_password:"Wrong password", err_locked:"Too many attempts. Please wait a few minutes.", err_session:"Session expired. Please sign in again.",
err_busy:"Another operation is running. Try again shortly.", err_forbidden:"Access from this network is not allowed.", err_csrf:"Security check failed. Reload the page.",
running:"Server running", apps:"Applications", disk_used:"Used by apps", disk_free:"free", uptime:"Uptime", version:"Version", refresh:"Refresh",
open:"Open", manage:"Manage", installed:"Installed", not_installed:"Not installed", active:"Active", check_updates:"Check for updates", check_all:"Check all",
checking:"Checking…", up_to_date:"Up to date", update_available:"Update available", not_live:"Not published", discovered:"Auto-discovered apps",
add_app:"Add application", edit:"Edit", remove:"Remove", back:"Back", all_apps:"All applications", no_apps:"No applications configured yet.",
versions:"Installed versions", status:"Status", actions:"Actions", activate:"Activate", delete:"Delete", no_versions:"No versions installed yet.",
activated:"Version activated", deleted:"Version deleted", installed_at:"Installed",
install_github:"Install from GitHub", load_releases:"Load releases", install_latest:"Install latest", install_selected:"Install selected release",
release:"Release", prerelease:"pre-release", installed_mark:"installed", no_repo:"No GitHub repository is configured for this app.", no_assets:"no matching file",
upload_zip:"Upload ZIP (offline install)", version_label:"Version label", choose_zip:"Drop a ZIP file here or click to choose", upload:"Upload & install", uploading:"Uploading…", uploaded:"Installed",
settings_app:"Configuration", f_id:"ID (used in the URL)", f_title:"Title", f_desc:"Description", f_icon:"Icon (emoji)", f_prefix:"Folder prefix", f_repo:"GitHub repository (owner/name)",
f_pattern:"Release file pattern (regex)", f_index:"Entry file", f_enabled:"Enabled", f_pre:"Include pre-releases", f_coi:"Cross-origin isolation (COOP/COEP)",
save:"Save", cancel:"Cancel", close:"Close", confirm:"Confirm", saved:"Saved",
remove_confirm:"Remove this application from the server?", purge:"Also delete all installed versions", delete_confirm:"Delete this version permanently?",
jobs:"Operations", audit:"Audit log", time:"Time", action:"Action", detail:"Details", no_jobs:"No operations yet.", done:"Done", failed:"Failed", log:"Log", ip:"IP",
server:"Server", python:"Python", host:"Listening on", security:"Security", tls_on:"HTTPS is enabled", tls_off:"HTTPS is off: the admin password travels unencrypted on this network. Set tls_cert and tls_key in apps.json.",
networks:"Allowed admin networks", session_idle:"Session idle timeout", min:"min", max_upload:"Max upload", change_password:"Change password", current_pw:"Current password", new_pw:"New password (min 10 characters)", pw_changed:"Password changed",
inbox:"Inbox folder", inbox_hint:"Copy <folder_prefix><version>.zip files here and they are installed automatically.", pending:"Waiting", failed_files:"Failed files", loading:"Loading…", lang_name:"العربية", theme:"Toggle theme",
import_files:"Import downloaded files", import_title:"Import files you already downloaded", import_hint:"Pick the ZIP files (several at once). They are matched to your apps by name, installed without downloading anything, and kept in the local cache.",
col_file:"File", col_app:"Application", col_version:"Version", import_start:"Import", import_done:"Done", import_skip:"skipped", import_pick:"Choose ZIP files", pick_app:"— choose —",
cache_title:"Saved downloads (cache)", cache_hint:"Every ZIP you download, upload or import is kept here, so any version can be reinstalled without internet.", cache_empty:"Nothing saved yet.", install_cached:"Install", cached_n:"cached",
f_auto:"Install updates automatically", last_checked:"Checked", update_now:"Update", onboard_title:"Already downloaded the app files?", onboard_body:"Import them now: nothing is downloaded again.",
auto_every:"Update check every", hours:"h", admin_port:"Dashboard port", cache_keep:"ZIPs kept per app", off:"off", saved_dl:"Saved downloads"
},
ar: {
admin:"لوحة التحكم", nav_overview:"نظرة عامة", nav_apps:"التطبيقات", nav_activity:"النشاط", nav_settings:"الإعدادات",
login_title:"تسجيل الدخول", password:"كلمة المرور", sign_in:"دخول", sign_out:"خروج",
setup_title:"لم يتم تعيين كلمة مرور المدير", setup_body:"نفّذ هذا الأمر على الخادم ثم أعد تحميل الصفحة:",
err_bad_password:"كلمة المرور غير صحيحة", err_locked:"محاولات كثيرة. انتظر بضع دقائق.", err_session:"انتهت الجلسة. سجّل الدخول من جديد.",
err_busy:"عملية أخرى قيد التنفيذ. حاول بعد قليل.", err_forbidden:"الدخول من هذه الشبكة غير مسموح.", err_csrf:"فشل الفحص الأمني. أعد تحميل الصفحة.",
running:"الخادم يعمل", apps:"التطبيقات", disk_used:"مساحة التطبيقات", disk_free:"متاحة", uptime:"مدة التشغيل", version:"الإصدار", refresh:"تحديث",
open:"فتح", manage:"إدارة", installed:"مثبّت", not_installed:"غير مثبّت", active:"فعّال", check_updates:"فحص التحديثات", check_all:"فحص الكل",
checking:"جارٍ الفحص…", up_to_date:"محدّث", update_available:"يوجد تحديث", not_live:"غير منشور", discovered:"تطبيقات مكتشفة تلقائياً",
add_app:"إضافة تطبيق", edit:"تعديل", remove:"إزالة", back:"رجوع", all_apps:"كل التطبيقات", no_apps:"لا توجد تطبيقات مضافة بعد.",
versions:"النسخ المثبّتة", status:"الحالة", actions:"إجراءات", activate:"تفعيل", delete:"حذف", no_versions:"لا توجد نسخ مثبّتة بعد.",
activated:"تم تفعيل النسخة", deleted:"تم حذف النسخة", installed_at:"وقت التثبيت",
install_github:"التثبيت من GitHub", load_releases:"تحميل الإصدارات", install_latest:"تثبيت الأحدث", install_selected:"تثبيت الإصدار المحدد",
release:"الإصدار", prerelease:"تجريبي", installed_mark:"مثبّت", no_repo:"لا يوجد مستودع GitHub لهذا التطبيق.", no_assets:"لا يوجد ملف مطابق",
upload_zip:"رفع ملف ZIP (تثبيت بدون إنترنت)", version_label:"رقم النسخة", choose_zip:"اسحب ملف ZIP هنا أو انقر للاختيار", upload:"رفع وتثبيت", uploading:"جارٍ الرفع…", uploaded:"تم التثبيت",
settings_app:"الإعدادات", f_id:"المعرّف (يظهر في الرابط)", f_title:"العنوان", f_desc:"الوصف", f_icon:"الأيقونة (إيموجي)", f_prefix:"بادئة المجلد", f_repo:"مستودع GitHub‏ (owner/name)",
f_pattern:"نمط ملف الإصدار (regex)", f_index:"ملف البداية", f_enabled:"مفعّل", f_pre:"تضمين الإصدارات التجريبية", f_coi:"عزل المصدر (COOP/COEP)",
save:"حفظ", cancel:"إلغاء", close:"إغلاق", confirm:"تأكيد", saved:"تم الحفظ",
remove_confirm:"إزالة هذا التطبيق من الخادم؟", purge:"حذف كل النسخ المثبّتة أيضاً", delete_confirm:"حذف هذه النسخة نهائياً؟",
jobs:"العمليات", audit:"سجل التدقيق", time:"الوقت", action:"الإجراء", detail:"التفاصيل", no_jobs:"لا توجد عمليات بعد.", done:"اكتملت", failed:"فشلت", log:"السجل", ip:"العنوان",
server:"الخادم", python:"بايثون", host:"يعمل على", security:"الأمان", tls_on:"HTTPS مفعّل", tls_off:"HTTPS متوقف: كلمة المرور تنتقل بدون تشفير داخل الشبكة. فعّل tls_cert وtls_key في apps.json.",
networks:"الشبكات المسموح لها بالدخول", session_idle:"مهلة الخمول", min:"دقيقة", max_upload:"أقصى حجم رفع", change_password:"تغيير كلمة المرور", current_pw:"كلمة المرور الحالية", new_pw:"كلمة المرور الجديدة (10 أحرف فأكثر)", pw_changed:"تم تغيير كلمة المرور",
inbox:"مجلد الاستلام", inbox_hint:"انسخ ملفات <البادئة><الإصدار>.zip هنا ليتم تثبيتها تلقائياً.", pending:"بالانتظار", failed_files:"ملفات فاشلة", loading:"جارٍ التحميل…", lang_name:"English", theme:"تبديل المظهر",
import_files:"استيراد ملفات منزّلة", import_title:"استيراد ملفات نزّلتها سابقاً", import_hint:"اختر ملفات ZIP (عدة ملفات معاً). تُطابَق مع تطبيقاتك بالاسم وتُثبَّت بدون تنزيل أي شيء، وتُحفظ في الكاش المحلي.",
col_file:"الملف", col_app:"التطبيق", col_version:"النسخة", import_start:"استيراد", import_done:"تم", import_skip:"متجاوَز", import_pick:"اختر ملفات ZIP", pick_app:"— اختر —",
cache_title:"التنزيلات المحفوظة (الكاش)", cache_hint:"كل ملف ZIP تنزّله أو ترفعه أو تستورده يُحفظ هنا، فيمكن إعادة تثبيت أي نسخة بدون إنترنت.", cache_empty:"لا توجد ملفات محفوظة.", install_cached:"تثبيت", cached_n:"محفوظ",
f_auto:"تثبيت التحديثات تلقائياً", last_checked:"آخر فحص", update_now:"تحديث", onboard_title:"هل نزّلت ملفات التطبيقات سابقاً؟", onboard_body:"استوردها الآن: لن يُعاد تنزيل شيء.",
auto_every:"فحص التحديثات كل", hours:"ساعة", admin_port:"منفذ اللوحة", cache_keep:"عدد ملفات ZIP المحفوظة لكل تطبيق", off:"متوقف", saved_dl:"التنزيلات المحفوظة"
}};

const LS = { get(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
let lang = LS.get("cw.lang", "ar");
const t = k => (T[lang] && T[lang][k]) || T.en[k] || k;

/* ------------------------------------------------------------ icons (static, trusted strings) */
const IC = {
  grid:"M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z", box:"M21 8l-9-5-9 5v8l9 5 9-5zM3.3 7.5 12 12.5l8.7-5M12 22V12.5",
  activity:"M22 12h-4l-3 9L9 3l-3 9H2", sliders:"M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
  sun:"M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon:"M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z", logout:"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  upload:"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12", download:"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  refresh:"M23 4v6h-6M1 20v-6h6M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15", ext:"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3",
  trash:"M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6", check:"M20 6 9 17l-5-5", plus:"M12 5v14M5 12h14",
  edit:"M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z", x:"M18 6 6 18M6 6l12 12", undo:"M1 4v6h6M3.5 15a9 9 0 1 0 2.1-9.4L1 10", back:"M19 12H5M12 19l-7-7 7-7",
};
const ic = n => { const s = document.createElement("span"); s.className = "ic"; s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + IC[n] + '"/></svg>'; return s; };

/* ------------------------------------------------------------ DOM helper (text only: never innerHTML with data) */
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style") Object.assign(el.style, v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  const add = k => { if (Array.isArray(k)) k.forEach(add); else if (k != null && k !== false) el.append(k instanceof Node ? k : document.createTextNode(String(k))); };
  kids.forEach(add);
  return el;
}
const btn = (label, cls, onclick, icon, extra) => h("button", Object.assign({ class: "btn " + (cls || ""), type: "button", onclick }, extra), icon ? ic(icon) : null, label);
const fmtBytes = n => { if (!n) return "0 B"; const u = ["B","KB","MB","GB","TB"]; const i = Math.min(4, Math.floor(Math.log(n) / Math.log(1024))); return (n / Math.pow(1024, i)).toFixed(i ? 1 : 0) + " " + u[i]; };
const fmtTime = x => { if (!x) return "—"; const d = typeof x === "number" ? new Date(x * 1000) : new Date(x); return d.toLocaleString(lang === "ar" ? "ar" : "en", { dateStyle: "medium", timeStyle: "short" }); };
const fmtUp = s => { const d = Math.floor(s / 86400), hh = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return (d ? d + "d " : "") + (hh ? hh + "h " : "") + m + "m"; };

function toast(msg, bad) { const el = h("div", { class: "toast" + (bad ? " bad" : "") }, msg); document.getElementById("toasts").append(el); setTimeout(() => el.remove(), 4200); }

/* ------------------------------------------------------------ API */
let csrf = null, session = null, authed = false, data = null, checks = {}, releases = {};
async function api(path, body, method) {
  const init = { method: method || (body !== undefined ? "POST" : "GET"), headers: {}, credentials: "same-origin" };
  if (csrf) init.headers["X-CSRF-Token"] = csrf;
  if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  let res;
  try { res = await fetch("/admin/api/" + path, init); } catch (e) { throw new Error("Network error"); }
  let out = {}; try { out = await res.json(); } catch (e) {}
  if (!res.ok) {
    if (res.status === 401 && path !== "login") { authed = false; csrf = null; render(); }
    const err = new Error(out.error || res.statusText); err.code = out.code; throw err;
  }
  return out;
}
const errText = e => (e.code && T[lang]["err_" + e.code]) || e.message;
const fail = e => toast(errText(e), true);
function upload(file, app, version, onProgress, mode) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open("POST", "/admin/api/upload");
    x.setRequestHeader("X-CSRF-Token", csrf); x.setRequestHeader("X-App", app); x.setRequestHeader("X-Version", version);
    x.setRequestHeader("Content-Type", "application/zip"); x.setRequestHeader("X-Filename", encodeURIComponent(file.name)); if (mode) x.setRequestHeader("X-Mode", mode);
    x.upload.onprogress = e => e.lengthComputable && onProgress(e.loaded / e.total);
    x.onload = () => { let d = {}; try { d = JSON.parse(x.responseText); } catch (e) {} if (x.status < 300) resolve(d); else { const er = new Error(d.error || x.statusText); er.code = d.code; reject(er); } };
    x.onerror = () => reject(new Error("Network error"));
    x.send(file);
  });
}

/* ------------------------------------------------------------ modal */
function modal(title, body, actions, wide) {
  const dlg = h("dialog", { class: "modal" + (wide ? " wide" : "") });
  const close = () => { dlg.close(); };
  dlg.append(h("div", { class: "mh" }, h("h2", {}, title), h("button", { class: "btn ghost icon", type: "button", "aria-label": t("close"), onclick: close }, ic("x"))),
    h("div", { class: "mb" }, body),
    h("div", { class: "mf" }, (actions || [{ label: t("close"), onclick: () => true }]).map(a =>
      btn(a.label, a.kind, async ev => { const b = ev.currentTarget; b.disabled = true; let keep = false; try { keep = (await a.onclick()) === false; } catch (e) { fail(e); keep = true; } if (keep) b.disabled = false; else close(); }))));
  dlg.addEventListener("close", () => dlg.remove());
  document.body.append(dlg); dlg.showModal();
  return { close, el: dlg };
}
const confirmBox = (msg, label, extra) => new Promise(res => { let done = false;
  const m = modal(t("confirm"), h("div", {}, h("p", { style: { marginTop: 0 } }, msg), extra || null),
    [{ label: t("cancel"), onclick: () => { res(false); return true; } }, { label, kind: "danger", onclick: () => { done = true; res(true); return true; } }]);
  m.el.addEventListener("close", () => { if (!done) res(false); }); });

function showJob(id, title) {
  const pre = h("pre", { class: "log" }, "…"), badge = h("span", { class: "badge acc" }, t("running"));
  const m = modal(title, h("div", {}, h("p", { style: { marginTop: 0 } }, badge), pre), null, true);
  let stop = false;
  m.el.addEventListener("close", () => { stop = true; reload(); });
  (async function poll() {
    if (stop) return;
    try {
      const { job } = await api("job?id=" + encodeURIComponent(id));
      pre.textContent = job.log.join("\n") || "…"; pre.scrollTop = pre.scrollHeight;
      badge.className = "badge " + (job.status === "done" ? "ok" : job.status === "failed" ? "bad" : "acc");
      badge.textContent = t(job.status);
      if (job.status === "running") setTimeout(poll, 800);
    } catch (e) { pre.textContent = errText(e); }
  })();
}

/* ------------------------------------------------------------ data + routing */
async function reload() { try { data = await api("overview"); } catch (e) { if (authed) fail(e); } render(); }
const route = () => { const p = location.hash.replace(/^#\/?/, "").split("/"); return { page: p[0] || "overview", id: p[1] ? decodeURIComponent(p[1]) : null }; };
window.addEventListener("hashchange", () => { document.querySelectorAll("dialog[open]").forEach(d => d.close()); render(); if (route().page === "activity") loadActivity(); });
const setLang = l => { lang = l; LS.set("cw.lang", l); document.documentElement.lang = l; document.documentElement.dir = l === "ar" ? "rtl" : "ltr"; render(); };
const toggleTheme = () => { const n = document.documentElement.dataset.theme === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = n; LS.set("cw.theme", n); render(); };

/* ------------------------------------------------------------ login */
function loginView() {
  const err = h("div", { class: "err" }), pw = h("input", { type: "password", autocomplete: "current-password", autofocus: true, required: true });
  const submit = async ev => {
    ev.preventDefault(); err.textContent = "";
    try { const r = await api("login", { password: pw.value }); csrf = r.csrf; authed = true; pw.value = ""; await reload(); }
    catch (e) { err.textContent = errText(e); pw.select(); }
  };
  const card = session && session.setup_required
    ? h("div", {}, h("h2", { style: { marginBottom: "6px" } }, t("setup_title")), h("p", { class: "muted" }, t("setup_body")), h("code", { class: "cmd" }, "python server.py --set-admin-password"))
    : h("form", { onsubmit: submit }, h("label", { class: "f" }, h("span", {}, t("password")), pw), err, h("button", { class: "btn primary", style: { width: "100%", justifyContent: "center" }, type: "submit" }, t("sign_in")));
  return h("div", { class: "login" }, h("div", { class: "card" },
    h("div", { class: "logo" }, h("img", { src: "/admin/static/favicon.svg", alt: "" }), h("h1", {}, "Craft Apps"), h("span", { class: "muted" }, t("admin") + (session && session.version ? " · v" + session.version : ""))),
    card, h("div", { class: "tools" }, btn(t("lang_name"), "ghost sm", () => setLang(lang === "ar" ? "en" : "ar")), btn("", "ghost sm icon", toggleTheme, document.documentElement.dataset.theme === "dark" ? "sun" : "moon", { title: t("theme") }))));
}

/* ------------------------------------------------------------ shell */
function shell(title, content) {
  const r = route();
  const nav = [["overview", "grid", "nav_overview"], ["apps", "box", "nav_apps"], ["activity", "activity", "nav_activity"], ["settings", "sliders", "nav_settings"]];
  return h("div", { class: "shell" },
    h("aside", { class: "side" },
      h("div", { class: "brand" }, h("img", { src: "/admin/static/favicon.svg", alt: "" }), h("div", {}, h("b", {}, data ? data.server.name : "Craft Apps"), h("small", {}, t("admin")))),
      h("nav", { class: "nav" }, nav.map(([p, i, k]) => h("a", { href: "#/" + p, class: r.page === p ? "on" : "" }, ic(i), h("span", { class: "t" }, t(k))))),
      h("div", { class: "grow" }), h("small", { class: "ltr", style: { padding: "0 10px" } }, data ? "v" + data.server.version : "")),
    h("div", { class: "main" },
      h("header", { class: "top" }, h("h1", {}, title), h("span", { class: "pill" }, t("running")),
        btn("", "ghost icon", reload, "refresh", { title: t("refresh") }), btn("", "ghost icon", toggleTheme, document.documentElement.dataset.theme === "dark" ? "sun" : "moon", { title: t("theme") }),
        btn(t("lang_name"), "ghost sm", () => setLang(lang === "ar" ? "en" : "ar")),
        btn(t("sign_out"), "sm", async () => { try { await api("logout", {}); } catch (e) {} authed = false; csrf = null; data = null; render(); }, "logout")),
      h("main", { class: "content" }, content)));
}

/* ------------------------------------------------------------ overview */
const stat = (k, v, s, bar) => h("div", { class: "card stat" }, h("div", { class: "k" }, k), h("div", { class: "v" }, v), s ? h("div", { class: "s" }, s) : null, bar != null ? h("div", { class: "bar" }, h("i", { style: { width: Math.max(2, bar) + "%" } })) : null);

async function checkApp(a) {
  checks[a.id] = { s: "loading" }; render();
  try { a.latest = await api("check", { app: a.id }); } catch (e) { fail(e); }
  delete checks[a.id]; render();
}
function updateBadge(a) {
  if (checks[a.id]) return h("span", { class: "badge" }, h("span", { class: "spin" }), t("checking"));
  const L = a.latest; if (!L) return null;
  if (L.error) return h("span", { class: "badge bad", title: L.error }, "!");
  if (L.tag && L.update) return h("span", { class: "badge warn ltr", title: t("last_checked") + ": " + fmtTime(L.checked) }, t("update_available") + ": " + L.tag);
  if (L.tag) return h("span", { class: "badge ok", title: t("last_checked") + ": " + fmtTime(L.checked) }, ic("check"), t("up_to_date"));
  return null;
}
const installTag = async (a, tag) => { try { const r = await api("install", { app: a.id, tag: tag || "" }); showJob(r.job, t("install_github") + ": " + a.title); } catch (e) { fail(e); } };
function appCard(a) {
  return h("div", { class: "card app" },
    h("div", { class: "row" }, h("div", { class: "bubble" }, a.icon || "🌐"), h("div", { style: { minWidth: 0, flex: 1 } }, h("h3", {}, a.title), h("span", { class: "muted ltr", style: { fontSize: "12px" } }, "/" + a.id + "/"))),
    h("p", {}, a.description),
    h("div", { class: "row", style: { flexWrap: "wrap", gap: "8px" } },
      a.active ? h("span", { class: "badge ok ltr" }, ic("check"), a.active) : h("span", { class: "badge warn" }, t("not_installed")),
      !a.enabled ? h("span", { class: "badge" }, "off") : null, updateBadge(a)),
    h("div", { class: "acts" },
      a.live ? h("a", { class: "btn sm", href: "/" + encodeURIComponent(a.id) + "/", target: "_blank", rel: "noopener" }, ic("ext"), t("open")) : null,
      btn(t("manage"), "sm primary", () => { location.hash = "#/apps/" + encodeURIComponent(a.id); }, "sliders"),
      a.latest && a.latest.update && a.latest.tag ? btn(t("update_now"), "sm primary", () => installTag(a, a.latest.tag), "download") : null,
      a.repo ? btn(t("check_updates"), "sm", () => checkApp(a), "refresh") : null));
}
function overviewPage() {
  const s = data.server, total = s.disk_total || 1, usedPct = Math.min(100, (s.apps_bytes / total) * 100 + 0);
  const apps = data.apps;
  return h("div", {},
    h("div", { class: "stats" },
      stat(t("apps"), apps.filter(a => a.active).length + " / " + apps.length, t("installed")),
      stat(t("disk_used"), fmtBytes(s.apps_bytes), fmtBytes(s.disk_free) + " " + t("disk_free") + " · " + t("saved_dl") + ": " + fmtBytes(apps.reduce((n, a) => n + a.cache.reduce((m, c) => m + c.size, 0), 0)), usedPct),
      stat(t("uptime"), fmtUp(s.uptime), s.tls ? "HTTPS" : "HTTP"),
      stat(t("version"), "v" + s.version, "Python " + s.python)),
    h("div", { class: "sec" }, h("h2", {}, t("apps")), btn(t("check_all"), "sm", () => data.apps.filter(a => a.repo).forEach(checkApp), "refresh"), btn(t("import_files"), "sm", importDialog, "upload"), btn(t("add_app"), "sm primary", () => appForm(null), "plus")),
    apps.length && !apps.some(a => a.active) ? h("div", { class: "note ok", style: { display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" } }, h("div", { style: { flex: 1 } }, h("b", {}, t("onboard_title")), h("div", {}, t("onboard_body"))), btn(t("import_files"), "primary", importDialog, "upload")) : null,
    apps.length ? h("div", { class: "grid" }, apps.map(appCard)) : h("div", { class: "card empty" }, t("no_apps")),
    data.discovered.length ? h("div", { class: "card", style: { marginBottom: "24px" } }, h("div", { class: "hd" }, h("h2", {}, t("discovered"))), h("div", { class: "bd" }, data.discovered.map(d => h("span", { class: "badge acc ltr", style: { marginInlineEnd: "8px" } }, d.id + " · " + d.version)))) : null,
    inboxCard());
}
function inboxCard() {
  const i = data.inbox; if (!data.server.inbox_enabled || (!i.pending.length && !i.failed.length)) return null;
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("inbox"))), h("div", { class: "bd" },
    i.pending.map(f => h("div", {}, h("span", { class: "badge warn" }, t("pending")), " ", h("span", { class: "ltr mono" }, f))),
    i.failed.map(f => h("div", {}, h("span", { class: "badge bad" }, t("failed")), " ", h("span", { class: "ltr mono" }, f)))));
}

/* ------------------------------------------------------------ apps */
function appsListPage() {
  return h("div", {}, h("div", { class: "sec" }, h("h2", {}, t("all_apps")), btn(t("import_files"), "sm", importDialog, "upload"), btn(t("add_app"), "sm primary", () => appForm(null), "plus")),
    data.apps.length ? h("div", { class: "card tw" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, t("nav_apps")), h("th", {}, t("version")), h("th", {}, "GitHub"), h("th", {}))),
      h("tbody", {}, data.apps.map(a => h("tr", {}, h("td", {}, h("b", {}, (a.icon ? a.icon + " " : "") + a.title), h("div", { class: "muted ltr", style: { fontSize: "12px" } }, "/" + a.id + "/")),
        h("td", {}, a.active ? h("span", { class: "badge ok ltr" }, a.active) : h("span", { class: "badge warn" }, t("not_installed"))),
        h("td", { class: "ltr muted" }, a.repo || "—"), h("td", { class: "r" }, btn(t("manage"), "sm", () => { location.hash = "#/apps/" + encodeURIComponent(a.id); }, "sliders"))))))) : h("div", { class: "card empty" }, t("no_apps")));
}
function appForm(a) {
  const v = a || { enabled: true, asset_pattern: ".*\\.zip$", index_path: "index.html" }, f = {};
  const field = (key, label, o) => { o = o || {}; f[key] = h("input", { type: "text", value: v[key] || "", disabled: o.disabled, dir: o.ltr ? "ltr" : null, placeholder: o.ph }); return h("label", { class: "f" }, h("span", {}, label), f[key]); };
  const chk = (key, label) => { f[key] = h("input", { type: "checkbox", checked: v[key] ? true : null }); return h("label", { class: "chk" }, f[key], label); };
  const body = h("div", {}, field("id", t("f_id"), { disabled: !!a, ltr: true }), field("title", t("f_title")), field("description", t("f_desc")), field("icon", t("f_icon")),
    field("repo", t("f_repo"), { ltr: true, ph: "owner/name" }), field("folder_prefix", t("f_prefix"), { ltr: true, disabled: !!(a && a.versions.length), ph: "myapp-web-" }),
    field("asset_pattern", t("f_pattern"), { ltr: true }), field("index_path", t("f_index"), { ltr: true }), chk("enabled", t("f_enabled")), chk("prerelease", t("f_pre")), chk("auto_update", t("f_auto")), chk("cross_origin_isolation", t("f_coi")));
  modal(a ? t("edit") + ": " + a.title : t("add_app"), body, [{ label: t("cancel"), onclick: () => true }, { label: t("save"), kind: "primary", onclick: async () => {
    const app = {}; for (const k of Object.keys(f)) app[k] = f[k].type === "checkbox" ? f[k].checked : f[k].value;
    if (!app.folder_prefix) delete app.folder_prefix;
    await api("app", { app, original_id: a ? a.id : null }); toast(t("saved")); await reload(); if (!a) location.hash = "#/apps/" + encodeURIComponent(app.id); return true; } }]);
}
function versionsCard(a) {
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("versions"))),
    a.versions.length ? h("div", { class: "tw" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, t("version")), h("th", {}, t("status")), h("th", {}))),
      h("tbody", {}, a.versions.map(x => h("tr", {}, h("td", { class: "ltr mono" }, x.tag), h("td", {}, x.active ? h("span", { class: "badge ok" }, ic("check"), t("active")) : h("span", { class: "badge" }, t("installed"))),
        h("td", { class: "r" }, x.active ? (a.installed_at ? h("span", { class: "muted" }, fmtTime(a.installed_at)) : null) : [
          btn(t("activate"), "sm", async () => { try { await api("activate", { app: a.id, tag: x.tag }); toast(t("activated")); reload(); } catch (e) { fail(e); } }, "undo"),
          btn(t("delete"), "sm danger", async () => { if (await confirmBox(t("delete_confirm") + " " + x.tag, t("delete"))) { try { await api("delete-version", { app: a.id, tag: x.tag }); toast(t("deleted")); reload(); } catch (e) { fail(e); } } }, "trash")]))))))
      : h("div", { class: "empty" }, t("no_versions")));
}
function githubCard(a) {
  if (!a.repo) return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("install_github"))), h("div", { class: "empty" }, t("no_repo")));
  const sel = h("select", { dir: "ltr" }), list = releases[a.id];
  const install = tag => installTag(a, tag);
  if (list) list.forEach(r => sel.append(h("option", { value: r.tag, disabled: r.assets.length ? null : true }, r.tag + (r.prerelease ? " (" + t("prerelease") + ")" : "") + (r.installed ? " ✓" : "") + (r.assets.length ? "" : " — " + t("no_assets")))));
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("install_github")), h("span", { class: "muted ltr" }, a.repo)),
    h("div", { class: "bd" }, h("div", { class: "inline" },
      list ? h("label", { class: "f", style: { margin: 0 } }, h("span", {}, t("release")), sel) : null,
      !list ? btn(t("load_releases"), "", async ev => { ev.currentTarget.disabled = true; try { releases[a.id] = (await api("releases?app=" + encodeURIComponent(a.id))).releases; } catch (e) { fail(e); } render(); }, "refresh") : btn(t("install_selected"), "", () => install(sel.value), "download"),
      btn(t("install_latest"), "primary", () => install(""), "download"))));
}
function uploadCard(a) {
  let file = null;
  const ver = h("input", { type: "text", dir: "ltr", placeholder: "v1.2.0" }), name = h("div", { class: "ltr mono" }), bar = h("i", { style: { width: "0%" } }), barBox = h("div", { class: "bar", hidden: true }, bar);
  const pick = f => { if (!f) return; file = f; name.textContent = f.name + " (" + fmtBytes(f.size) + ")"; if (!ver.value) ver.value = f.name.replace(/\.zip$/i, "").replace(new RegExp("^" + a.folder_prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"), ""); };
  const input = h("input", { type: "file", accept: ".zip,application/zip", onchange: ev => pick(ev.target.files[0]) });
  const drop = h("label", { class: "drop", ondragover: ev => { ev.preventDefault(); drop.classList.add("over"); }, ondragleave: () => drop.classList.remove("over"), ondrop: ev => { ev.preventDefault(); drop.classList.remove("over"); pick(ev.dataTransfer.files[0]); } }, ic("upload"), h("div", {}, h("b", {}, t("choose_zip"))), name, input);
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("upload_zip"))), h("div", { class: "bd" }, drop, h("div", { style: { height: "14px" } }),
    h("div", { class: "inline" }, h("label", { class: "f", style: { margin: 0 } }, h("span", {}, t("version_label")), ver),
      btn(t("upload"), "primary", async ev => {
        if (!file || !ver.value.trim()) return; const b = ev.currentTarget; b.disabled = true; barBox.hidden = false;
        try { await upload(file, a.id, ver.value.trim(), p => { bar.style.width = Math.round(p * 100) + "%"; }); toast(t("uploaded")); await reload(); } catch (e) { fail(e); b.disabled = false; barBox.hidden = true; }
      }, "upload")), barBox));
}
function cacheCard(a) {
  const total = a.cache.reduce((n, c) => n + c.size, 0);
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("cache_title")), h("span", { class: "muted" }, a.cache.length + " · " + fmtBytes(total))),
    h("div", { class: "bd", style: { paddingBottom: a.cache.length ? "0" : "" } }, h("p", { class: "hint", style: { margin: 0 } }, t("cache_hint"))),
    a.cache.length ? h("div", { class: "tw", style: { marginTop: "14px" } }, h("table", {}, h("tbody", {}, a.cache.map(c => h("tr", {},
      h("td", { class: "ltr mono" }, c.tag), h("td", { class: "muted" }, fmtBytes(c.size)), h("td", { class: "muted" }, fmtTime(c.mtime)),
      h("td", { class: "r" }, a.versions.some(v => v.tag === c.tag) ? h("span", { class: "badge ok" }, t("installed")) : btn(t("install_cached"), "sm", async () => { try { const r = await api("cache-install", { app: a.id, name: c.name }); showJob(r.job, t("install_cached") + ": " + c.tag); } catch (e) { fail(e); } }, "download"),
        btn("", "sm danger icon", async () => { if (await confirmBox(t("delete_confirm") + " " + c.tag, t("delete"))) { try { await api("cache-delete", { app: a.id, name: c.name }); reload(); } catch (e) { fail(e); } } }, "trash"))))))) : h("div", { class: "empty" }, t("cache_empty")));
}
function importDialog() {
  const rows = [], list = h("div", { class: "tw" }), input = h("input", { type: "file", accept: ".zip,application/zip", multiple: true });
  const body = h("div", {}, h("p", { style: { marginTop: 0 } }, t("import_hint")), h("label", { class: "drop" }, ic("upload"), h("div", {}, h("b", {}, t("import_pick"))), input), list);
  const appSel = () => { const sel = h("select", {}, h("option", { value: "" }, t("pick_app")), data.apps.map(x => h("option", { value: x.id }, x.title))); return sel; };
  input.addEventListener("change", async () => {
    const files = Array.from(input.files); rows.length = 0; list.textContent = "";
    let m = []; try { m = (await api("match", { names: files.map(f => f.name) })).matches; } catch (e) { fail(e); }
    const table = h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, t("col_file")), h("th", {}, t("col_app")), h("th", {}, t("col_version")), h("th", {}))), h("tbody", {}));
    files.forEach((f, i) => {
      const sel = appSel(), ver = h("input", { type: "text", dir: "ltr" }), st = h("td", { class: "muted" });
      sel.value = (m[i] && m[i].app) || ""; ver.value = (m[i] && m[i].tag) || "";
      rows.push({ f, sel, ver, st });
      table.lastChild.append(h("tr", {}, h("td", { class: "ltr mono", style: { wordBreak: "break-all" } }, f.name + " (" + fmtBytes(f.size) + ")"), h("td", {}, sel), h("td", {}, ver), st));
    });
    list.append(table);
  });
  modal(t("import_title"), body, [{ label: t("close"), onclick: () => { reload(); return true; } }, { label: t("import_start"), kind: "primary", onclick: async () => {
    for (const r of rows) {
      if (!r.sel.value || !r.ver.value.trim()) { r.st.textContent = t("import_skip"); continue; }
      r.st.textContent = "0%";
      try { await upload(r.f, r.sel.value, r.ver.value.trim(), p => { r.st.textContent = Math.round(p * 100) + "%"; }, "import"); r.st.textContent = "✓ " + t("import_done"); }
      catch (e) { r.st.textContent = errText(e); }
    }
    return false; } }], true);
}
function appDetailPage(a) {
  const c = checks[a.id];
  return h("div", {}, h("a", { class: "back", href: "#/apps" }, h("span", { class: "flip" }, ic("back")), t("nav_apps")),
    h("div", { class: "card", style: { marginBottom: "18px" } }, h("div", { class: "bd" }, h("div", { class: "row", style: { display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" } },
      h("div", { class: "bubble" }, a.icon || "🌐"), h("div", { style: { flex: 1, minWidth: "180px" } }, h("h2", {}, a.title), h("div", { class: "muted" }, a.description || "—")),
      a.active ? h("span", { class: "badge ok ltr" }, ic("check"), a.active) : h("span", { class: "badge warn" }, t("not_installed")), updateBadge(a),
      a.live ? h("a", { class: "btn sm", href: "/" + encodeURIComponent(a.id) + "/", target: "_blank", rel: "noopener" }, ic("ext"), t("open")) : null,
      a.repo ? btn(t("check_updates"), "sm", () => checkApp(a), "refresh") : null,
      btn(t("edit"), "sm", () => appForm(a), "edit"),
      btn(t("remove"), "sm danger", async () => {
        const purge = h("input", { type: "checkbox" });
        if (await confirmBox(t("remove_confirm"), t("remove"), h("label", { class: "chk" }, purge, t("purge")))) { try { await api("app-delete", { id: a.id, purge: purge.checked }); location.hash = "#/apps"; await reload(); } catch (e) { fail(e); } }
      }, "trash")))),
    h("div", { class: "stack" }, versionsCard(a), h("div", { class: "two" }, githubCard(a), uploadCard(a)), cacheCard(a)));
}

/* ------------------------------------------------------------ activity */
let activity = { jobs: [], audit: [] };
async function loadActivity() { try { const [j, a] = await Promise.all([api("jobs"), api("audit")]); activity = { jobs: j.jobs, audit: a.entries }; } catch (e) { fail(e); } render(); }
function activityPage() {
  return h("div", { class: "stack" },
    h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("jobs")), btn("", "ghost icon", loadActivity, "refresh")),
      activity.jobs.length ? h("div", { class: "tw" }, h("table", {}, h("tbody", {}, activity.jobs.map(j => h("tr", {}, h("td", {}, h("b", {}, j.title)), h("td", {}, h("span", { class: "badge " + (j.status === "done" ? "ok" : j.status === "failed" ? "bad" : "acc") }, t(j.status))), h("td", { class: "muted" }, fmtTime(j.started)), h("td", { class: "r" }, btn(t("log"), "sm", () => showJob(j.id, j.title)))))))) : h("div", { class: "empty" }, t("no_jobs"))),
    h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("audit"))),
      activity.audit.length ? h("div", { class: "tw" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, t("time")), h("th", {}, t("ip")), h("th", {}, t("action")), h("th", {}, t("detail")))),
        h("tbody", {}, activity.audit.map(e => h("tr", {}, h("td", { class: "muted" }, fmtTime(e.t)), h("td", { class: "ltr mono" }, e.ip), h("td", {}, h("span", { class: "badge" }, e.action)), h("td", { class: "ltr" }, e.detail)))))) : h("div", { class: "empty" }, "—")));
}

/* ------------------------------------------------------------ settings */
function settingsPage() {
  const s = data.server, cur = h("input", { type: "password", autocomplete: "current-password" }), nw = h("input", { type: "password", autocomplete: "new-password" });
  const kv = rows => h("dl", { class: "kv" }, rows.map(([k, v]) => [h("dt", {}, k), h("dd", { class: "ltr" }, v)]));
  return h("div", { class: "stack" },
    h("div", { class: "two" },
      h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("server"))), h("div", { class: "bd" }, kv([[t("version"), "v" + s.version], [t("python"), s.python], [t("host"), s.host + ":" + s.port], [t("uptime"), fmtUp(s.uptime)], [t("max_upload"), s.max_upload_mb + " MB"], [t("admin_port"), String(s.admin_port || "= " + s.port)], [t("auto_every"), s.auto_update_hours ? s.auto_update_hours + " " + t("hours") : t("off")], [t("cache_keep"), s.cache_enabled ? String(s.cache_keep) : t("off")], [t("inbox"), data.inbox.path]]), s.inbox_enabled ? h("p", { class: "hint" }, t("inbox_hint")) : null)),
      h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("security"))), h("div", { class: "bd" }, h("div", { class: "note" + (s.tls ? " ok" : "") }, s.tls ? t("tls_on") : t("tls_off")),
        kv([[t("session_idle"), s.session_minutes + " " + t("min")], [t("networks"), s.allowed_networks.join(", ")]])))),
    h("div", { class: "card", style: { maxWidth: "520px" } }, h("div", { class: "hd" }, h("h2", {}, t("change_password"))), h("div", { class: "bd" },
      h("label", { class: "f" }, h("span", {}, t("current_pw")), cur), h("label", { class: "f" }, h("span", {}, t("new_pw")), nw),
      btn(t("save"), "primary", async () => { try { await api("password", { current: cur.value, new: nw.value }); cur.value = nw.value = ""; toast(t("pw_changed")); } catch (e) { fail(e); } }, "check"))));
}

/* ------------------------------------------------------------ render */
function render() {
  const root = document.getElementById("app"); root.textContent = "";
  document.title = "Craft Apps — " + t("admin");
  if (!authed) { root.append(loginView()); return; }
  if (!data) { root.append(h("div", { class: "login" }, h("span", { class: "spin" }))); return; }
  const r = route(); let title, body;
  if (r.page === "apps" && r.id) { const a = data.apps.find(x => x.id === r.id); if (a) { title = a.title; body = appDetailPage(a); } }
  if (!body) {
    if (r.page === "apps") { title = t("nav_apps"); body = appsListPage(); }
    else if (r.page === "activity") { title = t("nav_activity"); body = activityPage(); }
    else if (r.page === "settings") { title = t("nav_settings"); body = settingsPage(); }
    else { title = t("nav_overview"); body = overviewPage(); }
  }
  root.append(shell(title, body));
}

(async function init() {
  try {
    session = await api("session");
    if (session.authenticated) { authed = true; csrf = session.csrf; render(); await reload(); if (route().page === "activity") loadActivity(); return; }
  } catch (e) { session = { setup_required: false }; }
  render();
})();
})();
