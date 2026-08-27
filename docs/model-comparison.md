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


FireRedTTS3 is a newer official candidate. Its official repository states that FireRedTTS3-Base supports zero-shot voice cloning across 24 languages including Arabic, while FireRedTTS3-Instruct adds voice design and speech editing. The documented Python API accepts a prompt audio plus matching prompt text and a target language, which suits this dubbing workflow. The repository reports a 1.5B-class system and a direct pip install path; this is substantially more practical for Colab than Fish S2 Pro's 4B model and 24GB-VRAM recommendation. The official repository also documents Arabic explicitly, unlike Qwen3-TTS's current 10-language release, which does not list Arabic.

Sources:

- https://github.com/FireRedTeam/FireRedTTS3
- https://github.com/QwenLM/Qwen3-TTS
