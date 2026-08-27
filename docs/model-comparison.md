# Alternative model evaluation

Chatterbox Multilingual V3 is the selected XTTS alternative for this workspace. The official Resemble AI and Hugging Face materials describe it as a 0.5B multilingual model with zero-shot voice cloning across 20+ languages, including Arabic, and reference-audio conditioning. The model card documents `ChatterboxMultilingualTTS.from_pretrained(device=..., t3_model="v3")` and generation with `language_id="ar"`. It also documents `cfg` and `exaggeration` controls, with lower CFG recommended when the reference speaker is fast and higher exaggeration for more expressive delivery. Outputs include an embedded PerTh watermark. The repository and model card identify the model as MIT licensed, while the provider page notes that synthetic outputs remain watermarked.

Sources:

- https://github.com/resemble-ai/chatterbox
- https://huggingface.co/ResembleAI/chatterbox
- https://www.resemble.ai/learn/models/chatterbox-multilingual


Additional comparison: Fun-CosyVoice 3 is reported by its official repository as strong in naturalness and speaker similarity, but its documented nine primary languages do not include Arabic, so it is not selected for this Arabic job. Fish Audio S2 Pro officially lists Arabic support and short-reference voice cloning, with strong multilingual and emotion controls, but its installation documentation requires approximately 24 GB of GPU memory for inference. The current sandbox has no GPU, so S2 Pro is not a practical local candidate here without moving execution to a GPU machine.

Sources:

- https://github.com/FunAudioLLM/CosyVoice
- https://github.com/fishaudio/fish-speech
- https://speech.fish.audio/install/
