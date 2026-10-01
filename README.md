# mtasa_dlls

## Advanced Rendering System

تمت إضافة Resource عميل مستقل لـMTA:SA في [`advanced_rendering/`](advanced_rendering/README.md). يحتوي pipeline post-process متعدد المراحل بملفات HLSL منفصلة، screen-source capture، render-target pool، temporal accumulation تقريبية، depth-gated passes، لوحة تحكم وdebug views.

> هذا تنفيذ ضمن واجهات MTA:SA المتاحة وليس DLSS حقيقيًا. لا يستطيع Resource عادي التحكم بدقة رسم مشهد GTA الأصلي أو الوصول إلى object motion vectors / HDR / G-buffer. القيود وطريقة التركيب والأوامر في README المورد.

## Spider SA

في [`spider_sa/`](spider_sa/docs/README.md) ملف تكسترات كامل `Dragon_2.5.txd` (246 KB، 5 تكسترات) لمود العنكبوت الموجود في `Spider_sa.zip`، مبني من الصور المرفقة، إضافةً إلى مورد MTA:SA يركّب النموذج كعنصر مخصص بأوامر `/spider` و`/spiderall`.

الحزمة الأصلية كانت تفتقد ملف TXD نهائياً — النموذج يطلب 5 تكسترات (`box`, `spider_eye`, `i_sh3`, `spider_teeth`, `i`)، والمادتان `spider_eye` و`spider_teeth` لا يوجد لهما صور في الحزمة فأُعيد بناؤهما من ألوان صورك (موضّح بشفافية في README المورد).

> لم يُختبر الشكل النهائي داخل اللعبة هنا؛ التحقق تم على بنية الملف وألوانه وتشغيل منطق Lua في بيئة وهمية. التفاصيل والقيود في README المورد.
