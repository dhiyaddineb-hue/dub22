.PHONY: install test lint local-dub professional-dub

install:
	python3 -m pip install -r requirements.txt

test:
	python3 -m unittest discover -s tests -v

lint:
	python3 -m py_compile scripts/dub22.py

local-dub:
	./scripts/build_dub.sh assets/input/source.mp4 outputs/arabic_dub_local.mp4

professional-dub:
	dub22 run --input assets/input/source.mp4 --output outputs/arabic_dub_elevenlabs.mp4 --source-language en --target-language ar --model-id dubbing_v2 --cloning-strength 7

xtts-dub:
	python3 scripts/xtts_dub.py --input assets/input/source.mp4 --manifest manifests/dialogue_ar.json --output outputs/arabic_dub_xtts_v2.mp4 --workdir assets/xtts_segments --device cpu
