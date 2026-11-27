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
sys_title:"System and updates", sys_version:"Installed version", sys_check:"Check for updates", sys_update:"Update the server and restart", sys_restart:"Restart the server", sys_avail:"A new server version is available", sys_latest:"You have the latest version.", sys_offline:"Could not reach GitHub.",
sys_unsupervised:"One-click update and restart need the background service: install it with the Manager.", sys_auto:"Install new server versions automatically", sys_health:"Check everything", sys_restarting:"The server is restarting… this page reloads by itself.", sys_data:"Data folder", sys_staged:"Downloaded version", sys_restart_q:"Restart the server now? Apps are unavailable for a few seconds.", sys_go:"Go to settings",
make_offline:"Make offline-ready", offline_ready:"Offline-ready", localize_all:"Download internet resources automatically after each install (the app then works offline)", setup_https_btn:"Set up HTTPS",
https_title:"HTTPS", https_on:"HTTPS is active", https_restart:"Configured: restart the server to apply it", https_off:"Not set up", https_names:"Valid for", https_expires:"Expires in", days:"days",
https_missing:"New addresses of this server are not in the certificate: ", https_renew:"Issue a new certificate", https_extra:"Extra names or IPs (comma separated)", https_setup_run:"Set up / update HTTPS",
https_ca:"Certificate authority (trust it once on every device)", download_crt:"Download .crt", download_cer:"Download .cer", fingerprint:"Authority fingerprint (SHA-256)", trust_help:"How to trust the authority",
new_ca:"Create a new authority (devices must trust it again)", https_hint:"Creates a private certificate authority and a certificate for this server, entirely offline. Trust the authority once on each device; then the browser shows the padlock and features such as service workers and the clipboard work.",
compat_title:"Compatibility check", compat_run:"Check again", compat_ok:"No problems found", own_port_btn:"Run on its own port", coi_btn:"Enable COOP/COEP", f_ownport:"Run on its own port (best compatibility and isolation)", f_port:"Port (optional)", port_word:"port", port_err:"Port unavailable",
compat_settings:"Compatibility", isolate_all:"Run every app on its own port", isolate_hint:"Fixes apps that expect to live at the site root (stuck on loading) and keeps each app's storage separate. Open ports 8100 and up in the firewall.", coi_all:"Cross-origin isolation (COOP/COEP) for all apps",
diag_missing_files:"Files that do not exist", diag_missing_files_fix:"The page asks for files that are not in this build. The build may be incomplete: reinstall it or try another version.",
diag_root_paths:"Files requested from the site root", diag_root_paths_fix:"Handled automatically by compatibility mode. For full isolation (and apps with a service worker) run it on its own port.",
diag_external_resources:"Needs the internet", diag_external_resources_fix:"These hosts must be reachable, otherwise the app can stay on Loading on an offline network.",
diag_secure_context:"Needs a secure context (HTTPS)", diag_secure_context_fix:"Uses browser features that are blocked on http://IP. Enable HTTPS (tls_cert and tls_key).",
diag_wasm_threads:"Needs cross-origin isolation", diag_wasm_threads_fix:"Uses SharedArrayBuffer: enable COOP/COEP together with HTTPS.",
diag_service_worker:"Uses a service worker", diag_service_worker_fix:"Best run on its own port so it cannot affect the other apps.",
diag_base_href:"Sets base href", diag_base_href_fix:"May change where relative files are loaded from.", diag_no_index:"Entry file not found", diag_no_index_fix:"",
import_files:"Import downloaded files", import_title:"Import files you already downloaded", import_hint:"Pick the ZIP files (several at once). A name like app-v1.2.0.zip is enough: apps are recognised and created automatically, installed without downloading anything, and kept in the local cache.",
col_file:"File", col_app:"Application", col_version:"Version", import_start:"Import", import_done:"Done", import_skip:"skipped", import_pick:"Choose ZIP files", pick_app:"— choose —",
cache_title:"Saved downloads (cache)", cache_hint:"Every ZIP you download, upload or import is kept here, so any version can be reinstalled without internet.", cache_empty:"Nothing saved yet.", install_cached:"Install", cached_n:"cached",
f_auto:"Install updates automatically", last_checked:"Checked", update_now:"Update", onboard_title:"Already downloaded the app files?", onboard_body:"No setup needed: apps are created from the file names (name + version) and nothing is downloaded again.",
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
sys_title:"النظام والتحديث", sys_version:"الإصدار المثبّت", sys_check:"فحص التحديثات", sys_update:"تحديث الخادم وإعادة تشغيله", sys_restart:"إعادة تشغيل الخادم", sys_avail:"يوجد إصدار جديد للخادم", sys_latest:"لديك أحدث إصدار.", sys_offline:"تعذّر الوصول إلى GitHub.",
sys_unsupervised:"التحديث وإعادة التشغيل بنقرة واحدة يحتاجان إلى الخدمة في الخلفية: ثبّتها من لوحة الإدارة (Manager).", sys_auto:"تثبيت إصدارات الخادم الجديدة تلقائياً", sys_health:"فحص كل شيء", sys_restarting:"الخادم يعيد التشغيل… ستُحدَّث هذه الصفحة تلقائياً.", sys_data:"مجلد البيانات", sys_staged:"تم تنزيل الإصدار", sys_restart_q:"إعادة تشغيل الخادم الآن؟ تنقطع التطبيقات لثوانٍ.", sys_go:"إلى الإعدادات",
make_offline:"جعله يعمل بدون إنترنت", offline_ready:"جاهز للعمل بدون إنترنت", localize_all:"تنزيل موارد الإنترنت تلقائياً بعد كل تثبيت (يعمل التطبيق بعدها بدون إنترنت)", setup_https_btn:"تفعيل HTTPS",
https_title:"HTTPS", https_on:"HTTPS يعمل", https_restart:"تم الإعداد: أعد تشغيل الخادم للتطبيق", https_off:"غير مفعّل", https_names:"صالحة للعناوين", https_expires:"تنتهي بعد", days:"يوماً",
https_missing:"عناوين جديدة لهذا الخادم غير موجودة في الشهادة: ", https_renew:"إصدار شهادة جديدة", https_extra:"أسماء أو عناوين إضافية (مفصولة بفاصلة)", https_setup_run:"إعداد / تحديث HTTPS",
https_ca:"مرجع الشهادات (ثبّته مرة واحدة على كل جهاز)", download_crt:"تنزيل .crt", download_cer:"تنزيل .cer", fingerprint:"بصمة المرجع (SHA-256)", trust_help:"طريقة الوثوق بالمرجع",
new_ca:"إنشاء مرجع جديد (يجب الوثوق به من جديد على الأجهزة)", https_hint:"ينشئ مرجع شهادات خاصاً وشهادة لهذا الخادم بالكامل بدون إنترنت. تثبّت المرجع مرة واحدة على كل جهاز، ثم يظهر القفل وتعمل ميزات مثل Service Workers والحافظة.",
compat_title:"فحص التوافق", compat_run:"فحص مجدداً", compat_ok:"لم تُوجد مشاكل", own_port_btn:"تشغيل على منفذ خاص", coi_btn:"تفعيل COOP/COEP", f_ownport:"تشغيل على منفذ خاص (أفضل توافق وعزل)", f_port:"رقم المنفذ (اختياري)", port_word:"منفذ", port_err:"المنفذ غير متاح",
compat_settings:"التوافق", isolate_all:"تشغيل كل تطبيق على منفذ خاص", isolate_hint:"يحل مشكلة التطبيقات التي تتوقع العمل من جذر الموقع (تبقى على loading) ويعزل تخزين كل تطبيق. افتح المنافذ من 8100 فصاعداً في الجدار الناري.", coi_all:"عزل المصدر (COOP/COEP) لكل التطبيقات",
diag_missing_files:"ملفات غير موجودة", diag_missing_files_fix:"الصفحة تطلب ملفات ليست في هذه النسخة. قد تكون النسخة ناقصة: أعد تثبيتها أو جرّب نسخة أخرى.",
diag_root_paths:"ملفات تُطلب من جذر الموقع", diag_root_paths_fix:"تُعالَج تلقائياً بوضع التوافق. للعزل الكامل (وللتطبيقات ذات Service Worker) شغّله على منفذ خاص.",
diag_external_resources:"يحتاج إلى الإنترنت", diag_external_resources_fix:"يجب أن تكون هذه المواقع قابلة للوصول، وإلا قد يبقى التطبيق على loading في شبكة بلا إنترنت.",
diag_secure_context:"يحتاج سياقاً آمناً (HTTPS)", diag_secure_context_fix:"يستخدم ميزات يحجبها المتصفح على http://IP. فعّل HTTPS (tls_cert وtls_key).",
diag_wasm_threads:"يحتاج عزل المصدر", diag_wasm_threads_fix:"يستخدم SharedArrayBuffer: فعّل COOP/COEP مع HTTPS.",
diag_service_worker:"يستخدم Service Worker", diag_service_worker_fix:"الأفضل تشغيله على منفذ خاص كي لا يؤثر على بقية التطبيقات.",
diag_base_href:"يحدد base href", diag_base_href_fix:"قد يغيّر مكان تحميل الملفات النسبية.", diag_no_index:"ملف البداية غير موجود", diag_no_index_fix:"",
import_files:"استيراد ملفات منزّلة", import_title:"استيراد ملفات نزّلتها سابقاً", import_hint:"اختر ملفات ZIP (عدة ملفات معاً). يكفي اسم مثل app-v1.2.0.zip: تُكتشف التطبيقات وتُنشأ تلقائياً، وتُثبَّت بدون تنزيل أي شيء، وتُحفظ في الكاش المحلي.",
col_file:"الملف", col_app:"التطبيق", col_version:"النسخة", import_start:"استيراد", import_done:"تم", import_skip:"متجاوَز", import_pick:"اختر ملفات ZIP", pick_app:"— اختر —",
cache_title:"التنزيلات المحفوظة (الكاش)", cache_hint:"كل ملف ZIP تنزّله أو ترفعه أو تستورده يُحفظ هنا، فيمكن إعادة تثبيت أي نسخة بدون إنترنت.", cache_empty:"لا توجد ملفات محفوظة.", install_cached:"تثبيت", cached_n:"محفوظ",
f_auto:"تثبيت التحديثات تلقائياً", last_checked:"آخر فحص", update_now:"تحديث", onboard_title:"هل نزّلت ملفات التطبيقات سابقاً؟", onboard_body:"بدون أي إعداد: تُنشأ التطبيقات من أسماء الملفات (الاسم + رقم الإصدار) ولن يُعاد تنزيل شيء.",
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
const appUrl = a => location.protocol + "//" + location.hostname + ":" + (a.port || (data && data.server.public_port) || location.port) + (a.port ? "/" : "/" + encodeURIComponent(a.id) + "/");
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

function showJob(id, title, onDone) {
  const pre = h("pre", { class: "log" }, "…"), badge = h("span", { class: "badge acc" }, t("running"));
  const m = modal(title, h("div", {}, h("p", { style: { marginTop: 0 } }, badge), pre), null, true);
  let stop = false;
  m.el.addEventListener("close", () => { stop = true; diags = {}; httpsInfo = null; sysInfo = null; reload(); });
  (async function poll() {
    if (stop) return;
    try {
      const { job } = await api("job?id=" + encodeURIComponent(id));
      pre.textContent = job.log.join("\n") || "…"; pre.scrollTop = pre.scrollHeight;
      badge.className = "badge " + (job.status === "done" ? "ok" : job.status === "failed" ? "bad" : "acc");
      badge.textContent = t(job.status);
      if (job.status === "done" && onDone) onDone();
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
    ? h("div", {}, h("h2", { style: { marginBottom: "6px" } }, t("setup_title")), h("p", { class: "muted" }, t("setup_body")), h("code", { class: "cmd" }, session.setup_command || "python server.py --set-admin-password"))
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
      !a.enabled ? h("span", { class: "badge" }, "off") : null, a.port ? h("span", { class: "badge acc ltr" }, t("port_word") + " " + a.port) : null,
      a.port_error ? h("span", { class: "badge bad", title: a.port_error }, t("port_err")) : null, updateBadge(a)),
    h("div", { class: "acts" },
      a.live ? h("a", { class: "btn sm", href: appUrl(a), target: "_blank", rel: "noopener" }, ic("ext"), t("open")) : null,
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
    s.self_update && s.self_update.update ? h("div", { class: "note", style: { display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" } }, h("div", { style: { flex: 1 } }, h("b", {}, t("sys_avail") + ": " + s.self_update.latest), h("div", { class: "ltr" }, "v" + s.version + " → v" + s.self_update.latest)), btn(t("sys_go"), "primary", () => { location.hash = "#/settings"; })) : null,
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
    field("asset_pattern", t("f_pattern"), { ltr: true }), field("index_path", t("f_index"), { ltr: true }), chk("enabled", t("f_enabled")), chk("prerelease", t("f_pre")), chk("auto_update", t("f_auto")), chk("own_port", t("f_ownport")), field("port_config", t("f_port"), { ltr: true, ph: "auto" }), chk("cross_origin_isolation", t("f_coi")));
  modal(a ? t("edit") + ": " + a.title : t("add_app"), body, [{ label: t("cancel"), onclick: () => true }, { label: t("save"), kind: "primary", onclick: async () => {
    const app = {}; for (const k of Object.keys(f)) app[k] = f[k].type === "checkbox" ? f[k].checked : f[k].value;
    app.port = app.port_config; delete app.port_config;
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
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("cache_title")), h("span", { class: "muted ltr" }, a.cache.length + " · " + fmtBytes(total))),
    h("div", { class: "bd", style: { paddingBottom: a.cache.length ? "0" : "" } }, h("p", { class: "hint", style: { margin: 0 } }, t("cache_hint"))),
    a.cache.length ? h("div", { class: "tw", style: { marginTop: "14px" } }, h("table", {}, h("tbody", {}, a.cache.map(c => h("tr", {},
      h("td", { class: "ltr mono" }, c.tag), h("td", { class: "muted ltr" }, fmtBytes(c.size)), h("td", { class: "muted" }, fmtTime(c.mtime)),
      h("td", { class: "r" }, a.versions.some(v => v.tag === c.tag) ? h("span", { class: "badge ok" }, t("installed")) : btn(t("install_cached"), "sm", async () => { try { const r = await api("cache-install", { app: a.id, name: c.name }); showJob(r.job, t("install_cached") + ": " + c.tag); } catch (e) { fail(e); } }, "download"),
        btn("", "sm danger icon", async () => { if (await confirmBox(t("delete_confirm") + " " + c.tag, t("delete"))) { try { await api("cache-delete", { app: a.id, name: c.name }); reload(); } catch (e) { fail(e); } } }, "trash"))))))) : h("div", { class: "empty" }, t("cache_empty")));
}
function importDialog() {
  const rows = [], list = h("div", { class: "tw" }), input = h("input", { type: "file", accept: ".zip,application/zip", multiple: true });
  const body = h("div", {}, h("p", { style: { marginTop: 0 } }, t("import_hint")), h("label", { class: "drop" }, ic("upload"), h("div", {}, h("b", {}, t("import_pick"))), input), list);
  let news = {};
  const appSel = () => h("select", {}, h("option", { value: "" }, t("pick_app")), data.apps.map(x => h("option", { value: x.id }, x.title)), Object.values(news).map(n => h("option", { value: "+" + n.folder_prefix }, "＋ " + n.title)));
  input.addEventListener("change", async () => {
    const files = Array.from(input.files); rows.length = 0; list.textContent = "";
    let m = []; try { m = (await api("match", { names: files.map(f => f.name) })).matches; } catch (e) { fail(e); }
    news = {}; m.forEach(x => { if (x.suggest) news[x.suggest.folder_prefix] = x.suggest; });
    const table = h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, t("col_file")), h("th", {}, t("col_app")), h("th", {}, t("col_version")), h("th", {}))), h("tbody", {}));
    files.forEach((f, i) => {
      const sel = appSel(), ver = h("input", { type: "text", dir: "ltr" }), st = h("td", { class: "muted" });
      sel.value = (m[i] && (m[i].app || (m[i].suggest ? "+" + m[i].suggest.folder_prefix : ""))) || ""; ver.value = (m[i] && m[i].tag) || "";
      rows.push({ f, sel, ver, st });
      table.lastChild.append(h("tr", {}, h("td", { style: { wordBreak: "break-all" } }, h("div", { class: "ltr mono" }, f.name), h("div", { class: "muted ltr" }, fmtBytes(f.size))), h("td", {}, sel), h("td", {}, ver), st));
    });
    list.append(table);
  });
  modal(t("import_title"), body, [{ label: t("close"), onclick: () => { reload(); return true; } }, { label: t("import_start"), kind: "primary", onclick: async () => {
    const made = {};
    for (const r of rows) {   // apps recognised from the file names are created first
      const v = r.sel.value; if (!v.startsWith("+") || v in made) continue;
      const n = news[v.slice(1)]; made[v] = n.id;
      try { await api("app", { app: { id: n.id, title: n.title, folder_prefix: n.folder_prefix, asset_pattern: n.asset_pattern } }); } catch (e) { if (e.code !== "exists") { made[v] = null; r.st.textContent = errText(e); } }
    }
    for (const r of rows) {
      const appId = r.sel.value.startsWith("+") ? made[r.sel.value] : r.sel.value;
      if (!appId || !r.ver.value.trim()) { if (!r.st.textContent) r.st.textContent = t("import_skip"); continue; }
      r.st.textContent = "0%";
      try { await upload(r.f, appId, r.ver.value.trim(), p => { r.st.textContent = Math.round(p * 100) + "%"; }, "import"); r.st.textContent = "✓ " + t("import_done"); }
      catch (e) { r.st.textContent = errText(e); }
    }
    return false; } }], true);
}
let diags = {};
async function runDiag(a) {
  diags[a.id] = { loading: true }; render();
  try { diags[a.id] = await api("diagnose?app=" + encodeURIComponent(a.id)); } catch (e) { diags[a.id] = { error: errText(e) }; }
  render();
}
const saveApp = async (a, changes) => { try { await api("app", { app: Object.assign({}, a, { port: a.port_config || 0 }, changes), original_id: a.id }); toast(t("saved")); await reload(); runDiag(a); } catch (e) { fail(e); } };
function diagCard(a) {
  const d = diags[a.id];
  if (!d && a.active) setTimeout(() => runDiag(a), 0), diags[a.id] = { loading: true };
  const body = !a.active ? h("div", { class: "empty" }, t("no_versions")) : !d || d.loading ? h("div", { class: "empty" }, h("span", { class: "spin" })) : d.error ? h("div", { class: "empty" }, d.error) :
    !d.issues.length ? h("div", { class: "bd" }, h("span", { class: "badge ok" }, ic("check"), t("compat_ok"))) :
    h("div", { class: "tw" }, h("table", {}, h("tbody", {}, d.issues.map(i => h("tr", {},
      h("td", { style: { width: "1%" } }, h("span", { class: "badge " + (i.severity === "error" ? "bad" : i.severity === "warn" ? "warn" : "acc") }, i.severity)),
      h("td", {}, h("b", {}, t("diag_" + i.id) + (i.count ? " (" + i.count + ")" : "")), h("div", { class: "muted" }, t("diag_" + i.id + "_fix")),
        i.items && i.items.length ? h("div", { class: "ltr mono muted", style: { fontSize: "12px", marginTop: "4px", wordBreak: "break-all" } }, i.items.join(" · ")) : null),
      h("td", { class: "r" },
        ["root_paths", "service_worker"].includes(i.id) && !d.own_port ? btn(t("own_port_btn"), "sm primary", () => saveApp(a, { own_port: true }), "check") : null,
        i.id === "external_resources" ? btn(t("make_offline"), "sm primary", async () => { try { const r = await api("localize", { app: a.id }); showJob(r.job, t("make_offline") + ": " + a.title); } catch (e) { fail(e); } }, "download") : null,
        ["secure_context", "wasm_threads"].includes(i.id) && !d.tls ? btn(t("setup_https_btn"), "sm primary", () => { location.hash = "#/settings"; }, "check") : null,
        i.id === "wasm_threads" && !d.isolation ? btn(t("coi_btn"), "sm", () => saveApp(a, { cross_origin_isolation: true }), "check") : null))))));
  const ready = d && d.localized && d.localized.resources ? h("span", { class: "badge ok" }, ic("check"), t("offline_ready") + ": " + d.localized.resources) : null;
  return h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("compat_title")), ready, a.active ? btn("", "ghost icon", () => runDiag(a), "refresh", { title: t("compat_run") }) : null), body);
}
function appDetailPage(a) {
  const c = checks[a.id];
  return h("div", {}, h("a", { class: "back", href: "#/apps" }, h("span", { class: "flip" }, ic("back")), t("nav_apps")),
    h("div", { class: "card", style: { marginBottom: "18px" } }, h("div", { class: "bd" }, h("div", { class: "row", style: { display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" } },
      h("div", { class: "bubble" }, a.icon || "🌐"), h("div", { style: { flex: 1, minWidth: "180px" } }, h("h2", {}, a.title), h("div", { class: "muted" }, a.description || "—")),
      a.active ? h("span", { class: "badge ok ltr" }, ic("check"), a.active) : h("span", { class: "badge warn" }, t("not_installed")), updateBadge(a),
      a.live ? h("a", { class: "btn sm", href: appUrl(a), target: "_blank", rel: "noopener" }, ic("ext"), t("open")) : null,
      a.repo ? btn(t("check_updates"), "sm", () => checkApp(a), "refresh") : null,
      btn(t("edit"), "sm", () => appForm(a), "edit"),
      btn(t("remove"), "sm danger", async () => {
        const purge = h("input", { type: "checkbox" });
        if (await confirmBox(t("remove_confirm"), t("remove"), h("label", { class: "chk" }, purge, t("purge")))) { try { await api("app-delete", { id: a.id, purge: purge.checked }); location.hash = "#/apps"; await reload(); } catch (e) { fail(e); } }
      }, "trash")))),
    h("div", { class: "stack" }, versionsCard(a), diagCard(a), h("div", { class: "two" }, githubCard(a), uploadCard(a)), cacheCard(a)));
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
let sysInfo = null, doctor = null, doctorBusy = false;
async function loadSystem() { try { sysInfo = await api("system"); } catch (e) { sysInfo = { error: errText(e) }; } render(); }
function waitForRestart() {
  toast(t("sys_restarting"));
  const tick = async () => { try { const r = await fetch("/admin/api/session", { credentials: "same-origin" }); if (r.ok) { location.reload(); return; } } catch (e) {} setTimeout(tick, 2500); };
  setTimeout(tick, 5000);
}
async function runDoctor() { doctorBusy = true; render(); try { doctor = await api("doctor"); } catch (e) { fail(e); } doctorBusy = false; render(); }
function systemCard() {
  if (sysInfo === null) { sysInfo = { loading: true }; setTimeout(loadSystem, 0); }
  const i = sysInfo, u = i.update, can = i.supervised;
  const badge = i.loading ? h("span", { class: "spin" }) : i.staged ? h("span", { class: "badge warn" }, t("sys_staged") + " " + i.staged)
    : u && u.error ? h("span", { class: "badge" }, t("sys_offline")) : u && u.update ? h("span", { class: "badge warn ltr" }, t("sys_avail") + ": " + u.latest)
    : u && u.latest ? h("span", { class: "badge ok" }, ic("check"), t("sys_latest")) : null;
  const mark = { ok: "✓", warn: "!", fail: "✕", info: "•" };
  return h("div", { class: "card", style: { maxWidth: "720px" } }, h("div", { class: "hd" }, h("h2", {}, t("sys_title")), badge), h("div", { class: "bd" },
    i.loading ? null : h("dl", { class: "kv" }, h("dt", {}, t("sys_version")), h("dd", { class: "ltr" }, "v" + i.version + (i.kind ? " (" + i.kind + ")" : "")), h("dt", {}, t("sys_data")), h("dd", { class: "ltr mono", style: { wordBreak: "break-all" } }, i.data_dir || "—")),
    h("div", { class: "acts", style: { marginTop: "16px" } },
      btn(t("sys_check"), "", async () => { try { sysInfo.update = await api("system-check", {}); render(); } catch (e) { fail(e); } }, "refresh"),
      u && u.update ? btn(t("sys_update"), "primary", async () => { try { const r = await api("system-update", {}); showJob(r.job, t("sys_update"), waitForRestart); } catch (e) { fail(e); } }, "download", { disabled: can ? null : true }) : null,
      btn(t("sys_restart"), "", async () => { if (await confirmBox(t("sys_restart_q"), t("sys_restart"))) { try { await api("system-restart", {}); waitForRestart(); } catch (e) { fail(e); } } }, "undo", { disabled: can ? null : true })),
    !can && !i.loading ? h("p", { class: "hint" }, t("sys_unsupervised")) : null,
    h("div", { style: { marginTop: "18px" } }, btn(doctorBusy ? t("loading") : t("sys_health"), "", runDoctor, "check", { disabled: doctorBusy ? true : null }),
      doctor ? h("ul", { style: { listStyle: "none", margin: "14px 0 0", padding: 0 } }, doctor.checks.map(c => h("li", { style: { display: "flex", gap: "10px", padding: "8px 0", borderTop: "1px solid var(--border)" } },
        h("span", { class: "badge " + (c.status === "ok" ? "ok" : c.status === "warn" ? "warn" : c.status === "fail" ? "bad" : ""), style: { minWidth: "28px", justifyContent: "center" } }, mark[c.status]),
        h("div", {}, h("b", {}, c.title), h("div", { class: "muted", dir: "auto", style: { fontSize: "13px" } }, c.detail))))) : null)));
}
let httpsInfo = null;
async function loadHttps() { try { httpsInfo = await api("https-info"); } catch (e) { httpsInfo = { error: errText(e) }; } render(); }
const TRUST = "Windows (as Administrator):  certutil -addstore -f ROOT certs\\ca.pem\nmacOS:   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/ca.pem\niPhone / iPad:  open the .crt link, install the profile, then Settings > General > About > Certificate Trust Settings\nAndroid:  Settings > Security > Install a certificate > CA certificate\nFirefox:  Settings > Privacy > Certificates > Import";
function httpsCard() {
  if (httpsInfo === null) { httpsInfo = { loading: true }; setTimeout(loadHttps, 0); }
  const i = httpsInfo, names = h("input", { type: "text", dir: "ltr", placeholder: "craft.lan, 192.168.1.20" }), renew = h("input", { type: "checkbox" }), newCa = h("input", { type: "checkbox" });
  const caUrl = ext => location.protocol + "//" + location.hostname + ":" + (data.server.public_port || location.port) + "/ca." + ext;
  const status = i.loading ? h("span", { class: "spin" }) : i.active ? h("span", { class: "badge ok" }, ic("check"), t("https_on")) : i.needs_restart ? h("span", { class: "badge warn" }, t("https_restart")) : h("span", { class: "badge" }, t("https_off"));
  return h("div", { class: "card", style: { maxWidth: "720px" } }, h("div", { class: "hd" }, h("h2", {}, t("https_title")), status), h("div", { class: "bd" },
    h("p", { class: "hint", style: { marginTop: 0 } }, t("https_hint")),
    i.exists ? h("dl", { class: "kv" }, h("dt", {}, t("https_names")), h("dd", { class: "ltr" }, i.names.concat(i.ips).join(", ")), h("dt", {}, t("https_expires")), h("dd", { class: "ltr" }, i.days_left + " " + t("days")), h("dt", {}, t("fingerprint")), h("dd", { class: "ltr mono", style: { fontSize: "11px", wordBreak: "break-all" } }, i.ca_sha256 || "—")) : null,
    i.exists && i.missing_ips && i.missing_ips.length ? h("div", { class: "note", style: { marginTop: "14px" } }, t("https_missing") + i.missing_ips.join(", ")) : null,
    h("div", { class: "inline", style: { marginTop: "16px" } }, h("label", { class: "f", style: { margin: 0 } }, h("span", {}, t("https_extra")), names),
      btn(t("https_setup_run"), "primary", async () => { try { const r = await api("https-setup", { names: names.value.split(",").map(x => x.trim()).filter(Boolean), renew: renew.checked, new_ca: newCa.checked }); showJob(r.job, t("https_title")); } catch (e) { fail(e); } }, "check")),
    h("label", { class: "chk", style: { marginTop: "10px" } }, renew, t("https_renew")),
    h("label", { class: "chk" }, newCa, t("new_ca")),
    i.exists ? h("div", { style: { marginTop: "16px" } }, h("h3", { style: { fontSize: "14px", marginBottom: "8px" } }, t("https_ca")),
      h("div", { class: "acts" }, h("a", { class: "btn sm", href: caUrl("crt") }, ic("download"), t("download_crt")), h("a", { class: "btn sm", href: caUrl("cer") }, ic("download"), t("download_cer"))),
      h("h3", { style: { fontSize: "14px", margin: "16px 0 8px" } }, t("trust_help")), h("pre", { class: "log" }, TRUST)) : null));
}
function settingsPage() {
  const s = data.server, cur = h("input", { type: "password", autocomplete: "current-password" }), nw = h("input", { type: "password", autocomplete: "new-password" });
  const kv = rows => h("dl", { class: "kv" }, rows.map(([k, v]) => [h("dt", {}, k), h("dd", { class: "ltr" }, v)]));
  return h("div", { class: "stack" },
    h("div", { class: "two" },
      h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("server"))), h("div", { class: "bd" }, kv([[t("version"), "v" + s.version], [t("python"), s.python], [t("host"), s.host + ":" + (s.public_port || s.port)], [t("uptime"), fmtUp(s.uptime)], [t("max_upload"), s.max_upload_mb + " MB"], [t("admin_port"), String(s.admin_port || "= " + s.port)], [t("auto_every"), s.auto_update_hours ? s.auto_update_hours + " " + t("hours") : t("off")], [t("cache_keep"), s.cache_enabled ? String(s.cache_keep) : t("off")], [t("inbox"), data.inbox.path]]), s.inbox_enabled ? h("p", { class: "hint" }, t("inbox_hint")) : null)),
      h("div", { class: "card" }, h("div", { class: "hd" }, h("h2", {}, t("security"))), h("div", { class: "bd" }, h("div", { class: "note" + (s.tls ? " ok" : "") }, s.tls ? t("tls_on") : t("tls_off")),
        kv([[t("session_idle"), s.session_minutes + " " + t("min")], [t("networks"), s.allowed_networks.join(", ")]])))),
    h("div", { class: "card", style: { maxWidth: "720px" } }, h("div", { class: "hd" }, h("h2", {}, t("compat_settings"))), h("div", { class: "bd" },
      [["isolate_apps", t("isolate_all")], ["cross_origin_isolation", t("coi_all")], ["localize_external", t("localize_all")], ["self_update_auto", t("sys_auto")]].map(([key, label]) =>
        h("label", { class: "chk" }, h("input", { type: "checkbox", checked: s[key] ? true : null, onchange: async ev => { try { await api("settings", { [key]: ev.target.checked }); toast(t("saved")); reload(); } catch (e) { fail(e); ev.target.checked = !ev.target.checked; } } }), label)),
      h("p", { class: "hint" }, t("isolate_hint")))),
    systemCard(),
    httpsCard(),
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
