# تدقيق المرجع البصري/التقني

**المرجع الذي فُحص:** `saradztn/remakecity`, commit `b9371780017fa0378694ac2915ca69b0e1352280`, الملف `suncity-arena-01a10841-suncity (20).zip` (نحو 500 KB). أمكن جلب المستودع وفك ZIP الرئيسي و`source.zip`؛ لم يُفك الملف الداخلي `1.rar` لأن بيئة العمل لا تحتوي على `unrar/7z/bsdtar`.

## ما تحقّقنا منه فعلياً

- أرشيف المصدر يضم `wet.fx`, `glass`-style water effects (`water.fx`), `sky.fx`, `post.fx`, و`client.lua`, `env.lua`, `build.py`, وملفات التحقق والـ API stub.
- `wet.fx` يستخدم **screen-space reflection approximation** من لقطة `dxCreateScreenSource`، مع إحداثيات شاشة مستنتجة، وزن Fresnel، roughness blur، wet film/puddles، وبيانات مواد منفصلة. ليس ray tracing ولا انعكاساً فيزيائياً كاملاً.
- `sky.fx` يبني طبقات سحب إجرائية وسماء/نجوم؛ `post.fx` يطبّق grading وتأثيرات شاشة. يجري دفع uniforms من Lua. تصف وثائق المرجع توافق مسار الرسوميات المستهدف مع MTA 1.6 وShader Model 3، مع fallback محدود.
- المشروع المرجعي ينظم البيئة/الطقس والمواد والتأثيرات ويحتوي على اختبارات بنيوية وواجهة MTA وهمية/مقلّدة. وجود هذه الاختبارات لا يثبت تشغيل التأثيرات في عميل MTA حقيقي.
- لا توجد رخصة واضحة في الأرشيف الذي فُحص؛ لذلك لم تُنسخ ملفات الـFX أو الأصول منه إلى هذا المشروع. أُعيد تنفيذ المبادئ المطلوبة باستقلالية، وأُدرجت هذه الملاحظات لتوضيح المصدر والحدود.

## ما نُقل إلى ProjectSquidArena

مبدأ فصل wet reflective surface عن glass Fresnel وعن emissive strip، واستخدام screen capture محدود ومنخفض الدقة كبديل مقيد للانعكاس، والتحكم بالجودة، والإبقاء على fallback عند فشل إنشاء shader. صيغ HLSL في المورد مكتوبة للمشروع ولا تُدّعي اجتياز compiler؛ لا تتوفر MTA/DirectX في بيئة الإنشاء.

## بيئة التطوير المتاحة

البيئة الحالية Linux، Python 3.11؛ لم يُعثر على Blender أو عميل/خادم MTA أو `luac` أو compiler HLSL. لذلك يستخدم المشروع نماذج RenderWare هندسية مولّدة ببايثون، ولا يعتمد على تشغيل Blender. أعاد البناء اختبار قراءة DFF/COL/TXD وتحليل Lua/XML ساكناً؛ **لم يحدث اختبار داخل MTA**.
