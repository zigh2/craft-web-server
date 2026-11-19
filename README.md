# Craft Web Server

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Release](../../actions/workflows/release.yml/badge.svg)](../../actions/workflows/release.yml)
[![CodeQL](../../actions/workflows/codeql.yml/badge.svg)](../../actions/workflows/codeql.yml)
[![Latest release](https://img.shields.io/github/v/release/OWNER/craft-web-server)](../../releases/latest)

خادم ويب خفيف لتشغيل تطبيقات **Craft** (PDF Craft وFig Craft وغيرها) داخل شبكة محلية، مع **لوحة تحكم** احترافية لتثبيتها وتحديثها والرجوع لنسخ سابقة.

- **بدون أي اعتماديات**: Python 3.9+ فقط (أو ملف exe لويندوز، أو Docker).
- كل تطبيق على رابط ثابت: `http://SERVER-IP:8080/pdfcraft/`
- لوحة التحكم على منفذ **منفصل**: `http://SERVER-IP:8081/`
- **لا إعادة تنزيل**: ملفاتك المنزّلة سابقاً تُستورد، وكل ملف يُحفظ في كاش محلي.

## البدء السريع

اختر طريقة واحدة:

| الطريقة | الأوامر |
|---|---|
| **Python** | `python server.py --set-admin-password` ثم `python server.py` (ويندوز: `set-admin-password.bat` ثم `start-server.bat`) |
| **ويندوز بدون Python** | نزّل `craft-web-server-vX.Y.Z-windows-x64.zip` من [Releases](../../releases/latest) ثم `craft-web-server.exe passwd` و`craft-web-server.exe` |
| **Docker** | `docker compose up -d` ثم `docker compose exec craft-web-server python -m craftweb passwd` |

ثم افتح لوحة التحكم (يُطبع عنوانها عند التشغيل) وسجّل الدخول.
> ويندوز: اسمح بالمنفذين في الجدار الناري:
> `netsh advfirewall firewall add rule name="Craft Apps" dir=in action=allow protocol=TCP localport=8080,8081`

## عندك ملفات web منزّلة مسبقاً؟

لا تنزّلها مرة أخرى:

1. **من اللوحة**: نظرة عامة ← **استيراد ملفات منزّلة** ← اختر عدة ملفات zip معاً. تُطابَق بالاسم (`pdfcraft-web-v1.2.0.zip`)
   ويمكنك تصحيح التطبيق/النسخة يدوياً قبل الاستيراد.
2. **من سطر الأوامر** (مجلد على قرص الخادم): `python updater.py --import D:\downloads`
   (يقبل ملفات zip ومجلدات مفكوكة؛ `--app pdfcraft` لفرض التطبيق إن لم يطابق الاسم).
3. أو انسخ الملفات إلى مجلد **`inbox/`** فتُثبَّت تلقائياً.

القواعد: النسخة الأحدث تُفعَّل، ولا تُخفَّض النسخة الفعّالة أبداً، ولا يُفكّ إلا ما يتسع له `backup_count`، لكن **كل ملف يُحفظ في الكاش** ويمكن تثبيته لاحقاً بنقرة.

## لوحة التحكم

| الصفحة | الوظيفة |
|---|---|
| نظرة عامة | الحالة والمساحة، بطاقات التطبيقات، شارة "يوجد تحديث" تلقائية وزر **تحديث** مباشر |
| التطبيقات | النسخ المثبّتة (تفعيل/رجوع/حذف)، التثبيت من GitHub، رفع ZIP، **التنزيلات المحفوظة (الكاش)**، تعديل/إضافة/إزالة تطبيق |
| النشاط | العمليات الجارية وسجلها + سجل تدقيق (من فعل ماذا ومن أي عنوان) |
| الإعدادات | معلومات الخادم، حالة الأمان، تغيير كلمة المرور |

عربي/إنجليزي، فاتح/داكن، متجاوب مع الجوال.

## التحديثات

- **فحص تلقائي** كل `auto_update_hours` (6 افتراضياً) يعرض شارة التحديث دون أي نقرة.
- **تحديث تلقائي** اختياري لكل تطبيق (`auto_update`)، ولا يتراجع عن رجوعك المتعمّد لنسخة أقدم.
- **الكاش**: أي إصدار موجود في الكاش لا يُنزَّل من جديد، ويمكن إعادة تثبيته بدون إنترنت.
- **بدون إنترنت**: رفع ZIP من اللوحة، أو `inbox/`، أو `--import`.
- مستودعات خاصة أو حدّ GitHub API: اضبط `GITHUB_TOKEN`. الوكيل يُقرأ من `HTTPS_PROXY`.

## الأمان

- لوحة التحكم على **منفذ مستقل** (`admin_port`): التطبيق المستضاف يعمل من منفذ آخر (أصل مختلف) فلا يستطيع برمجياً مخاطبة اللوحة بجلسة المدير. المنفذ العام يردّ 404 على `/admin`. (ويمكن ربط اللوحة بـ `127.0.0.1` فقط عبر `admin_host`).
- **لا كلمة مرور افتراضية**، وتُخزَّن مشفّرة بـ scrypt.
- الدخول مسموح فقط من **الشبكات الخاصة** (`admin_allowed_networks`).
- جلسات على الخادم مرتبطة بعنوان IP، كوكي `HttpOnly` + `SameSite=Strict`، مهلة خمول وحدّ أقصى، حماية CSRF + فحص Origin، وقفل بعد 5 محاولات فاشلة.
- سياسة CSP صارمة (لا سكربت ولا ستايل مضمّن)، ولا تُقدَّم إلا ملفات واجهة محددة مسبقاً.
- الرفع والتنزيل: حدّ للحجم، فحص zip-slip وقنابل الضغط، فحص مساحة القرص، تحقق SHA-256، ولا يُرسل `GITHUB_TOKEN` لأي نطاق آخر.
- التفاصيل وسياسة الإبلاغ في [SECURITY.md](SECURITY.md).

### HTTPS
المتصفحات تعطّل Service Workers وclipboard و`SharedArrayBuffer` على `http://192.168.x.x`، وبعض تطبيقات Craft تحتاجها:
```bash
mkdir certs && mkcert -install
mkcert -cert-file certs/server.pem -key-file certs/server-key.pem SERVER-IP localhost
# apps.json -> settings: "tls_cert": "certs/server.pem", "tls_key": "certs/server-key.pem"
```
ثم ثبّت شهادة mkcert (CA) على الأجهزة الأخرى. للتطبيقات التي تحتاج COOP/COEP فعّل `cross_origin_isolation`.

## الإعدادات (`apps.json` ← `settings`)

| الإعداد | الافتراضي | الوصف |
|---|---|---|
| `port` / `host` | 8080 / `0.0.0.0` | منفذ التطبيقات وعنوان الربط |
| `admin_port` / `admin_host` | 8081 / فارغ | منفذ اللوحة (0 = مشترك مع التطبيقات، غير مُوصى به) |
| `admin_enabled` | true | تعطيل اللوحة بالكامل |
| `admin_allowed_networks` | الشبكات الخاصة | قائمة CIDR المسموح لها |
| `admin_session_minutes` | 30 | مهلة الخمول |
| `backup_count` | 3 | عدد النسخ القديمة المفكوكة بجانب الفعّالة |
| `cache_enabled` / `cache_keep` | true / 5 | حفظ ملفات zip وعدد النسخ المحفوظة لكل تطبيق |
| `auto_update_hours` | 6 | فترة فحص GitHub (0 = إيقاف) |
| `max_upload_mb` | 1024 | أقصى حجم رفع |
| `inbox_enabled` | true | مجلد الاستلام التلقائي |
| `cross_origin_isolation` | false | ترويسات COOP/COEP (عام أو لكل تطبيق) |
| `tls_cert` / `tls_key` | — | تفعيل HTTPS |
| `access_log` | false | تسجيل الطلبات في `logs/server.log` |

التطبيقات تُدار من اللوحة، أو يدوياً في `apps` (`id`, `folder_prefix`, `repo`, `asset_pattern`, `auto_update`, ...).

## سطر الأوامر

```
python -m craftweb serve | update | passwd | version        (أو craft-web-server.exe ...)
python updater.py --list                         النسخ المثبّتة
python updater.py --check                        مقارنة مع GitHub (رمز الخروج 10 إن وُجد تحديث)
python updater.py --latest --all                 تحديث كل التطبيقات
python updater.py --app pdfcraft --tag v1.2.0    إصدار محدد
python updater.py --app pdfcraft --rollback      النسخة السابقة
python updater.py --import PATH...               ملفات منزّلة مسبقاً
```

## الإصدارات على GitHub (تلقائية)

عند كل `push` إلى `main` يعمل workflow باسم **Release**:

1. يطبّق حزمة `incoming/` إن وُجدت، ويشغّل الاختبارات، ويحدد الرقم التالي.
2. ينشر Release `vX.Y.Z` فيه `zip` و`tar.gz` و`SHA256SUMS` مع **شهادة مصدر البناء** (attestation) وملاحظات من `CHANGELOG.md` + "What's changed" مصنّفة.
3. يضيف **نسخة ويندوز بدون Python** وصورة **Docker** (amd64/arm64) على GHCR. هذان اختياريان ولا يوقفان الإصدار إن فشلا.

الترقيم **تصاعدي دائماً**: إن عدّلت `VERSION` إلى رقم أعلى من آخر وسم يُستخدم كما هو، وإلا يزداد الـ patch تلقائياً. إصدار يدوي: *Actions ← Release ← Run workflow* واختر `patch/minor/major`.
تعديلات ملفات `.md` وحدها لا تُنتج إصداراً. أما CI (Linux/Windows/macOS، lint، CodeQL، Dependabot) فيعمل على كل PR.

### تحديث المشروع عبر `incoming/`
1. انسخ حزمة التحديث (`craft-web-server-vX.Y.Z.zip`) إلى `incoming/` في المستودع.
2. `git add incoming && git commit -m "update" && git push`
3. يفك الـ workflow الحزمة فوق المشروع، يختبرها، يحذف الـ zip، ويصدر release جديداً.

ملفات `.github/workflows/` لا تُستبدل من الحزم أبداً. إن كان `main` محمياً فاسمح لـ `github-actions[bot]` بالدفع.
بعد أول push استبدل `OWNER` في `README.md` و`docker-compose.yml` و`.github/ISSUE_TEMPLATE/config.yml` باسم حسابك.

## الهيكل

```
├── VERSION  CHANGELOG.md  apps.json  Dockerfile  docker-compose.yml
├── server.py  updater.py  run.py                 نقاط التشغيل
├── craftweb/    config · server · admin · security · updater · scheduler · inbox
│   └── dashboard/                                واجهة اللوحة (بدون اعتماديات)
├── root/ cache/ inbox/ logs/ state.json admin.json   بيانات التشغيل (غير مرفوعة)
├── incoming/                                     تحديثات المشروع نفسه
├── tests/   deploy/craft-web-server.service
└── .github/  workflows · scripts · ISSUE_TEMPLATE · dependabot.yml
```

التشغيل كخدمة: لينكس `deploy/craft-web.service`، ويندوز
`schtasks /create /tn "CraftApps" /tr "C:\path\craft-web-server.exe" /sc onstart /ru SYSTEM`.

## التطوير
```bash
python -m unittest discover -s tests -v
```
انظر [CONTRIBUTING.md](CONTRIBUTING.md). الرخصة: [MIT](LICENSE).

---
### English summary
Zero-dependency Python server + admin dashboard (own port, 8081) for hosting Craft web apps on a LAN. Import files you already
downloaded (`--import` or the dashboard), keep every zip in a local cache (no re-downloads, offline rollback), automatic
update checks with optional auto-install, rollback, audit log. Every push to `main` publishes a versioned GitHub release
(zip/tar.gz + checksums + provenance, Windows build, Docker image); drop a package into `incoming/` to update the project itself.
