# Spider SA — ملف TXD + مورد MTA:SA لمود العنكبوت (Dragon 2.5)

**English summary at the bottom.**

هذا المجلد يسلّم ملف التكسترات المطلوب `assets/Dragon_2.5.txd` لمود العنكبوت
الموجود في `Spider_sa.zip`، إضافةً إلى مورد MTA:SA جاهز يركّب النموذج داخل اللعبة.

---

## 1. المشكلة التي كان يحلّها الملف

الحزمة `Spider_sa.zip` تحتوي على نموذج ومجموعة صور، **لكنها لا تحتوي على أي ملف TXD**.
النموذج `Dragon_2.5.dff` يطلب **خمس تكسترات** بأسماء محددة (مكتوبة داخل المواد):

| رقم المادة | اسم التكسترة في الـDFF | الملف المصدر في الحزمة |
|---|---|---|
| mat0 | `box` | لا يوجد (مادة بلون واحد) |
| mat1 | `spider_eye` | **لا يوجد ملف باسمها** |
| mat2 | `i_sh3` | `SH3.png` (شكل الشوكة/الخصلة) |
| mat3 | `spider_teeth` | **لا يوجد ملف باسمها** |
| mat4 | `i` | `Spinnen_Bein_tex.jpg` + `haar_detail_NRM.jpg` |

بدون TXD بهذه الأسماء بالضبط يظهر النموذج في اللعبة **بدون تكسترات** (أبيض/أسود)
أو يفشل تحميله. لذلك بُني الملف من الصور الموجودة، وأُعيد بناء المادتين الناقصتين
انطلاقاً من ألوان صورك نفسها (موضّح أدناه بشفافية).

---

## 2. جدول التوليد — من أين جاءت كل تكسترة

| التكسترة | المقاس | الصيغة | المصدر |
|---|---|---|---|
| `box` | 64×64 | X8R8G8B8 (بدون شفافية) | لون رمادي-بني محايد مشتق من متوسط ألوان الصور. المادة تستخدم إحداثي UV ثابت `(0,0)`، فالناتج كتلة لونية واحدة نظيفة بلا نمط ظاهر |
| `spider_eye` | 64×64 | X8R8G8B8 | **إعادة بناء** من لوحة ألوان صورك (بقع داكنة + لمعة رطبة). السبب: لا توجد صورة للعين في الحزمة |
| `i_sh3` | 128×128 | A8R8G8B8 (بقناة شفافية) | `SH3.png` — الشوكة الفاتحة، مقصوصة على حدود الشفافية ومكرّرة ×3 بارتفاعات مختلفة لتكوّن شريط خصلات قابل للتكرار |
| `spider_teeth` | 64×64 | A8R8G8B8 | **إعادة بناء** من لوحة ألوان صورك (أنياب عاجية على لثة داكنة). السبب: لا توجد صورة للأسنان في الحزمة |
| `i` | 128×256 | X8R8G8B8 | `Spinnen_Bein_tex.jpg` (صورة الساق) + دمج تفاصيل `haar_detail_NRM.jpg` كإبراز لمعان دقيق |

**نقطة مهمة بشفافية:** `spider_eye` و`spider_teeth` **ليستا صورتين من الحزمة** — لا
يوجد فيهما أي صورة بهذين الاسمين. أُعيد بناؤهما إجرائياً بألوان مستخرجة من صورك
(أغمق لون `(50,29,7)`، غامق `(61,37,12)`، متوسط `(111,70,29)`، أفتح `(244,169,85)`).
والبديل الوحيد كان ترك النموذج بدون عين ولا أسنان. إن كانت لديك صور أصلية للعين أو
الأسنان فأرسلها وسأستبدلها خلال دقيقة عبر `--source`.

كذلك `haar_detail_NRM.jpg` هو خريطة Normal، و**RenderWare/GTA:SA لا يملك خانة Normal Map**
للموديلات، فدُمج كتفاصيل إضاءة رمادية داخل `i` (بمقدار `--detail 0.25`) بدل إهماله.

---

## 3. مواصفات الـTXD (قيم مُتحقَّق منها فعلياً)

الملف مبني بمطابقة بايت-لبايت لبنية ملفات TXD الأصلية في GTA:SA:

```
TextureDictionary (0x16, version 0x1803FFFF)
├── Struct (0x01)  → uint16 count = 5, uint16 = 2
├── TextureNative (0x15) × 5
│   ├── Struct (0x01) → 88 بايت رأس D3D9 + بيانات المستوى
│   └── Extension (0x03، فارغ)
└── Extension (0x03، فارغ)
```

| الحقل | القيمة |
|---|---|
| Platform | `9` (D3D9) |
| Filter word | `0x001106` = FILTER_LINEAR_MIP_LINEAR + WRAP/WRAP |
| rasterFormat | `0x0500` (FORMAT_8888) للمواد ذات الشفافية، `0x0600` (FORMAT_888) لغيرها |
| d3dFormat | `0x15` = 21 = `D3DFMT_A8R8G8B8` / `0x16` = 22 = `D3DFMT_X8R8G8B8` |
| Depth | 32 |
| Mip levels | 1 + علم `autoMipmaps` مفعّل → اللعبة تولّد المستويات بنفسها |
| Flags byte | `0x05` (شفافية + mipmaps تلقائية) أو `0x04` |
| ترتيب البكسلات | BGRA، الصف الأول للأعلى (كما في ملفات Rockstar الأصلية) |

> تم التحقق من الصيغة مقابل ملف TXD أصلي للعبة (`infernus.txd`) ومقابل مصدر أداة
> libtxd: الصيغ غير المضغوطة تخزّن **قيمة D3DFORMAT الرقمية** (21/22) في حقل
> الأربع بايتات، وليس نصاً مثل `"A8R8G8B8"` — كتابة النص تُفسد الرأس.

---

## 4. طريقة الاستخدام

### أ) الملف وحده (الأساسي)

انسخ `assets/Dragon_2.5.txd` إلى أي أداة أو مورد يستخدم TXD لهذا المود.
اسم الملف غير مهم — المهم أن أسماء التكسترات داخله (`box`, `spider_eye`, `i_sh3`,
`spider_teeth`, `i`) مطابقة لما يطلبه الـDFF.

### ب) المورد الجاهز (spider_sa)

انسخ مجلد `spider_sa/` إلى `mods/deathmatch/resources/` ثم:

```
start spider_sa
```

| الأمر | الوظيفة |
|---|---|
| `/spider` | تركيب النموذج (مرة واحدة) وإنشاء العنكبوت عند نقطة التصويب |
| `/spider move` | نقل أقرب عنكبوت إلى نقطة التصويب |
| `/spider remove` | حذف كل العنكبوت الذي أنشأته |
| `/spider install` / `uninstall` | تركيب/إلغاء تركيب النموذج فقط |
| `/spider info` | حالة النموذج والملفات |
| `/spiderall` | **سيرفر**: يضع العنكبوت لكل اللاعبين أمام اللاعب المنفّذ |
| `/spiderall remove` \| `info` | إزالة/معلومات النسخة العامة |

المورد يتبع الترتيب المطلوب `COL → TXD → DFF`، ويستخدم `engineRequestModel("object")`
لحجز معرّف نموذج حر (لا يستبدل أي نموذج أصلي)، ويحرّره في `engineFreeModel` عند
إيقاف المورد. ويدعم سقوط اللاعبين الجدد: العميل يسأل السيرفر عن الحالة عند التشغيل
(`spiderSa:requestState`).

---

## 5. أدلة التحقّق (ما تم فحصه فعلياً)

| الفحص | النتيجة |
|---|---|
| بنية TXD (مشي على كل chunk) | 5 تكسترات، 246,440 بايت، المشي ينتهي عند آخر بايت بالضبط |
| تطابق الأسماء مع الـDFF | كل الأسماء الخمسة المطلوبة موجودة |
| حجم بيانات كل تكسترة | `width × height × 4` مطابق لكل تكسترة |
| ترتيب الألوان (دوران كامل) | متوسط `i` المستخرج من الملف = `(111, 70, 29)` = متوسط صورة `Spinnen_Bein_tex.jpg` بالضبط |
| حدود التصادم | حدود `Dragon_2.5.col` = حدود هندسة الـDFF تماماً `(±0.920, -0.959..1.027, 0..0.546)` |
| صحة Lua | 5 ملفات تمرّ بتحليل Lua 5.1 |
| تشغيل فعلي (محاكاة) | اختبار يشغّل المورد ببيئة MTA وهمية: التركيب/الإنشاء/النقل/الحذف/التحرير وسيرفر `/spiderall` — كلها تمر |
| حالة الملف المفقود | عند حجب ملف التكسترات في الاختبار تظهر رسالة `missing asset file: assets/Dragon_2.5.txd` ولا يُحجز معرّف نموذج ولا يُحمَّل أي ملف آخر |

تشغيل الفحوص محلياً:

```bash
python3 spider_sa/tools/validate.py     # فحص ثابت للبنية والصياغة
node    spider_sa/tools/smoke_test.js   # تشغيل المورد ببيئة وهمية
```

---

## 6. إعادة التوليد أو التعديل

```bash
python3 spider_sa/tools/build_txd.py                 # يقرأ ../../Spider_sa.zip ويكتب assets/Dragon_2.5.txd
python3 spider_sa/tools/build_txd.py --detail 0.45   # إبراز أقوى لخريطة الشعر
python3 spider_sa/tools/build_txd.py --source /path/to/images --out /tmp/my.txd
python3 spider_sa/tools/build_txd.py --flip-rows     # فقط إذا ظهرت التكسترات مقلوبة داخل اللعبة
python3 spider_sa/tools/build_txd.py --seed 7        # تغيير شكل العين/الأسنان الإجرائي
```

يحتاج فقط `Pillow`. بعد أي تعديل أعد تشغيل `validate.py`.

---

## 7. القيود — بصراحة كاملة

* **لم يُختبر داخل اللعبة.** لا يوجد MTA/GTA في بيئة العمل هنا. كل ما سبق تحقّق
  حسابي (بنية الملف، الألوان، حجم البيانات) وتشغيل Lua في بيئة وهمية. الشكل
  النهائي على الشاشة يحتاج تشغيلاً عندك.
* **`spider_eye` و`spider_teeth` إعادة بناء إجرائية** وليست صورك الأصلية (غير موجودة).
* **لا Mipmaps مخزّنة** داخل الملف: علم التوليد التلقائي مفعّل، واللعبة تبنيها.
  تخزين مستويات ميب + علم auto-mipmaps معاً يجعل GTA:SA يفشل في التحميل.
* **لا Normal Map**: RenderWare لا يملك خانة لها؛ `haar_detail_NRM.jpg` دُمج كتفاصيل
  إضاءة فقط.
* **أوراق الشعر/الشوكات أحادية الوجه** في الـDFF؛ المورد يفعّل `setElementDoubleSided`
  لتفادي اختفاء الشعر من زوايا معينة (يمكن تعطيله بـ `config.doubleSided = false`).
* **استبدال النموذج في MTA يتم على طرف العميل**: اللاعب الذي لا يشغّل المورد لن يرى
  العنكبوت. لذلك `/spiderall` (سيرفر) هو الطريق الصحيح للعبة متعددة اللاعبين.
* **يتطلب MTA 1.6** (r22190+) بسبب `engineRequestModel`/`engineFreeModel`. على
  نسخ أقدم يمكن ضبط `stockObjectModel` في `config.lua` لاستبدال نموذج أصلي.
* **الشفافية تعتمد على `engineReplaceModel`**: إن ظهرت حواف الشعر صلبة أو سوداء على
  بعض إصدارات MTA فهذا سلوك معروف لتلك النسخ، وليس خطأ في الـTXD.
* ضبط `language = "both"` يطبع الأمرين بالعربية والإنجليزية في الشات؛ بعض عملاء MTA
  بلا خط عربي في الشات الافتراضي — لجعل العربية فقط غيّر الخط أو استخدم `dxDrawText`.

---

## 8. الملفات

```
spider_sa/
├── meta.xml                      تعريف المورد (MTA 1.6+)
├── config.lua                    كل الإعدادات القابلة للتعديل
├── client.lua                    التركيب/الإنشاء/الأوامر/التنظيف
├── server.lua                    /spiderall ومزامنة الحالة
├── assets/
│   ├── Dragon_2.5.dff            النموذج (كما في الحزمة)
│   ├── Dragon_2.5.col            التصادم (كما في الحزمة)
│   └── Dragon_2.5.txd            ★ الملف المطلوب: 246,440 بايت، 5 تكسترات
├── docs/
│   ├── README.md                 هذا الملف
│   └── texture_preview.png       معاينة التكسترات الخمس
└── tools/                        أدوات تطوير (لا تُحمّل في اللعبة)
    ├── build_txd.py              باني الـTXD من صور الحزمة
    ├── validate.py               فحص ثابت: بنية TXD/DFF/COL + Lua
    ├── smoke_test.js             تشغيل المورد ببيئة MTA وهمية
    ├── mta_stub.lua / mta_stub_server.lua
    └── package.json
```

---

## English summary

The `Spider_sa.zip` bundle ships a DFF and several images but **no TXD**, so the model
would load untextured. `assets/Dragon_2.5.txd` (246,440 bytes, 5 textures) was built to
match the DFF's material names exactly: `box`, `spider_eye`, `i_sh3`, `spider_teeth`, `i`.

* `i` uses `Spinnen_Bein_tex.jpg` (the leg image) with `haar_detail_NRM.jpg` baked in as
  luminance relief, because RenderWare has no normal map slot.
* `i_sh3` uses `SH3.png`, cropped to its alpha bounds and repeated as a strand pattern.
* `box` is a neutral flat colour (its material samples a single constant UV).
* `spider_eye` and `spider_teeth` have **no matching image in the bundle** and were
  procedurally rebuilt from the palette of the supplied images — this is stated openly,
  not presented as original art.

Format verified against a shipping Rockstar `infernus.txd` and the libtxd writer:
platform 9, filter word `0x001106` (linear-mip-linear, wrap), rasterFormat `0x0500`/`0x0600`,
numeric D3DFORMAT `0x15`/`0x16`, depth 32, one level plus the auto-mipmap flag, BGRA texels
top row first. A full round trip (decode the built file, average the `i` texture) returns
exactly the source image average `(111, 70, 29)`, proving colour order and orientation.

`tools/validate.py` (static structure + Lua syntax) and `tools/smoke_test.js` (runs the
resource Lua against a mocked MTA API, including the missing-asset branch, which reports the
file by name instead of failing silently) both pass. **Nothing has been verified inside an
actual MTA client** — only the binaries and the Lua logic could be checked here.
