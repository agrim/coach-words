# Technical Documentation & Developer Guide

This document outlines the architecture, prompt engineering, and technical strategies ("tricks") employed in the **Gemini Coach** application.

## 1. System Architecture

The application is built on **Python's Tkinter** framework. It uses a strictly decoupled architecture to prevent GUI freezing during heavy AI operations.

### The "Thread-Safe" GUI Model
One of the critical challenges in Python GUIs (especially on macOS/Python 3.14) is that background threads cannot modify UI elements directly. Doing so causes the app to crash immediately.

**The Solution:**
We use a specific pattern: `Background Thread` -> `Main Thread Scheduler` -> `UI Update`.

* **Worker Threads:** All network calls (Uploads, API requests) happen in `daemon` threads.
* **The Bridge:** We use `root.after(0, callback)` to pass data from the worker thread back to the main loop.
* **Safe Methods:** Functions like `_safe_ui_update` ensure that no matter what the AI is doing, the interface remains responsive and crash-free.

## 2. The "Analyst Grade" Prompt Strategy

The application relies on an external file `transcription_prompt.txt`. This allows the user to modify instructions without touching the code.

### Delivery vs. Sentiment
Standard AI transcription offers "Sentiment" (Positive/Negative). This app was specifically engineered to ignore generic sentiment and focus on **Delivery**.

* **Instruction:** *"Delivery notes must be descriptive sentences, not one word."*
* **Goal:** To catch nuances like *"Candidate rushed through the list without pausing"* or *"Coach lowered voice to sound authoritative."*
* **Format:** Tags are enclosed in `[Delivery: ...]` to make them regex-searchable later if needed.

### The Chit-Chat Filter
To save tokens (and money), the prompt explicitly instructs the model to summarize pleasantries.
* **Prompt Command:** *"Summarize chit-chat (weather, connection checks) in italics."*
* **Result:** 5 minutes of "Can you hear me?" becomes `[Brief technical check]`.

## 3. File & Data Handling

### The Splitter Logic
The LLM returns a single stream of text. The application splits this into two distinct files using a "Marker Strategy."
1.  The Prompt forces the AI to print a header: `TASK 2: SESSION SUMMARY REPORT`.
2.  The Python script detects this string.
3.  **Part A** is saved as `_TRANSCRIPT.txt`.
4.  **Part B** is saved as `_SUMMARY.md`.

### Batch Processing & The CSV Database
Batch processing is asynchronous (fire-and-forget). To prevent losing track of jobs when the app is closed, we use `job_history.csv` as a persistent database.

* **Submission:** When a batch job is sent, the Google Job ID is saved to CSV with status `SUBMITTED`.
* **Retrieval:** When you click "Check Batch Statuses", the app reads the CSV, queries Google for only the `SUBMITTED` jobs, downloads the result if ready, and updates the CSV to `COMPLETED`.

## 4. Cost Optimization Tricks

* **Dynamic Model Fetching:** The app doesn't hardcode models. It queries the API for models supporting `generateContent`. This ensures that when Google releases a cheaper model (e.g., "Gemini 2.0 Flash Lite"), it automatically appears in your dropdown.
* **Batch API:** By implementing the specific JSONL (JSON Lines) format required for Google's Batch API, the app achieves a **50% discount** on token costs compared to standard calls.

## 5. Troubleshooting

### "Python Quit Unexpectedly"
* **Cause:** A background thread tried to update a Label or Listbox directly.
* **Fix:** Ensure you are using the `_safe_ui_update` wrapper for any visual changes.

### "403 Permission Denied"
* **Cause:** The API Key is invalid or does not have access to the selected model (some Preview models require specific access).
* **Fix:** Refresh the model list and try a standard model like `gemini-1.5-flash`.

### "Summary Not Found" in Output
* **Cause:** The AI hallucinated or skipped the specific header `TASK 2: SESSION SUMMARY REPORT`.
* **Fix:** The prompt file is editable. You can capitalize or repeat the instruction to make the header mandatory.