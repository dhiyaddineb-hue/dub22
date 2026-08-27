# SILMA TTS v1 — research notes

Checked 2026-08-27 against the official GitHub repository, Hugging Face model card, Hugging Face launch article, and SILMA product page.

- Official repository: https://github.com/SILMA-AI/silma-tts
- Official model card: https://huggingface.co/silma-ai/silma-tts
- Official launch article: https://huggingface.co/blog/silma-ai/opensource-arabic-english-text-to-speech-model
- Official product page: https://silma.ai/open-source-arabic-tts-models
- The model card documents `pip install silma-tts`, `from silma_tts.api import SilmaTTS`, and `SilmaTTS().infer(ref_file=..., ref_text=..., gen_text=..., file_wave=..., seed=None, speed=1)`.
- The model card describes SILMA TTS v1 as a 150M-parameter bilingual Arabic/English model built on F5-TTS, with Arabic MSA and tashkeel support, reference voice cloning using less than 8 seconds, and Apache-2.0 model weights. Code is MIT according to the card/repository.
- The published performance number is RTF around 0.12 on an RTX 4090, not a T4. The SILMA product page separately states 1.9s for 100 characters; neither number is a T4 guarantee.
- The model card requires consent for cloned voices and disclosure that generated audio is AI-generated. This project must use only authorized reference voices.
- The official model card says weights can be downloaded through the package/runtime; exact disk/VRAM figures are not stated in the checked sources. T4 suitability is therefore a hypothesis to test, not a verified claim.
