# Coach Words Agent Design

## Purpose
Coach Words empowers professional coaches to transform raw coaching session recordings into structured, reusable intelligence. The platform ingests audio or video files, extracts high-quality transcriptions with configurable options, and delivers derivative artifacts—such as summaries or fine-tuning datasets—directly into the recording's source directory.

## Primary User Flow
- Coach adds recordings via drag-and-drop or file picker in the GUI.
- For each file, the destination for generated artifacts defaults to the recording's source folder.
- The coach selects desired processing actions for the batch.

## Initial Feature Set
1. **Transcription Model Selection**
   - Available providers: WhisperX (local), GCP STT Chirp, OpenAI Transcribe, with expansion hooks.
   - App validates credentials/model availability.
   - App guides user through setup when prerequisites are missing (handoff or interactive).
2. **Transcription Options**
   - Toggles and selectors: diarization, timestamps, SRT output, TXT output, anonymisation, proper-noun obfuscation, PII removal, etc.
   - Extensible option registry for future controls.
3. **Fine-Tuning Dataset Generation**
   - Template outputs for OpenAI, Claude, Gemini, aggregated, or generic fine-tune formats.
   - Generated artifacts stored per-file alongside original recordings.

## Architectural Principles
- **Hyper-Modular Design**: Every feature built as a swappable module with clean contracts. No hard coupling across modules; dependency injection wherever practical.
- **Extensibility-First**: New transcription engines, option toggles, or post-processing pipelines can be added without touching core flow.
- **MCP/MVC Inspired**: Use controller-like orchestrators coordinating interchangeable model modules and view components. Encourage local overrides and experimentation.
- **Configurable Pipelines**: Batch operations expressed as pipelines with standardized IO contracts.
- **Robust Validation & Guidance**: Each module responsible for validating its requirements and exposing actionable remediation steps.

## Next Steps
- Define module interface contracts for ingestion, transcription, post-processing, and delivery.
- Map UI components to underlying pipeline modules.
- Capture credential management flows per provider.
- Draft test strategy ensuring modules can be unit-tested in isolation and in pipeline compositions.
