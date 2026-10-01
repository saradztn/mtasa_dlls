MTA:SA Z1000 LAYERED MOTORCYCLE AUDIO
=====================================

حالة مهمة قبل التركيب
---------------------
لا توجد في المستودع تسجيلات Kawasaki Z1000 حقيقية أو ملفات مرجعية مرفقة. لذلك لم أستخدم
صوت GTA:SA، ولم أنشئ صوتاً اصطناعياً أو صوت دراجة عام، ولم أحمّل تسجيلاً من الإنترنت.
ملفات audio/z1000_*.wav الموجودة حالياً هي WAV صامت قصير فقط كي تكون ملفات المورد وmeta.xml
صالحة وقابلة للتشغيل. Config.AudioReady=false عمداً؛ بهذه الحالة لا يتم تشغيلها ولا يتم كتم
الصوت الأصلي. لا يمكن ادعاء أن النتيجة الصوتية النهائية واقعية قبل وضع تسجيلات حقيقية ومعاينتها.

بعد إضافة التسجيلات وتشغيل أداة البناء، غيّر Config.AudioReady إلى true في config.lua.
عندها فقط يبدأ المورد بالمكساج المخصص ومحاولة كتم صوت المحرك الأصلي للدراجات المستهدفة.

المحتويات
---------
meta.xml                       تعريف مورد MTA وملفات WAV المنقولة للعملاء
config.lua                     الموديلات، RPM، الطبقات، مستوى الصوت، المسافة والأوامر
client.lua                     تقدير RPM، 3D mixer، crossfade، التنظيف وdebug
audio/*.wav                    حالياً placeholders صامتة؛ يستبدلها build_audio.py
 audio/reference/README.txt    أسماء التسجيلات المطلوبة وإرشادات التسجيل
 tools/build_audio.py          فحص وتجهيز WAV من التسجيلات التي تملك حق استخدامها

التركيب في MTA:SA
-----------------
1. انسخ مجلد z1000_sound بالكامل إلى مجلد الموارد في الخادم، مثلاً:
   server/mods/deathmatch/resources/[audio]/z1000_sound/
2. حدّد موديل الدراجة الصحيح في config.lua، وأضف التسجيلات الحقيقية كما هو موضح أدناه.
3. شغّل من كونسول الخادم: refresh ثم start z1000_sound.
4. يجب أن يشغّل كل لاعب يريد سماع الصوت هذا المورد على العميل. الصوت Client-side و3D محلي
   لكل لاعب، لذلك لا يحتاج المورد إلى server.lua.

تحديد المركبات المستهدفة
------------------------
افتراضياً لا يوجد model ID محدد، حتى لا يطبق الصوت على دراجة خاطئة.
في config.lua عدّل:

    Config.TargetModels = {
        [522] = true -- مثال فقط؛ استبدل 522 برقم موديل دراجتك الحقيقي
    }

يمكن إضافة أكثر من موديل:

    Config.TargetModels = {
        [522] = true,
        [581] = true
    }

أو استخدم element-data لكل مركبة بدلاً من قائمة الموديلات:

    Config.TargetElementData = {
        Enabled = true,
        Key = "z1000Sound",
        Value = true
    }

ثم يضع مورد السيرفر الذي ينشئ/يعرف المركبة هذه القيمة على المركبات المطلوبة، مثلاً:
setElementData(vehicle, "z1000Sound", true)

مصدر RPM وطريقة عمل الطبقات
---------------------------
MTA لا يوفّر RPM دقيقاً موحداً لكل المركبات. النظام يقدّر RPM من سرعة المركبة،
handling.maxVelocity، numberOfGears، التسارع/التباطؤ، ودواسة البنزين المحلية. للمركبات
البعيدة عن اللاعب يُستنتج throttle من التسارع المتزامن. هذا تقدير مرن وليس قراءة ECU حقيقية؛
اضبط Config.RPM وhandling الخاصة بموديلك داخل اللعبة.

الطبقات الأساسية: idle, low, mid, high, redline. يتم الانتقال بينها بمنحنيات smoothstep
وequal-power crossfade. تضاف طبقات accel/decel/engineBrake/limiter حسب throttle والحركة.
يمكن تفعيل lightAccel وhardAccel وthrottleRelease وcoast وintake وexhaust من
Config.LayerEnabled بعد تجهيز تسجيلاتها. تقدير تغيير الغيار يضيف هبوطاً قصيراً ناعماً؛
shift transient الحقيقي اختياري ولا يعمل إلا عند تفعيل Config.ShiftTransientEnabled.

ملاحظة مهمة عن كتم صوت GTA الأصلي
----------------------------------
setWorldSoundEnabled في MTA يكتم مجموعات صوتية عامة، وليس موديل مركبة واحداً، لذلك لا
يستخدمه المورد حتى لا تختفي أصوات سيارات/مركبات أخرى. بدلاً منه، عند AudioReady=true و
Config.SuppressStockSound=true، يفلتر onClientWorldSound المصدر الذي هو مركبة مستهدفة
ويكتم مجموعات محرك GTA الافتراضية 7-16 و40 فقط. يمكن تعديل Config.NativeEngineGroups
إذا كان إصدار/مود مركبتك يستخدم مجموعات أخرى.

هذه أفضل محاولة انتقائية متاحة عبر واجهات MTA المعتادة، وليست استبدالاً داخلياً لبنك GTA.
توثيق MTA يحذر من أن إلغاء صوت بعض المركبات عبر onClientWorldSound قد يجعل اللعبة تعيد
إطلاقه في الإطار التالي؛ لذلك اختبر مجموعة الموديل المستهدف والأداء على إصدار خادمك. إذا
كان مصدر الحدث لا يشير إلى المركبة أو بقيت بعض أصواتها، لن يستطيع هذا المورد ضمان إسكاتها
كلها من دون كتم مجموعات عالمية تؤثر على مركبات أخرى. لا يتم تعطيل صوت أي مركبة أخرى عمداً.

إضافة التسجيلات الحقيقية
------------------------
1. اقرأ audio/reference/README.txt.
2. ضع تسجيلات WAV نظيفة تملك حق استخدامها في audio/reference بالأسماء المحددة هناك.
   التسجيلات الأساسية التسعة مطلوبة للنظام الكامل؛ بقية الملفات اختيارية.
3. شغّل من مجلد المورد:

   python3 tools/build_audio.py --self-test
   python3 tools/build_audio.py

4. افحص audio/build_report.txt واستمع إلى الملفات الناتجة داخل MTA. لا يكفي نجاح الأداة
   وحده للحكم على جودة التسجيل أو خلوه من كل click/noise.
5. بعد اعتماد الملفات، غيّر السطر التالي في config.lua:

   Config.AudioReady = true

6. أعد تشغيل المورد. إذا كان ملف اختياري صامتاً أو لم تسجل ذلك النوع، اترك طبقته معطلة
   في Config.LayerEnabled. لا تفعّلها لمجرد أن placeholder موجود.

أداة البناء تقبل PCM WAV غير مضغوط فقط. إن كانت مرجعيتك MP3/OGG، حوّل نسخة عمل إلى WAV
قبل المعالجة، مثلاً باستخدام ffmpeg:

   ffmpeg -i input.ogg -ar 48000 -c:a pcm_s24le audio/reference/idle.wav

فحوصات المعالجة تشمل: sample rate، bit depth، mono/stereo، clipping، RMS/peak، صمت
البداية والنهاية، DC offset، ارتباط الطور بين قناتي stereo، ومقدار القفزة عند loop seam.
تقص الأداة الصمت تحت -55 dBFS مع إبقاء 30ms حماية، وتزيل متوسط DC، وتحول الناتج إلى
mono PCM 16-bit، وتطبع peak بشكل محافظ (هدف -2 dBFS مع حد boost افتراضي +3 dB)، وتطبق
crossfade خطي افتراضي 80ms على الحلقات. لا يوجد EQ أو compression أو limiter أو إزالة hum
آلية؛ لا يمكن إصلاح تسجيل clipped أو إلغاء صوت شارع/موسيقى بمجرد التطبيع. عند وجود طور
stereo معاكس بشدة تختار الأداة القناة الأعلى RMS بدلاً من دمج قد يلغي الصوت، وتصدر تحذيراً.

تسجيل المرجع المطلوب
--------------------
لأفضل نتيجة سجّل نفس جيل/نسخة Kawasaki Z1000 الذي تستهدفه قدر الإمكان: تسجيل خارجي نظيف
للعادم والمحرك، مع RPM معروف وثابت لكل حلقة RPM، وملفات مستقلة للتسارع/التباطؤ/limiter.
يفضل WAV PCM 24-bit و48 kHz أثناء التسجيل، دون موسيقى أو كلام أو clipping، مع تثبيت موضع
الميكروفون وعدم تغيير المسافة بين طبقات RPM. اترك بداية/نهاية قصيرة هادئة؛ أداة البناء
ستقص الصمت الزائد. لا تستخدم صوت لعبة أو ملفاً لا تملك حق استخدامه.

ضبط RPM والـ pitch والطبقات
---------------------------
- Config.RPM.Idle: RPM الخمول التقديري.
- Config.RPM.Redline / LimiterStart / Maximum: عتبة الـ redline والـ limiter والحد الأعلى.
- Config.RPM.LayerAnchors: RPM المرجعي المسجل لكل من idle/low/mid/high/redline.
- Config.RPM.OverlayAnchors: RPM مرجعي لطبقات accel/decel وغيرها.
- Config.RPM.DefaultGears: يستخدم إذا لم يرجع handling.numberOfGears قيمة صالحة.
- Config.RPM.GearCountOverride: اتركه 0 لاستخدام handling، أو اضبطه على 6 إذا أردت تثبيت
  تقدير ناقل الحركة على ست سرعات للدراجة المستهدفة.
- Config.RPM.GearSpeedExponent وConfig.Estimator: شكل تقدير الغيار/الاستجابة.
- Config.Pitch.Curve / Min / Max: مدى تغيير سرعة التشغيل؛ تم تقييده لتجنب صوت معدني.
  خفّضه إذا ظهرت آثار pitch واضحة، ولا تعتمد على pitch كبديل للتسجيلات الصحيحة.
- Config.Pitch.DopplerMaxPercent: Doppler-like صغير؛ أبقه منخفضاً لتجنب تغير مزعج.

ضبط مستوى الصوت و3D
-------------------
- Config.Volume.Master: مستوى المكساج العام (0 إلى 1).
- القيم الأخرى في Config.Volume: gain منفصل لكل طبقة.
- Config.MaxAudibleDistance: مسافة انقطاع 3D، وConfig.MinSoundDistance: نصف قطر الصوت الكامل.
- Config.MaxTrackedVehicles: حد أقصى صارم للمركبات التي تنشئ mix متزامناً. توجد 9 طبقات
  أساسية افتراضياً لكل مركبة، لذلك ارفع الحد فقط بعد اختبار CPU والصوت على الخادم.
- مواضع engine/front/rear تضبط من Config.SourceOffsets. طبقتا intake/exhaust الاختياريتان
  توازنان حسب جهة الكاميرا؛ بقية الصوت 3D ويتبع المركبة مع Doppler محدود.
- Config.Interior.Enabled يفعّل عينة helmet/onboard ثنائية الأبعاد للسائق المحلي فقط.
  هذه العينة تحتاج تسجيل onboard منفصلاً audio/reference/helmet.wav. لا يستخدم المورد
  مؤثر low-pass غير موثق ولا يصنع تأثير خوذة اصطناعياً.

أوامر الاختبار
--------------
/z1000debug                 إظهار/إخفاء overlay: RPM/speed/throttle/layer/gear/state
/z1000sound                 تشغيل/إيقاف test mix محلي 2D
/z1000rpm 3000              اختبار RPM يدوي
/z1000rpm 6000 0.6          RPM مع throttle من 0 إلى 1
/z1000rpm 9000
/z1000rpm 11000              يرفع throttle تلقائياً لاختبار limiter إذا تجاوز العتبة
/z1000stop                  إيقاف test mix بسلاسة؛ لا يوقف أصوات المركبات في العالم

اختبار /z1000sound و/z1000rpm هو 2D محلي لتجربة الطبقات دون قيادة، وليس اختبار 3D أو
مقارنة نهائية لموضع الصوت. إذا بقي Config.AudioReady=false ستخبرك الأوامر أن الملفات
المرجعية لم تجهز.
