# dub22 — Professional Arabic Dubbing Workspace

`dub22` هو خط تشغيل قابل لإعادة الاستخدام لدبلجة الفيديو إلى العربية. يوفّر مسارًا محليًا لفحص المدخلات وإعادة تركيب الصوت، ومسارًا احترافيًا اختياريًا عبر ElevenLabs Dubbing v2 عندما يوفّر المستخدم مفتاح API في بيئته. لا تُحفظ المفاتيح داخل المستودع.

> **النتيجة الواقعية:** مسار Dubbing v2 هو المسار المناسب عندما تكون الأولوية للحفاظ على هوية المتحدثين، النبرة، الإيقاع، التوقيت، والموسيقى الخلفية. أما الملفات الموجودة في `assets/audio/` فهي مخرجات اصطناعية محلية للاختبار وليست استنساخًا مطابقًا للممثلين.

## ما الذي توفره الأداة؟

| الوظيفة | التنفيذ |
|---|---|
| تفريغ الكلام | `manus-speech-to-text` عند تشغيله في بيئة Manus أو أي تفريغ خارجي يكتب إلى manifest |
| دبلجة احترافية بصوت قريب من الأصلي | ElevenLabs Dubbing v2 عبر `scripts/dub22.py run` |
| التحكم في قوة محاكاة الصوت | `--cloning-strength` من 0 إلى 10، والافتراضي 7 |
| العربية | `--target-language ar` |
| المتابعة وإعادة المحاولة | أوامر `create`, `status`, و`run` مع polling قابل للضبط |
| تركيب محلي قابل لإعادة البناء | `scripts/build_dub.sh` باستخدام مقاطع WAV وتوقيتات manifest |
| حماية الأسرار | متغير `ELEVENLABS_API_KEY` خارج Git، مع `.env.example` فقط |
| اختبارات | `python3 -m unittest discover -s tests -v` |

## التشغيل السريع للمسار الاحترافي

ثبّت الاعتمادية الوحيدة المطلوبة:

```bash
python3 -m pip install -r requirements.txt
```

ضع المفتاح في جلسة التشغيل فقط:

```bash
export ELEVENLABS_API_KEY='ضع-المفتاح-هنا'
```

افحص البيئة:

```bash
python3 scripts/dub22.py doctor
```

شغّل الدبلجة العربية ذات محاكاة الصوت، وانتظر حتى تكتمل، ثم نزّل الفيديو الناتج:

```bash
python3 scripts/dub22.py run \
  --input assets/input/source.mp4 \
  --output outputs/arabic_dub_elevenlabs.mp4 \
  --source-language en \
  --target-language ar \
  --model-id dubbing_v2 \
  --cloning-strength 7 \
  --reference dub22-arabic-test
```

للاستخدام على مراحل، أنشئ المشروع والهدف أولًا:

```bash
python3 scripts/dub22.py create \
  --input assets/input/source.mp4 \
  --source-language en \
  --target-language ar \
  --model-id dubbing_v2 \
  --cloning-strength 7
```

ثم استخدم المعرّفين اللذين أعادهما الأمر:

```bash
python3 scripts/dub22.py status \
  --project-id PROJECT_ID \
  --language-id LANGUAGE_ID
```

## المسار المحلي للاختبار

إذا كانت المقاطع العربية موجودة داخل `assets/audio/`، يمكن إعادة تركيب الفيديو دون اتصال خارجي:

```bash
chmod +x scripts/build_dub.sh
./scripts/build_dub.sh assets/input/source.mp4 outputs/arabic_dub_local.mp4
```

هذا المسار يحافظ على الصورة الأصلية ويستبدل مسار الصوت، ويضع كل مقطع عند وقت دخوله الموصوف في `manifests/dialogue_ar.json`. لتحديث الأداء، استبدل ملفات WAV فقط ثم أعد تشغيل السكربت.

## بنية المشروع

| المسار | المحتوى |
|---|---|
| `assets/input/source.mp4` | الفيديو الأصلي المستخدم في الاختبار |
| `assets/audio/` | مقطع صوتي مستقل لكل جملة للاختبار المحلي |
| `manifests/dialogue_ar.json` | النص العربي، المتحدث، وقت البداية، وملف الصوت |
| `manifests/source_transcript.txt` | التفريغ الزمني الأصلي |
| `scripts/dub22.py` | عميل CLI للدبلجة الاحترافية ومتابعة النتائج |
| `scripts/build_dub.sh` | تركيب محلي قابل لإعادة التشغيل عبر FFmpeg |
| `tests/test_cli.py` | اختبارات محلية لا تحتاج مفتاح API |
| `outputs/` | النتائج المحلية أو المنزّلة، مع استثناء النتائج التجريبية المتتبعة فقط |

## الاختبارات

```bash
python3 -m py_compile scripts/dub22.py
python3 -m unittest discover -s tests -v
```

## حدود الاستخدام

يتطلب المسار الاحترافي مفتاح API صالحًا وحسابًا يملك صلاحية تشغيل خدمة الدبلجة. لا يضع المشروع أي مفتاح أو credential داخل Git. كما أن استخدام أصوات أشخاص حقيقيين ينبغي أن يكون بتفويض مناسب؛ الأداة لا تتجاوز ضوابط المزود ولا تدّعي أن المسار المحلي استنساخ حقيقي.

## مراجع المزود

تستند واجهة المزود المستخدمة هنا إلى التوثيق الرسمي لإنشاء مشروع دبلجة، إنشاء هدف لغة، وجلب حالة المشروع والنتائج [1] [2] [3].

### References

[1]: https://elevenlabs.io/docs/overview/capabilities/dubbing "ElevenLabs Dubbing capabilities"
[2]: https://elevenlabs.io/docs/api-reference/dubbing/create-project "ElevenLabs Create project API"
[3]: https://elevenlabs.io/docs/api-reference/dubbing/language-targets/create-language-target "ElevenLabs Create language target API"
[4]: https://elevenlabs.io/docs/api-reference/dubbing/get-project "ElevenLabs Get project API"


## XTTS v2 المحلي ومحاكاة صوت المتحدث

يوجد مسار XTTS v2 محلي داخل `scripts/xtts_dub.py`. يستخدم مقطعًا مرجعيًا منفصلًا لكل متحدث من الصوت الأصلي، ثم يولّد كل جملة عربية كمقطع مستقل ويضعها عند وقت البداية في manifest.

ثبّت الاعتمادات الإضافية:

```bash
python3 -m pip install -r requirements-xtts.txt
```

شغّل XTTS v2 على CPU:

```bash
python3 scripts/xtts_dub.py \
  --input assets/input/source.mp4 \
  --manifest manifests/dialogue_ar.json \
  --output outputs/arabic_dub_xtts_v2.mp4 \
  --workdir assets/xtts_segments \
  --device cpu
```

يمكن استخدام CUDA على جهاز يدعمها بتغيير `--device cuda`. النموذج تم اختباره في هذه البيئة على CPU، ونجح في توليد ستة مقاطع WAV وتركيب فيديو عربي صالح مدته 24.842 ثانية. أُدخلت موافقة المستخدم على شروط CPML غير التجارية قبل تشغيل النموذج. راجع شروط النموذج قبل أي استخدام تجاري أو توزيع.


### نسخة XTTS v2 المحسّنة

توجد نسخة محسّنة في `outputs/arabic_dub_xtts_v2_final.mp4`. اعتمدت هذه النسخة مراجعًا منقّاة، حوارًا مجمّعًا لكل متحدث، حرارة توليد 0.45، وسرعة 1.0، مع قصّ صوتي تلقائي داخل نافذة كل مقطع عند الحاجة. ويعرض `manifests/xtts_final_transcript.txt` تفريغ فحص الوضوح للناتج.
