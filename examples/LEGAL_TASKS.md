# Agent Legal Tasks

هذا الملف مخصص لاختبار **الـ agent القانوني نفسه** من منظور بشري.

الملفات هنا ليست مجرد أمثلة API.
هي سيناريوهات قانونية متدرجة الصعوبة، الغرض منها أن ترى:

- كيف يفهم الـ agent الهدف القانوني
- كيف يختار الـ workflow المناسب
- كيف يمرر المخرجات من خطوة إلى التي بعدها
- كيف يتوقف إذا كانت المعلومات ناقصة
- كيف يصوغ الجواب النهائي بالعربية

ملفات الاختبار نفسها موثقة هنا:

- [LEGAL_TASK_ASSETS.md](./LEGAL_TASK_ASSETS.md)

## طريقة الاستخدام

من [E:/Private/Nawaf/BandAI_SDK/free_edition](/E:/Private/Nawaf/BandAI_SDK/free_edition):

```bash
python examples/example_11_legal_task_easy_contract_review.py --mode mocked
python examples/example_12_legal_task_medium_commercial_claim.py --mode mocked
python examples/example_16_legal_task_complex_missing_info_recovery.py --mode mocked
```

استخدم `mocked` أولًا حتى تتأكد من منطق الـ agent بدون استهلاك كوتا.
بعدها انتقل إلى `--mode live` تدريجيًا.

## التدرج المقترح

### 1. سهل: `example_11_legal_task_easy_contract_review.py`

القضية:
- لدينا عقد خدمات واحد.
- نريد من الـ agent أن يراجعه ويحدد الثغرات والمخاطر والتعديلات المقترحة.

ما الذي تختبره:
- اختيار سيناريو `CONTRACT_REVIEW_ONLY`
- تشغيل workflow واحد فقط
- جودة التفكيك الداخلي للمراجعة

معيار القبول:
- يختار الـ planner `workflow.contract_review` فقط.
- تظهر مخرجات الفحص كخلاصة قانونية مفهومة.
- يظهر breakdown واضح لمراحل التصنيف والاستخراج وتحليل المخاطر.

### 2. متوسط: `example_12_legal_task_medium_commercial_claim.py`

القضية:
- لدينا عقد خدمات.
- لدينا واقعة تأخر في السداد.
- نريد مراجعة العقد ثم بناء مطالبة قبل النزاع.

ما الذي تختبره:
- قدرة الـ agent على دمج مسارين مترابطين
- احترام predecessor بين مراجعة العقد والمطالبة
- انتقال المخرجات بين workflow وworkflow

معيار القبول:
- يختار `workflow.contract_review` ثم `workflow.pre_litigation_notice`.
- النتيجة النهائية تتضمن منطقًا تعاقديًا ومطالبة عملية.
- يظهر في الحالة أن الـ agent أكمل مرحلتين مترابطتين.

### 3. متوسط: `example_13_legal_task_medium_employment_rights.py`

القضية:
- موظف يريد فهم موقفه العمالي.
- لدينا عقد عمل وبعض الحقائق المالية والزمنية.

ما الذي تختبره:
- ربط قراءة العقد بالفحوص النظامية العمالية
- فحص فترة التجربة
- فحص مكافأة نهاية الخدمة

معيار القبول:
- يختار `workflow.employment_review`.
- يشرح النتيجة بالعربية بلغة عملية.
- تظهر المخاطر العمالية ومقترحات المتابعة.

### 4. صعب: `example_14_legal_task_hard_privacy_remediation.py`

القضية:
- لدينا إشعار خصوصية ناقص أو ضعيف.
- نريد تشخيص فجوات الامتثال وترتيب المعالجة وربما توليد مسودة علاجية.

ما الذي تختبره:
- قدرة الـ agent على تحويل نص ضعيف إلى remediation plan
- التعامل مع سياق بيانات وشركة وخدمة بشكل مترابط
- دمج التحليل مع مسودة علاجية

معيار القبول:
- يختار `workflow.privacy_compliance_review`.
- تظهر فجوات الامتثال وأولويات المعالجة.
- يظهر policy draft عندما يكون السياق كافيًا.

### 5. صعب: `example_15_legal_task_hard_policy_creation_review.py`

القضية:
- نريد إنشاء سياسة HR بالعربية ثم مراجعتها.

ما الذي تختبره:
- أن الـ agent لا يكتفي بالتوليد فقط
- بل يراجع الناتج ويولد ملاحظات وخطوات لاحقة

معيار القبول:
- يختار `workflow.policy_generation_review`.
- يظهر النص المولد كاملًا أو بشكل واضح.
- تظهر `review_notes` و`follow_up_actions`.

### 6. معقد: `example_16_legal_task_complex_missing_info_recovery.py`

القضية:
- نريد مطالبة قبل النزاع لكن البيانات الجوهرية ناقصة في البداية.
- بعد ذلك نكمل البيانات ونطلب من الـ agent المحاولة من جديد.

ما الذي تختبره:
- stopping rules
- guardrails
- عدم القفز إلى استنتاج قانوني ناقص
- recovery بعد استكمال البيانات

معيار القبول:
- المرحلة الأولى لا تدعي اكتمال المسار.
- تظهر `missing_inputs` أو `next_question`.
- المرحلة الثانية تكمل المسار بنجاح بعد توفير البيانات.

## كيف تراقب جودة الـ agent

أثناء التشغيل ركز على:

1. `Agent plan`
   هذا يوضح كيف فكر المخطط وما الـ workflows التي اختارها.

2. `Agent result summary`
   هذا يوضح هل انتهى المسار، أم طلب معلومات إضافية، وما الـ capabilities التي اكتملت.

3. `Workflow breakdown: ...`
   هذا هو المكان الأهم لترى كيف اشتغلت الأدوات معًا داخل كل workflow.

4. `Agent state payload`
   هذا يعرض التراكم الحقيقي للنتائج: findings, evidence, actions, artifacts.

5. `Observability events`
   هذا يريك الاستخدام والزمن والفشل والـ cache من منظور التشغيل.

## أفضل ترتيب للتجربة البشرية

1. ابدأ بـ `example_11_legal_task_easy_contract_review.py`
2. ثم `example_12_legal_task_medium_commercial_claim.py`
3. ثم `example_13_legal_task_medium_employment_rights.py`
4. ثم `example_14_legal_task_hard_privacy_remediation.py`
5. ثم `example_15_legal_task_hard_policy_creation_review.py`
6. اختم بـ `example_16_legal_task_complex_missing_info_recovery.py`

## الانتقال إلى الوضع الحي

بعد ثبات الـ mocked path:

```bash
python examples/example_11_legal_task_easy_contract_review.py --mode live
python examples/example_12_legal_task_medium_commercial_claim.py --mode live
python examples/example_14_legal_task_hard_privacy_remediation.py --mode live
```

الأفضل أن تبدأ بالمهام السهلة أو المتوسطة قبل السيناريوهات المعقدة.
