# Advanced Rendering System (ARS) for MTA:SA

مورد عميل مستقل يستخدم واجهات DirectX 9 المتاحة داخل MTA:SA (`dxCreateScreenSource`, و`dxCreateRenderTarget`، وHLSL Effects). ليس DLSS حقيقيًا ولا يعترض محرك GTA؛ حدود التنفيذ موضحة أدناه بصراحة.

## التثبيت والتشغيل

1. انسخ مجلد `advanced_rendering` إلى مجلد موارد السيرفر، مثل:
   `mods/deathmatch/resources/[local]/advanced_rendering/`
2. نفّذ في كونسول السيرفر:
   ```text
   refresh
   start advanced_rendering
   ```
3. يلزم عميل MTA:SA **1.6.0 r22649 أو أحدث** بسبب استخدام حدث `onClientHUDRender` لالتقاط المشهد قبل HUD اللعبة.
4. عند التشغيل ستظهر رسالة `[ARS] Ready`. اضغط **F10** أو نفّذ `/ars` لفتح لوحة التحكم. استخدم `debugscript 3` لمراجعة رسائل إنشاء الـshader والـRender Target.

المورد client-side بالكامل ولا يحتاج DLL أو ReShade أو ENB أو خدمة خارجية. يبقى المشهد الأصلي ظاهرًا إذا تعذر إنشاء screen source أو RT؛ لا يضع المورد صورة سوداء بدلًا منه.

## الأوامر

| الأمر | الوظيفة |
| --- | --- |
| `/ars` أو `/arsmenu` | فتح/إغلاق لوحة التحكم |
| `/ars on`, `/ars off`, `/ars toggle` | تشغيل الـpipeline أو تجاوزه |
| `/ars status` | FPS، frame time، الدقة الداخلية، depth، وعدد الـpasses |
| `/ars preset ultra` | `ultra`, `high`, `cinematic`, `realistic`, `balanced`, `performance` |
| `/ars quality high` | `ultra`, `high`, `medium`, `low`, `compatibility` |
| `/ars scale 85` | يقبل `100`, `85`, `75`, `67`, `50` بالمئة |
| `/ars auto on` / `/ars auto off` | تشغيل/إيقاف DRS المعتمد على frame time |
| `/ars feature ssr on` | تشغيل/إيقاف pass؛ أسماء الميزات موجودة في تلميح الأمر |
| `/arsdebug depth` | `off`, `source` (raw capture), `depth`, `motion`, `history`, `rejection`, `ssao`, `ssr`, `resolution` |
| `/arsnextdebug` | التنقل بين صور التشخيص |

يمكن لمورد عميل آخر استدعاء exports: `setARSRenderEnabled(bool)` و`getARSStatus()`.

## معمارية الـpipeline

1. **Scene Capture** — `onClientHUDRender` يحدّث screen source بالحجم الأصلي للشاشة قبل HUD اللعبة.
2. **Internal-resolution sample** — `core.fx` يقرأ screen source عبر أربع عينات عند خفض دقة مرحلة المعالجة. لا يخفض دقة rasterization الأصلية للعبة.
3. **Depth extraction** — عند توفر depth المقروء فقط، يقرأ `DEPTHBUFFER` و`PROJECTION_MAIN_SCENE` ويعبّئ المسافة الخطية في RGB8. تخزّن buffers بنظام ping-pong.
4. **Camera motion estimate** — يقارن Lua وضع الكاميرا بين الإطارات؛ `motion_vectors.fx` يحول دوران/انتقال الكاميرا إلى flow تقريبي screen-space. هذه ليست object motion vectors من GTA.
5. **Hybrid edge AA** — `taa.fx` يخفف الحواف عالية التباين بشكل محافظ؛ مسار PS 3.0 يستخدم depth gating، وتقنية PS 2.0 تتجاوز عينات depth لتقليل كلفة التعليمات.
6. **Optional SSR/AO/contact ثم temporal resolve** — `ssr.fx` ينفذ خطوات ray march قصيرة مع depth test، و`ssao.fx` و`shadow_enhance.fx` يضيفان تقديرات عمق منخفضة الشدة قبل temporal accumulation حتى تستفيد من تثبيت التاريخ. `temporal.fx` يعيد إسقاط التاريخ ويحدّه إلى 4 جيران حاليين. مسار PS 3.0 يضيف رفض اختلاف depth/luma والحركة التفاعلية؛ تقنية PS 2.0 الأبسط تحتفظ بحدود اللون ورفض depth/الحركة عند الحاجة.
7. **Detail reconstruction / sharpen** — `reconstruction.fx` يعيد استخدام التباين الموجود مع depth gating، ثم `sharpen.fx` يضيف استعادة تفصيلية محدودة. لا يصنع أي منهما texture detail جديدة.
8. **Luminance / exposure / LDR tone mapping** — تمريرات منفصلة؛ تقدير التعريض يحسب 2×2 عينات (أربع عينات) في 1×1 RT عند تفعيل Auto Exposure.
9. **Upscale / final composite** — `super_resolution.fx` ينفذ Catmull–Rom مقيدًا بحدود اللون وباختلاف depth على PS 3.0؛ على PS 2.0 يستخدم upscale خطيًا أخف. ثم `final_composite.fx` يطبق إعدادات اللون المحايدة افتراضيًا.
10. **Material hooks** — `materials.fx` يطبق استجابة ضئيلة على أسماء textures معرفة في `config.lua`. `vehicle.fx` يطبق لمعة Fresnel بسيطة على مركبة اللاعب المحلية عند وجود texture pattern متوافق. يتضمن المورد `mta-helper.fx` محليًا بالجزء المطلوب، فلا يعتمد على ملف include من مورد آخر.

### جدول تأثير الـpasses والكلفة النسبية

الأرقام تختلف كثيرًا حسب الدقة والبطاقة والسائق. MTA لا يوفر GPU timestamp queries للـLua؛ المورد يعرض frame time/FPS الفعليين ووقت CPU تقريبيًا لإرسال أوامر الـpasses فقط.

| Pass | الأثر | كلفة GPU النسبية | ملاحظة |
| --- | --- | --- | --- |
| Capture / `core.fx` | downsample بأربع عينات وتقليل aliasing قبل المعالجة | منخفضة–متوسطة | screen source الأصلي يبقى full resolution |
| `depth.fx` | عمق خطي RGB8 لتقليل تسرب المعالجة عبر الحدود | منخفضة | يتطلب readable depth buffer |
| `motion_vectors.fx` | flow تقريبي من الكاميرا والعمق | منخفضة | لا يتتبع حركة كل جسم |
| `taa.fx` | تنعيم edge-aware قبل التاريخ الزمني | متوسطة | PS 3.0 depth-aware؛ PS 2.0 نواة أخف بلا depth، وليس بديلًا عن MSAA/SMAA الأصلي |
| `ssr.fx` | انعكاس screen-space محدود مع 6 خطوات عمق | عالية جدًا | PS 3.0؛ اختياري ومطفأ في preset الواقعي الافتراضي |
| `temporal.fx` | تراكم تاريخ، clamp، disocclusion/rejection | متوسطة | PS 3.0 يضيف رفض luminance؛ PS 2.0 compatibility أخف، وdepth يحسن الرفض |
| `reconstruction.fx` | استعادة تباين عالي التردد موجود فقط | متوسطة | PS 3.0 مع depth gating؛ نواة أخف على PS 2.0، والشدة محدودة لمنع halos |
| `ssao.fx` | 8 عينات depth قصيرة وAO خفيف | عالية | PS 3.0؛ لا توجد normals حقيقية، ويتجاوزها المورد على التقنية الأقدم |
| `shadow_enhance.fx` | contact-occlusion تقريبية منخفضة الشدة | منخفضة–متوسطة | لا يقرأ shadow map اللعبة |
| `sharpen.fx` | استعادة تفصيل unsharp منخفضة الشدة | متوسطة | PS 3.0 depth-aware؛ PS 2.0 نواة أبسط بلا depth، ويعمل داخليًا قبل التكبير |
| `luminance.fx` | تقدير أربع عينات إلى RT بحجم 1×1 | منخفضة | يعمل فقط مع tone mapping وauto exposure |
| `tonemap.fx` | ضغط highlights لصورة LDR | منخفضة | لا يسترجع معلومات HDR المفقودة |
| `super_resolution.fx` | Catmull–Rom محدود قرب depth edges | متوسطة–عالية | PS 3.0: أربع عينات cubic + عينة مرجعية وdepth؛ PS 2.0: upscale خطي، ثم fallback ثابت عند تعذر الاثنين |
| `final_composite.fx` | exposure/contrast/saturation/temperature | منخفضة | neutral افتراضيًا |
| `materials.fx` / `vehicle.fx` | accent مادي خفيف قبل screen capture | يتوقف على المشهد | world shader، وليس post-process |

## ملفات المورد

```text
advanced_rendering/
├── meta.xml
├── client.lua
├── config.lua
├── performance.lua
├── materials.lua
├── pipeline.lua
├── debug.lua
├── ui.lua
├── shaders/
│   ├── core.fx
│   ├── depth.fx
│   ├── motion_vectors.fx
│   ├── temporal.fx
│   ├── taa.fx
│   ├── reconstruction.fx
│   ├── super_resolution.fx
│   ├── ssao.fx
│   ├── ssr.fx
│   ├── shadow_enhance.fx
│   ├── materials.fx
│   ├── vehicle.fx
│   ├── mta-helper.fx
│   ├── sharpen.fx
│   ├── luminance.fx
│   ├── tonemap.fx
│   ├── final_composite.fx
│   └── debug.fx
├── textures/
│   ├── blue_noise.png
│   └── sampling_noise.png
└── presets/
    ├── ultra.lua
    ├── high.lua
    ├── cinematic.lua
    ├── realistic.lua
    ├── balanced.lua
    └── performance.lua
```

## ما يمكن وما لا يمكن تنفيذه داخل MTA

- **ممكن:** التقاط صورة الشاشة، معالجة HLSL متعددة المراحل، RT pool دائم، shader-readable depth على الأجهزة المدعومة، temporal history، downsample/upscale للـpost-process، تطبيق world-texture shaders على أسماء محددة، وإظهار FPS/frame time.
- **ليس ممكنًا من Resource عادي:** استبدال render graph الداخلي للعبة أو جعل GTA يرسم المشهد نفسه عند 50–85% ثم upscale. `dxCreateScreenSource` يلتقط المشهد بعد rasterization؛ لذا DRS هنا يخفض كلفة passes اللاحقة فقط، وليس كلفة رسم GTA الأصلية.
- **غير مكشوف:** object motion vectors، normal/albedo/material-ID buffers، depth guarantee على كل GPU، GPU timing queries، shadow map الداخلية، أو HDR scene target. بالتالي لا ندّعي وجود vectors حقيقية أو DLSS/AI أو إعادة إضاءة deferred حقيقية.
- **تبعًا لذلك:** الحركة المقدرة camera-only؛ moving objects تعتمد على depth/luma rejection وقد يظهر residual ghosting. SSAO/contact shading وnormal-from-depth SSR تقريبيان، وSSR يعمل فقط على معلومات ظاهرة في الشاشة وقد يفقد ما وراء الحواف. `vehicle.fx` accent لامع خفيف وليس انعكاس cubemap ديناميكيًا.
- **Color/HDR:** screen source صورة LDR؛ tone mapping هنا highlight roll-off اختياري لا يستطيع استرجاع highlights clipped في اللعبة. إعدادات color منفصلة ومحايدة افتراضيًا.
- **Material mapping:** أنماط أسماء textures الافتراضية قابلة للتعديل في `config.lua`، لكنها لا تمثل تصنيفًا دلاليًا مؤكدًا لكل خريطة أو سيرفر.
- **Sampling textures:** `blue_noise.png` نمط rank-noise حتمي 64×64 للاستخدام كـdither/jitter؛ لم يتم التحقق من كونه blue-noise أمثل. `sampling_noise.png` بلاطة ضوضاء رمادية 64×64 للـSSR، وليسا بيانات مولدة أو معالجة سحابية.

## التحقق والاختبار

تم فحص XML ومسارات جميع الملفات، وتحليل syntax لملفات Lua، وفحص توازن الأقواس/تقنيات/أسماء parameters في ملفات Effects ساكنًا. بيئة التطوير الحالية لا تحتوي عميل MTA:SA أو DirectX 9 `fxc`، لذلك **لم يتم تشغيل المورد داخل لعبة فعلية ولم يتم ادعاء نجاح تجميع HLSL على بطاقة معينة**. بعد تشغيله على عميل MTA راجع `debugscript 3`، جرّب `/arsdebug source` للتحقق من صورة الالتقاط الخام، ثم `/arsdebug depth`، وقارن `/ars off` و`/ars quality compatibility`. إذا لم يكن depth متاحًا فستظل passes التي تحتاجه متجاوزة تلقائيًا.
