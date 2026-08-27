# Verified dubbing provider notes

The official ElevenLabs dubbing documentation states that its dubbing capability translates audio and video while preserving speaker emotion, timing, tone, and unique characteristics, and retains original background audio. It supports Arabic among 90+ languages. The documentation describes Dubbing v2 Alpha with configurable cloning strength from 0 to 10; the default of 7 is described as a balance between similarity and naturalness, while higher values prioritize similarity at the possible cost of naturalness.

The official API reference documents `POST https://api.elevenlabs.io/v1/dubbing/project` for creating a dubbing project from an uploaded file or public source URL. The multipart request can include `file`, `source_url`, `reference`, `source_language`, and `model_id` (`dubbing_v1` or `dubbing_v2`). The response contains a `project_id` and lifecycle status such as `queued`, `preparing`, `processing`, `ready`, or `failed`.

Sources:

- https://elevenlabs.io/docs/overview/capabilities/dubbing
- https://elevenlabs.io/docs/api-reference/dubbing/create-project


The verified target-language endpoint is `POST https://api.elevenlabs.io/v1/dubbing/project/:project_id/language`. It accepts `target_language` and optional `voice_settings`; the response includes `language_id`, status (`queued`, `processing`, `completed`, `stale`, or `failed`), warnings, and signed output URLs once completed. The project status endpoint is `GET https://api.elevenlabs.io/v1/dubbing/project/:project_id`.


The official page confirms that `voice_settings` is an optional object applied to the whole language target, but the public page does not expose a stable child-field schema in the rendered reference. The CLI therefore keeps the setting configurable and sends `cloning_strength` only when requested; if a provider account rejects that field, the user can omit it and rely on the provider default. The documented Dubbing v2 path is still the recommended one for automatic speaker preservation and synchronization.
