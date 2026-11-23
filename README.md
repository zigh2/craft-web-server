# Craft Web Server

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Release](../../actions/workflows/release.yml/badge.svg)](../../actions/workflows/release.yml)
[![CodeQL](../../actions/workflows/codeql.yml/badge.svg)](../../actions/workflows/codeql.yml)
[![Latest release](https://img.shields.io/github/v/release/zigh2/craft-web-server)](../../releases/latest)

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
> `netsh advfirewall firewall add rule name="Craft Apps" dir=in action=allow protocol=TCP localport=8080,8081,8100-8199`

## عندك ملفات web منزّلة مسبقاً؟ (بدون أي إعداد)

لا تعرّف التطبيقات ولا تنزّل شيئاً: يكفي أن يحوي اسم كل ملف **اسم التطبيق + رقم الإصدار**، مثل
`lesson-builder-web-v1.2.0.zip` أو `Quran_Tools_2.3.zip`. التطبيقات تُكتشف وتُنشأ تلقائياً، وتُجمَّع الملفات لكل تطبيق.

1. **من اللوحة**: نظرة عامة ← **استيراد ملفات منزّلة** ← اختر كل الملفات دفعة واحدة. ترى جدولاً فيه التطبيق والنسخة المكتشفان
   (التطبيقات الجديدة محدَّدة مسبقاً بعلامة «＋») ويمكنك تصحيح أي سطر قبل الضغط على «استيراد».
2. **من سطر الأوامر** (مجلد على قرص الخادم): `python updater.py --import D:\downloads`
   (يقبل zip ومجلدات مفكوكة؛ `--app NAME` لفرض تطبيق، `--no-create` لمنع إنشاء تطبيقات جديدة).
3. أو انسخ الملفات إلى مجلد **`inbox/`** فتُنشأ التطبيقات وتُثبَّت تلقائياً.

كيف يُقرأ الاسم؟ `pdfcraft-web-v1.2.0.zip` ← التطبيق `pdfcraft`، البادئة `pdfcraft-web-`، النسخة `v1.2.0`.
الاسم نفسه بفواصل أو حروف مختلفة (`FigCraft_Web_2.0.zip`) يُضم إلى التطبيق الموجود ولا يُكرَّر. ملف بلا رقم إصدار (`notes.zip`) يُتجاوز.
التطبيقات المنشأة تلقائياً بلا مستودع GitHub؛ أضف المستودع من «تعديل» إن أردت فحص التحديثات.

قواعد الاستيراد: النسخة الأحدث تُفعَّل، ولا تُخفَّض النسخة الفعّالة أبداً، ولا يُفكّ إلا ما يتسع له `backup_count`، لكن **كل ملف يُحفظ في الكاش** ويمكن تثبيته لاحقاً بنقرة.

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

## تطبيق يبقى على «Loading…» ولا يكتمل؟

السبب الأشهر: تطبيقات الويب المبنية للعمل من **جذر الموقع** تطلب ملفاتها من `/assets/app.js` و`/locales/en.json`،
بينما تُقدَّم هنا تحت `/اسم-التطبيق/`، فلا تجد ملفاتها وتبقى على التحميل. الحل على **ثلاث طبقات**، أغلبها تلقائي:

1. **وضع التوافق (تلقائي، بلا إعداد)**: أي طلب من الجذر يُوجَّه إلى التطبيق الصحيح بحسب الصفحة التي طلبته (`Referer`)، أو آخر تطبيق فتحتَه في المتصفح (كوكي).
   يعمل مع إعادة تحميل الصفحة ومسارات الـ SPA العميقة، ولا يستطيع الخروج من مجلد التطبيق. الاستجابات تحمل الترويسة `X-Craft-Compat: root-path`.
2. **منفذ خاص بالتطبيق (الحل الجذري)**: التطبيق يعمل من `http://SERVER-IP:8100/` فيرى نفسه في الجذر، ويُعزل تخزينه وService Workers عن بقية التطبيقات.
   فعّله لتطبيق واحد (تعديل ← *تشغيل على منفذ خاص*، أو زر الحل في بطاقة الفحص)، أو **لكل التطبيقات** من الإعدادات ← *التوافق*
   (`isolate_apps`). تُعطى المنافذ تلقائياً من `app_port_base` (8100) وتُحفظ، ولا تحتاج إعادة تشغيل. **افتح المنافذ 8100 فصاعداً في الجدار الناري.**
3. **فحص التوافق** (صفحة التطبيق): يقرأ التطبيق المثبّت ويخبرك بسبب المشكلة بدل التخمين:
   ملفات مفقودة فعلاً في النسخة، مسارات جذرية، **موارد من الإنترنت** (خطوط/CDN: تُعلّق التطبيق على شبكة بلا إنترنت)،
   ميزات تحتاج HTTPS (`crypto.subtle`, clipboard, Service Worker)، و`SharedArrayBuffer` الذي يحتاج COOP/COEP.
4. **توطين موارد الإنترنت (يعمل التطبيق بدون إنترنت)**: كثير من التطبيقات تحمّل خطوطاً أو مكتبات من CDN، وعلى شبكة بلا إنترنت يعلق التحميل.
   بعد كل تثبيت يحمّل الخادم هذه الملفات **مرة واحدة** (وتتبّع ما يستورده ملف CSS من خطوط وملفات فرعية) إلى `cache/vendor/`،
   ويعدّل التطبيق ليستعمل النسخ المحلية عبر `/_vendor/`. المخزن **مشترك بين كل التطبيقات والنسخ**، فلا يُعاد تنزيل شيء،
   وتبقى النسخة المحفوظة في الكاش كما هي. يدوياً: زر **جعله يعمل بدون إنترنت** في بطاقة الفحص، أو `python updater.py --localize [--app NAME]`.
   لخادم بلا إنترنت أبداً: شغّل التوطين على خادم متصل ثم انسخ مجلد `cache/vendor` (وملف `cache/vendor-index.json`) إلى الخادم الآخر.
   - **أمان**: روابط التوطين تأتي من ملفات طرف ثالث، لذا تُرفض العناوين الخاصة (127.x و192.168.x و169.254.169.254...) والمنافذ غير 80/443 وإعادات التوجيه إليها،
     مع حدود للحجم والعدد، فلا يمكن لصفحة أن تجعل الخادم يفحص شبكتك. مواقع التحليلات لا تُحمَّل، ومكتبات الوحدات (`esm.sh` وأمثالها) غير مدعومة وتُذكر في السجل.
   - يُعطَّل بـ `"localize_external": false` (أو من الإعدادات ← التوافق).

## الأمان

- لوحة التحكم على **منفذ مستقل** (`admin_port`): التطبيق المستضاف يعمل من منفذ آخر (أصل مختلف) فلا يستطيع برمجياً مخاطبة اللوحة بجلسة المدير. المنفذ العام يردّ 404 على `/admin`. (ويمكن ربط اللوحة بـ `127.0.0.1` فقط عبر `admin_host`).
- **لا كلمة مرور افتراضية**، وتُخزَّن مشفّرة بـ scrypt.
- الدخول مسموح فقط من **الشبكات الخاصة** (`admin_allowed_networks`).
- جلسات على الخادم مرتبطة بعنوان IP، كوكي `HttpOnly` + `SameSite=Strict`، مهلة خمول وحدّ أقصى، حماية CSRF + فحص Origin، وقفل بعد 5 محاولات فاشلة.
- سياسة CSP صارمة (لا سكربت ولا ستايل مضمّن)، ولا تُقدَّم إلا ملفات واجهة محددة مسبقاً.
- الرفع والتنزيل: حدّ للحجم، فحص zip-slip وقنابل الضغط، فحص مساحة القرص، تحقق SHA-256، ولا يُرسل `GITHUB_TOKEN` لأي نطاق آخر.
- التفاصيل وسياسة الإبلاغ في [SECURITY.md](SECURITY.md).

### HTTPS بأمر واحد
المتصفحات تعطّل Service Workers وclipboard و`SharedArrayBuffer` و`crypto.subtle` على `http://192.168.x.x`، وبعض تطبيقات Craft تحتاجها.
لا حاجة لـ openssl ولا mkcert (الكود بـ Python نقي ويعمل داخل exe وDocker):

```bash
python server.py --setup-https                 # ويندوز: setup-https.bat
python server.py --setup-https --names craft.lan,192.168.1.20      # أسماء إضافية
```
(أو من اللوحة: الإعدادات ← HTTPS ← *إعداد / تحديث HTTPS*.) ثم **أعد تشغيل الخادم**. يُنشأ في `certs/`:
مرجع شهادات خاص (`ca.pem`) وشهادة الخادم (`server.pem`) تغطي `localhost` واسم الجهاز وعناوين الشبكة (825 يوماً)، ويُفعَّل HTTPS في `apps.json` تلقائياً.
الشهادة تُجدَّد تلقائياً عند تغيّر عنوان الجهاز أو قرب انتهائها عند إعادة تشغيل الأمر، **والمرجع نفسه يبقى**.

**الوثوق بالمرجع مرة واحدة فقط على كل جهاز** (لا تحتاج إعادة ذلك عند التجديد). نزّل الشهادة من `https://SERVER-IP:8080/ca.crt` (اقبل التحذير مرة واحدة) ثم:

| النظام | الطريقة |
|---|---|
| Windows | `certutil -addstore -f ROOT certs\ca.pem` (كمسؤول) أو انقر مرتين على الملف ← تثبيت ← *Trusted Root* |
| macOS | `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/ca.pem` |
| iPhone / iPad | افتح `/ca.crt` ← تثبيت الملف الشخصي ← الإعدادات ← عام ← حول ← إعدادات الوثوق بالشهادات ← فعّله |
| Android | الإعدادات ← الأمان ← تثبيت شهادة ← شهادة CA |
| Firefox | الإعدادات ← الخصوصية ← الشهادات ← استيراد (أو `security.enterprise_roots.enabled`) |

**أمان المرجع**: مفتاحه `certs/ca-key.pem` لا يغادر الخادم أبداً (صلاحية 600، ولا يُقدَّم عبر الويب؛ يُقدَّم فقط `ca.crt` العام).
ولو تسرّب، المرجع **مقيَّد بـ NameConstraints** فلا يستطيع التوقيع إلا لأسماء الشبكة المحلية (`.lan` `.local` `.home` `.internal` و`localhost`
واسم الجهاز) وعناوين الشبكات الخاصة (بما فيها 100.64/10 لـ Tailscale)، فلا يصلح لانتحال موقع عام على الأجهزة التي تثق به (مُختبَر). إن أردت اسماً خارج ذلك: `--new-ca` (ثم تثق بالمرجع الجديد من جديد).
عند إيقاف الخادم نهائياً احذف المرجع من الأجهزة. في Docker: `docker compose exec craft-web-server python -m craftweb https` (الملفات في `/data/certs`).

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
| `auto_create_apps` | true | إنشاء التطبيقات تلقائياً من أسماء الملفات |
| `isolate_apps` / `app_port_base` | false / 8100 | تشغيل كل تطبيق على منفذ خاص، وأول منفذ يُعطى تلقائياً (لكل تطبيق: `own_port` أو `port`) |
| `cross_origin_isolation` | false | ترويسات COOP/COEP (عام أو لكل تطبيق) |
| `localize_external` | true | تنزيل موارد الإنترنت (CDN والخطوط) بعد كل تثبيت ليعمل التطبيق بدون إنترنت |
| `tls_cert` / `tls_key` | — | مسار الشهادة والمفتاح (يضبطهما `--setup-https` تلقائياً) |
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
python updater.py --localize [--app NAME]        توطين موارد الإنترنت (يعمل بدون إنترنت)
python server.py --setup-https [--names a,b]     HTTPS بأمر واحد (python -m craftweb https)
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
اسم المستودع المفترض: `zigh2/craft-web-server` (الروابط والشارات في هذا الملف تعتمد عليه).

## الهيكل

```
├── VERSION  CHANGELOG.md  apps.json  Dockerfile  docker-compose.yml
├── server.py  updater.py  run.py                 نقاط التشغيل
├── craftweb/    config · server · admin · security · updater · scheduler · inbox · portmux · diagnose · localize · pki
│   └── dashboard/                                واجهة اللوحة (بدون اعتماديات)
├── root/ cache/ (zips + vendor/) inbox/ logs/ certs/ state.json admin.json   بيانات التشغيل (غير مرفوعة)
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
