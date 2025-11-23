# **Project: Coach Words \- Intelligent Assistant for Coaching Session Transcription**

## **1\. Project Overview**

"Coach Words" is a desktop application designed to batch process long-form audio files (1-4 hours, .m4a/AAC) using the **Gemini 3.0 Pro** multimodal model. The app manages a queue of local audio files, sends them to the API with a dynamically constructed prompt, and saves the resulting artifacts (Rich Transcript, Summary, Fine Tuning data) back to the audio file's source directory.

## **2\. Tech Stack & Architecture**

* **Language:** Python 3.10+  
* **GUI Framework:** CustomTkinter (preferred for modern aesthetic) or PyQt6.  
* **AI API:** Google Generative AI SDK (google-generativeai) targeting model gemini-3.0-pro.  
* **Audio Handling:** ffmpeg-python or pydub (for duration/metadata extraction).  
* **Concurrency:** threading or asyncio (Crucial: UI must remain responsive during large file uploads/processing).  
* **Data Persistence:** JSON for Queue state management; .log for job history.

## **3\. Directory Structure**

/CoachWords  
│── /prompts  
│   ├── transcript\_prompt.md  
│   ├── summary\_prompt.md  
│   └── fine\_tuning\_prompt.md  
│── /jobs  
│   └── jobs.log  
│── /assets  
│   └── (icons for Play, Pause, Stop)  
│── main.py  
│── gui.py  
│── queue\_manager.py  
│── gemini\_worker.py  
└── logger.py

## **4\. Agent Roles & Responsibilities**

### **A. UI\_Agent (Front-End)**

**Responsibility:** Implement the Main Window based on the provided wireframe.  
**Specifications:**

* **Window Settings:** Title "Coach Words", fixed or resizable window.  
* **Row 1: Queue Management**  
  * Button: \[Queue\] (Opens Queue\_Window).  
  * Status Label: Dynamic text displaying "X done, Y ongoing, Z queued".  
* **Row 2: Operations & Feedback**  
  * Controls: Three distinct buttons with icons: \[Play\], \[Pause\], \[Stop\].  
  * Progress Label: Dynamic text area updating processing states: "Uploading (35%)", "Processing", "Fetching".  
* **Row 3: Configuration**  
  * Checkboxes:  
    * \[x\] Rich Transcript  
    * \[x\] Summary  
    * \[x\] Fine Tuning  
  * **Logic:** These checkboxes control which prompt files are loaded.

### **B. Queue\_Agent (Logic)**

**Responsibility:** Manage the Queue\_Window and file lists.  
**Specifications:**

* **Queue Window UI:** A separate modal/window invoked by the \[Queue\] button.  
* **Tabs:** "Pending/Queued" vs. "History/Completed".  
* **List View:** Shows File Name | Source Path | Duration.  
* **Actions:** Add Files (File Explorer), Remove Selected, Clear Queue.  
* **State Management:** Maintain a list of file objects. Each object tracks:  
  * status: (queued, processing, completed, failed).  
  * file\_path: (absolute path).  
  * output\_options: (which checkboxes were active when added).

### **C. Gemini\_Worker\_Agent (Back-End)**

**Responsibility:** Handle the API communication and Prompt Assembly.  
**Specifications:**

* **Prompt Assembly:**  
  * Check /prompts folder.  
  * Based on UI Checkboxes, concatenate content:  
    * IF Rich Transcript checked \-\> Add transcript\_prompt.md.  
    * IF Summary checked \-\> Add summary\_prompt.md.  
    * IF Fine Tuning checked \-\> Add fine\_tuning\_prompt.md.  
* **Instruction Injection:** Add a system instruction telling Gemini to separate these three outputs using specific delimiters (e.g., \#\#\#SECTION:TRANSCRIPT\#\#\#) so the app can parse them into separate files later.  
* **API Interaction:**  
  * Upload Audio File (handling 1-4hr m4a files via Gemini File API).  
  * Wait for file state ACTIVE (processing readiness).  
  * Send request with assembled prompt.  
* **Output Handling:**  
  * Parse response text.  
  * Write files to **Source Audio Directory**:  
    * \[filename\]\_transcript.md  
    * \[filename\]\_summary.md  
    * \[filename\]\_fine\_tuning.md

### **D. Control\_Agent (State Machine)**

**Responsibility:** Handle Play/Pause/Stop logic.

* **Play:** Start processing the first item in queue. When finished, automatically pick the next.  
* **Pause:** Finish the **currently processing** file, then stop the loop. Do not process the next file.  
* **Stop:** Abort current API call immediately (cancel request) and reset current file status to "Queued" or "Failed".

### **E. Logger\_Agent**

**Responsibility:** Write to /jobs/jobs.log.  
**Format:** Append new lines for every major event.  
**Parameters to Log:**

* Job\_ID (UUID)  
* Timestamp\_Start / Timestamp\_End  
* Source\_File\_Path  
* File\_Size\_MB  
* Duration\_Minutes  
* Input\_Tokens / Output\_Tokens (from API response metadata)  
* Processing\_Time\_Seconds  
* Status (Success/Fail)

## **5\. Implementation Flow (Step-by-Step)**

1. **Setup:** Create folders /prompts and /jobs. Create dummy .md files in prompts to test.  
2. **Core Logic:** Create the GeminiClient class that takes an audio path \+ prompt text and returns the result string.  
3. **UI Skeleton:** Build the Main Window using the drawing as a strict reference.  
4. **Queue System:** Implement the file picker and list data structure.  
5. **Integration:** Connect the \[Play\] button to the GeminiClient in a background thread.  
6. **Dynamic Feedback:** Connect thread signals to the UI "Status Label" (e.g., "Uploading...").  
7. **File IO:** Implement the response parser to split the AI output and save separate Markdown files.

### **Next Steps for the User**

1. Create the /prompts folder and populate it with your three draft prompts (transcript\_prompt.md, etc.).  
2. Obtain your Google GenAI API Key.  
3. Feed this AGENTS.md file along with the UI image to your coding assistant to generate the Python code.
