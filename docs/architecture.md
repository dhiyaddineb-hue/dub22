# Architecture

```text
source video
    |
    +--> local inspection / transcription manifest
    |
    +--> professional provider adapter
    |       +--> create dubbing project
    |       +--> queue Arabic language target
    |       +--> poll project and target
    |       +--> download signed output
    |
    +--> local deterministic mixer
            +--> one WAV per segment
            +--> explicit start timestamps
            +--> FFmpeg muxing
            +--> final MP4
```

## Provider boundary

The CLI separates the provider API from local media assembly. The provider path delegates translation, speaker preservation, timing, and background-audio handling to the dubbing model. The local path is deterministic and useful for testing, but it cannot recreate the identity of a source speaker by itself.

## Configuration boundary

Credentials are read only from `ELEVENLABS_API_KEY`. They are not accepted as command-line arguments and are not written to manifests, logs, or output metadata. Model choice, target language, cloning strength, polling interval, and timeout are explicit CLI parameters so the same job can be reproduced.

## Failure handling

HTTP failures are reported with the provider response, failed project and target states stop polling, and a timeout prevents a hung job from running indefinitely. A completed target without a signed output URL is treated as an error rather than silently producing an empty file.
