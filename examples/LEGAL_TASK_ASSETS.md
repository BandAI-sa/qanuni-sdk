# Legal Task Assets

هذا الملف يربط بين **سيناريوهات اختبار الـ agent** وبين **الملفات القانونية الفعلية** المستخدمة في كل اختبار.

كل المستندات موجودة داخل:

[E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents)

## السيناريو 11: مراجعة عقد سهلة

الملف:
- [scenario_easy_contract_review_contract_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_easy_contract_review_contract_ar.md)

الغرض:
- عقد خدمات فيه صياغة مقبولة ظاهريًا لكن به فجوات مقصودة في السداد والإنهاء وتفاصيل الحوكمة.

ما الذي يفترض أن يكشفه الـ agent:
- ضعف بند السداد
- عمومية بند الإنهاء
- نقص بنود حوكمة أو التزامات تنفيذية أو علاجية

## السيناريو 12: مطالبة تجارية متوسطة

الملفات:
- [scenario_medium_claim_contract_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_medium_claim_contract_ar.md)
- [scenario_medium_claim_support_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_medium_claim_support_ar.md)

الغرض:
- عقد رئيسي + مذكرة وقائع وفاتورة ومتابعات سداد.

ما الذي يفترض أن يكشفه الـ agent:
- الأساس التعاقدي للمطالبة
- ما إذا كان القبول قد تحقق
- وجود مبلغ مستحق ومهلة سداد منتهية
- إمكانية الانتقال إلى مطالبة قبل النزاع

## السيناريو 13: حقوق عمالية متوسطة

الملف:
- [scenario_medium_employment_contract_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_medium_employment_contract_ar.md)

الغرض:
- عقد عمل غير محدد المدة مع مدة تجربة ورواتب وبدلات.

ما الذي يفترض أن يكشفه الـ agent:
- فحص فترة التجربة
- قراءة عناصر الأجر
- تقدير أثر الإنهاء ومكافأة نهاية الخدمة

## السيناريو 14: معالجة امتثال خصوصية صعبة

الملفات:
- [scenario_hard_privacy_notice_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_hard_privacy_notice_ar.md)
- [scenario_hard_privacy_data_map_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_hard_privacy_data_map_ar.md)

الغرض:
- إشعار خصوصية ضعيف + مذكرة داخلية تشرح المعالجة الحقيقية للبيانات.

ما الذي يفترض أن يكشفه الـ agent:
- فجوات الإفصاح
- ضعف بيان الحقوق
- مشاكل النقل الدولي
- الحاجة إلى remediation priorities واضحة

## السيناريو 15: إنشاء ومراجعة سياسة صعبة

الملف:
- [scenario_hard_policy_requirements_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_hard_policy_requirements_ar.md)

الغرض:
- مذكرة متطلبات تشغيلية لصياغة سياسة حضور وانصراف قابلة للاستخدام.

ما الذي يفترض أن تلاحظه:
- هل المخرجات تعكس فعلاً متطلبات الشركة
- هل تظهر ملاحظات مراجعة عملية
- هل توجد إجراءات متابعة بعد التوليد

## السيناريو 16: مطالبة معقدة مع نقص معلومات

الملفات:
- [scenario_complex_claim_contract_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_complex_claim_contract_ar.md)
- [scenario_complex_claim_partial_support_ar.md](/E:/Private/Nawaf/BandAI_SDK/free_edition/qanuni/acceptance_data/documents/scenario_complex_claim_partial_support_ar.md)

الغرض:
- عقد تشغيل وصيانة + مذكرة وقائع ناقصة عمدًا.

ما الذي يفترض أن يكشفه الـ agent:
- أن البيانات غير كافية لإصدار مطالبة نهائية من أول مرة
- أن هناك معلومات جوهرية ناقصة
- أن المسار يكتمل فقط بعد تزويد facts إضافية

## أفضل طريقة للاختبار

1. اقرأ الملف أو الملفين المرتبطين بالسيناريو.
2. شغّل مثال الـ agent المقابل من مجلد [examples](/E:/Private/Nawaf/BandAI_SDK/free_edition/examples).
3. راقب `Agent plan`.
4. راقب `Workflow breakdown`.
5. قارن الجواب النهائي بالعربية مع ما تتوقعه من المستندات.
