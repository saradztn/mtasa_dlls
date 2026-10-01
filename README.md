# mtasa_dlls

## Advanced Rendering System

تمت إضافة Resource عميل مستقل لـMTA:SA في [`advanced_rendering/`](advanced_rendering/README.md). يحتوي pipeline post-process متعدد المراحل بملفات HLSL منفصلة، screen-source capture، render-target pool، temporal accumulation تقريبية، depth-gated passes، لوحة تحكم وdebug views.

> هذا تنفيذ ضمن واجهات MTA:SA المتاحة وليس DLSS حقيقيًا. لا يستطيع Resource عادي التحكم بدقة رسم مشهد GTA الأصلي أو الوصول إلى object motion vectors / HDR / G-buffer. القيود وطريقة التركيب والأوامر في README المورد.
