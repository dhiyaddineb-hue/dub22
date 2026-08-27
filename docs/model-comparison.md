# Alternative model evaluation

Chatterbox Multilingual V3 is the selected XTTS alternative for this workspace. The official Resemble AI and Hugging Face materials describe it as a 0.5B multilingual model with zero-shot voice cloning across 20+ languages, including Arabic, and reference-audio conditioning. The model card documents `ChatterboxMultilingualTTS.from_pretrained(device=..., t3_model="v3")` and generation with `language_id="ar"`. It also documents `cfg` and `exaggeration` controls, with lower CFG recommended when the reference speaker is fast and higher exaggeration for more expressive delivery. Outputs include an embedded PerTh watermark. The repository and model card identify the model as MIT licensed, while the provider page notes that synthetic outputs remain watermarked.

Sources:

- https://github.com/resemble-ai/chatterbox
- https://huggingface.co/ResembleAI/chatterbox
- https://www.resemble.ai/learn/models/chatterbox-multilingual
