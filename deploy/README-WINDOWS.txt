CRAFT WEB SERVER FOR WINDOWS
============================

1. Double-click  CraftManager.exe  and answer "Yes" to the administrator prompt.
2. Click "Install and start in the background" (choose a dashboard password the first time).
   From then on the server starts by itself after every restart of the computer, and starts
   again by itself if it ever stops.
3. Click "Open dashboard". Add your apps: drop the zip files you already downloaded into
   "Import downloaded files" (names like  app-name-v1.2.0.zip  are enough).

UPDATING THE SERVER
  Manager > Updates > "Check for updates"  (or dashboard > Settings > System and updates).
  The update is downloaded, verified (SHA-256) and tested before it replaces anything.
  Your apps, password and settings are NOT touched: they live in
      C:\ProgramData\CraftWebServer
  If a new version keeps crashing, the previous one is put back automatically.

SOMETHING NOT WORKING?
  Manager > "Check now" tests everything (ports, firewall, start at boot, password, HTTPS, logs...)
  and offers a button to fix what it can. The logs are in the same window.

REMOVING
  Manager > "Remove auto-start". Your data stays in C:\ProgramData\CraftWebServer (delete it by hand
  if you really want it gone).

NOTE: the programs are not code-signed, so Windows SmartScreen or your antivirus may warn
("More info" > "Run anyway"). Compare the file with SHA256SUMS on the release page if you want to be sure.

------------------------------------------------------------------------------------------------

خادم Craft لنظام ويندوز
=======================

1. انقر مرتين على CraftManager.exe ووافق على طلب صلاحية المسؤول.
2. اضغط "تثبيت وتشغيل في الخلفية" (واختر كلمة مرور للوحة التحكم أول مرة).
   بعدها يعمل الخادم تلقائياً بعد كل إعادة تشغيل للحاسوب، ويعيد تشغيل نفسه إن توقف.
3. اضغط "فتح لوحة التحكم" ثم "استيراد ملفات منزّلة" واسحب ملفات zip التي نزّلتها سابقاً.

تحديث الخادم: من لوحة الإدارة > التحديثات (أو لوحة التحكم > الإعدادات). يُنزَّل التحديث ويُتحقق منه ويُختبر قبل
أن يستبدل أي شيء. بياناتك وكلمة المرور وتطبيقاتك محفوظة في C:\ProgramData\CraftWebServer ولا تُمس أبداً.
إن تعطلت النسخة الجديدة تعود القديمة تلقائياً.

أي مشكلة؟ لوحة الإدارة > "افحص الآن" تفحص كل شيء وتقترح الحل. السجلات في النافذة نفسها.

ملاحظة: البرنامج غير موقَّع رقمياً، فقد يحذّر SmartScreen أو مضاد الفيروسات ("مزيد من المعلومات" ثم "تشغيل على أي حال").
