import os
import csv
import json
import time
import threading
import mimetypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import google.generativeai as genai

# --- CONFIGURATION ---
HISTORY_FILE = "job_history.csv"
DEFAULT_PROMPT_FILE = "transcription_prompt.txt"

# Estimated pricing descriptions
PRICING = {
    "gemini-2.0-flash-thinking-exp": "Reasoning & Speed (Preview)",
    "gemini-2.0-flash": "New Generation High Speed",
    "gemini-1.5-pro": "High Intelligence (Complex Tasks)",
    "gemini-1.5-flash": "High Efficiency (Volume Tasks)",
}

class GeminiCoachApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini Coach - Audio Analyst")
        self.root.geometry("1000x800")
        
        # --- DATA MODELS ---
        self.api_key_var = tk.StringVar(value=os.environ.get("GEMINI_API_KEY", ""))
        self.prompt_path_var = tk.StringVar(value=os.path.abspath(DEFAULT_PROMPT_FILE))
        self.model_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="BATCH")
        self.status_var = tk.StringVar(value="Ready")
        
        self.file_queue = [] 
        
        # --- UI SETUP ---
        self._setup_styles()
        self._build_ui()
        
        # --- INITIALIZATION ---
        self._init_csv()
        self._refresh_history_view()
        
        # Auto-connect if key exists
        if self.api_key_var.get():
            self._log("API Key found. Fetching models...")
            self._start_thread(self._fetch_models_worker, self.api_key_var.get())

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass # Fallback to default if clam isn't available
        style.configure("TButton", padding=6)
        style.configure("Accent.TButton", background="#007bff", foreground="white", font=('Helvetica', 10, 'bold'))
        style.map("Accent.TButton", background=[("active", "#0056b3")])
        style.configure("Header.TLabel", font=('Helvetica', 11, 'bold'))

    def _build_ui(self):
        # TOP CONFIGURATION
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=0, column=0, sticky="w", padx=5)
        self.api_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_entry.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Button(config_frame, text="Refresh Models", command=self._on_refresh_models_click).grid(row=0, column=2, padx=5)

        # Prompt File
        ttk.Label(config_frame, text="Prompt File:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.prompt_path_var, width=50).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Button(config_frame, text="Browse...", command=self._browse_prompt).grid(row=1, column=2, padx=5)

        # MAIN SPLIT
        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        # LEFT: CONTROLS
        left_frame = ttk.LabelFrame(paned, text="Job Controls", padding=10)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Select Model:", style="Header.TLabel").pack(anchor="w", pady=(0,5))
        self.model_menu = ttk.OptionMenu(left_frame, self.model_var, "Loading...")
        self.model_menu.pack(fill="x", pady=5)

        ttk.Label(left_frame, text="Processing Mode:", style="Header.TLabel").pack(anchor="w", pady=(15,5))
        ttk.Radiobutton(left_frame, text="Batch (50% Cost Savings)", variable=self.mode_var, value="BATCH").pack(anchor="w")
        ttk.Radiobutton(left_frame, text="Live (Immediate)", variable=self.mode_var, value="LIVE").pack(anchor="w")

        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", pady=20)

        self.run_btn = ttk.Button(left_frame, text="RUN QUEUE", style="Accent.TButton", command=self._on_run_click)
        self.run_btn.pack(fill="x", ipady=10)

        # RIGHT: QUEUE
        right_frame = ttk.LabelFrame(paned, text="Audio Queue", padding=10)
        paned.add(right_frame, weight=3)

        q_toolbar = ttk.Frame(right_frame)
        q_toolbar.pack(fill="x", pady=(0,5))
        ttk.Button(q_toolbar, text="+ Add Files", command=self._add_files).pack(side="left")
        ttk.Button(q_toolbar, text="Clear", command=self._clear_queue).pack(side="left", padx=5)

        self.queue_listbox = tk.Listbox(right_frame, height=8, selectmode="extended")
        self.queue_listbox.pack(fill="both", expand=True)

        # BOTTOM: HISTORY
        hist_frame = ttk.LabelFrame(self.root, text="History & Batch Status", padding=10)
        hist_frame.pack(fill="both", expand=True, padx=10, pady=5)

        h_toolbar = ttk.Frame(hist_frame)
        h_toolbar.pack(fill="x", pady=(0,5))
        ttk.Button(h_toolbar, text="Check Batch Statuses", command=self._on_check_batch_click).pack(side="right")

        cols = ("ID", "File", "Mode", "Status", "Time")
        self.tree = ttk.Treeview(hist_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("ID", text="Job ID")
        self.tree.heading("File", text="File")
        self.tree.heading("Mode", text="Mode")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Time", text="Timestamp")
        
        self.tree.column("ID", width=120)
        self.tree.column("File", width=250)
        self.tree.column("Mode", width=80)
        self.tree.column("Status", width=100)
        self.tree.column("Time", width=150)
        
        self.tree.pack(fill="both", expand=True)

        # STATUS BAR
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(fill="x", side="bottom")

    # --- THREAD HELPERS ---

    def _start_thread(self, target, *args):
        """Starts a daemon thread to prevent UI freezing."""
        threading.Thread(target=target, args=args, daemon=True).start()

    def _safe_ui_update(self, callback, *args):
        """Schedules a UI update on the main thread."""
        self.root.after(0, lambda: callback(*args))

    def _log(self, message):
        """Safely updates status bar from any thread."""
        self._safe_ui_update(self.status_var.set, message)

    # --- LOGIC: MODEL FETCHING ---

    def _on_refresh_models_click(self):
        key = self.api_key_var.get()
        if not key:
            messagebox.showerror("Error", "Please enter an API Key")
            return
        self._log("Fetching models...")
        self._start_thread(self._fetch_models_worker, key)

    def _fetch_models_worker(self, api_key):
        try:
            genai.configure(api_key=api_key)
            # Network call
            all_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Sort newer models to top
            all_models.sort(key=lambda x: x.name, reverse=True)
            
            # Prepare display names
            menu_items = []
            for m in all_models:
                desc = ""
                for k, v in PRICING.items():
                    if k in m.name:
                        desc = f" - {v}"
                        break
                menu_items.append((m.name, f"{m.display_name}{desc}"))
            
            # Schedule UI Update
            self._safe_ui_update(self._update_model_menu, menu_items)
            self._log(f"Loaded {len(menu_items)} models.")
        except Exception as e:
            self._log(f"Error fetching models: {e}")
            self._safe_ui_update(messagebox.showerror, "API Error", str(e))

    def _update_model_menu(self, items):
        menu = self.model_menu["menu"]
        menu.delete(0, "end")
        first = None
        for name, label in items:
            menu.add_command(label=label, command=lambda v=name: self.model_var.set(v))
            if not first: first = name
        
        if first and not self.model_var.get():
            self.model_var.set(first)

    # --- LOGIC: QUEUE PROCESSING ---

    def _on_run_click(self):
        if not self.file_queue:
            messagebox.showinfo("Empty Queue", "Add audio files first.")
            return
        if not self.model_var.get():
            messagebox.showerror("No Model", "Please select a model.")
            return
        
        # Lock UI
        self.run_btn.config(state="disabled")
        
        # Load prompt text
        prompt_txt = "Transcribe this audio."
        p_path = self.prompt_path_var.get()
        if os.path.exists(p_path):
            with open(p_path, "r", encoding="utf-8") as f:
                prompt_txt = f.read()
        
        # Start Worker
        self._start_thread(self._process_queue_worker, 
                           self.api_key_var.get(), 
                           self.model_var.get(), 
                           self.mode_var.get(), 
                           list(self.file_queue), # Copy list
                           prompt_txt)

    def _process_queue_worker(self, api_key, model_name, mode, files, prompt_text):
        genai.configure(api_key=api_key)
        client = genai.Client(api_key=api_key)

        for file_path in files:
            fname = os.path.basename(file_path)
            self._log(f"Processing {fname} ({mode})...")
            
            try:
                # 1. Upload
                self._log(f"Uploading {fname}...")
                mime = mimetypes.guess_type(file_path)[0] or "audio/ogg"
                
                # Upload
                audio_file = genai.upload_file(file_path, mime_type=mime)
                
                # Wait for processing
                while audio_file.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_file = genai.get_file(audio_file.name)
                
                if audio_file.state.name == "FAILED":
                    raise Exception("Google Processing Failed")

                # 2. Execution
                if mode == "BATCH":
                    self._log(f"Creating Batch Job for {fname}...")
                    
                    # Create JSONL
                    jsonl_path = f"temp_batch_{int(time.time())}.jsonl"
                    req = {
                        "request": {
                            "contents": [
                                {"role": "user", "parts": [{"text": prompt_text}, {"file_data": {"file_uri": audio_file.uri, "mime_type": mime}}]}
                            ]
                        }
                    }
                    with open(jsonl_path, "w") as f: f.write(json.dumps(req))
                    
                    batch_src = genai.upload_file(jsonl_path)
                    while batch_src.state.name == "PROCESSING": time.sleep(1)
                    
                    job = client.batches.create(
                        model=model_name,
                        src=batch_src.name,
                        config={"display_name": fname}
                    )
                    
                    # Cleanup & Log
                    os.remove(jsonl_path)
                    self._safe_ui_update(self._append_history, job.name, file_path, model_name, "BATCH", "SUBMITTED")

                else:
                    # Live Mode
                    self._log(f"Analyzing {fname} (Live)...")
                    self._safe_ui_update(self._append_history, "LIVE_SESSION", file_path, model_name, "LIVE", "PROCESSING")
                    
                    gen_model = genai.GenerativeModel(model_name)
                    response = gen_model.generate_content(
                        [prompt_text, audio_file],
                        request_options={"timeout": 3600} # 1 hour timeout for long files
                    )
                    
                    self._save_output(response.text, file_path)
                    self._log(f"Finished {fname}")
                    # Note: We don't easily update the specific row in history for Live mode in this simple implementation, 
                    # but we prevent the crash.
            
            except Exception as e:
                self._log(f"Error on {fname}: {e}")
                self._safe_ui_update(self._append_history, "ERROR", file_path, model_name, mode, "FAILED")

        self._log("Queue processing complete.")
        self._safe_ui_update(self._clear_queue_ui)
        self._safe_ui_update(lambda: self.run_btn.config(state="normal"))

    def _save_output(self, text, source_path):
        base = os.path.splitext(source_path)[0]
        
        # Splitter Logic
        transcript = text
        summary = "Summary not detected in output."
        
        # Keywords to split on
        markers = ["TASK 2: SESSION SUMMARY REPORT", "## SESSION SUMMARY", "**PART 2"]
        for m in markers:
            if m in text:
                parts = text.split(m)
                transcript = parts[0].replace("TASK 1: DIARIZED TRANSCRIPT", "").strip()
                summary = f"## SESSION SUMMARY\n{parts[1].strip()}"
                break
        
        with open(f"{base}_TRANSCRIPT.txt", "w", encoding="utf-8") as f: f.write(transcript)
        with open(f"{base}_SUMMARY.md", "w", encoding="utf-8") as f: f.write(summary)

    # --- LOGIC: BATCH CHECKING ---

    def _on_check_batch_click(self):
        self._log("Checking batch status...")
        self._start_thread(self._check_batch_worker, self.api_key_var.get())

    def _check_batch_worker(self, api_key):
        try:
            client = genai.Client(api_key=api_key)
            
            # Read CSV for pending jobs
            pending = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['Mode'] == 'BATCH' and row['Status'] == 'SUBMITTED':
                            pending.append(row)
            
            if not pending:
                self._log("No pending batch jobs found.")
                return

            updated_any = False
            for row in pending:
                jid = row['Job_ID']
                try:
                    self._log(f"Checking {jid}...")
                    remote = client.batches.get(jid)
                    state = remote.state.name
                    
                    if state == "COMPLETED":
                        self._log(f"Downloading {row['File_Name']}...")
                        for res in client.batches.complete(jid):
                            self._save_output(res.content.parts[0].text, row['File_Path'])
                        
                        self._safe_ui_update(self._update_csv_status, jid, "COMPLETED")
                        updated_any = True
                    
                    elif state == "FAILED":
                        self._safe_ui_update(self._update_csv_status, jid, "FAILED")
                        updated_any = True
                        
                except Exception as e:
                    print(f"Batch check error: {e}")

            self._log("Batch check complete.")
            if updated_any:
                self._safe_ui_update(self._refresh_history_view)

        except Exception as e:
            self._log(f"Error checking batches: {e}")

    # --- FILE & DATA HELPERS ---

    def _browse_prompt(self):
        f = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if f: self.prompt_path_var.set(f)

    def _add_files(self):
        fs = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a *.flac")])
        for f in fs:
            if f not in self.file_queue:
                self.file_queue.append(f)
                self.queue_listbox.insert("end", os.path.basename(f))

    def _clear_queue(self):
        self.file_queue.clear()
        self.queue_listbox.delete(0, "end")

    def _clear_queue_ui(self):
        self._clear_queue()

    # --- CSV HELPERS ---

    def _init_csv(self):
        if not os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Job_ID", "File_Name", "File_Path", "Model", "Mode", "Status", "Timestamp"])

    def _append_history(self, jid, fpath, model, mode, status):
        with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([jid, os.path.basename(fpath), fpath, model, mode, status, datetime.now().isoformat()])
        self._refresh_history_view()

    def _update_csv_status(self, target_id, new_status):
        rows = []
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        
        for row in rows:
            if row[0] == target_id:
                row[5] = new_status
        
        with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        self._refresh_history_view()

    def _refresh_history_view(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Reverse order (newest top)
                        self.tree.insert("", 0, values=(row['Job_ID'], row['File_Name'], row['Mode'], row['Status'], row['Timestamp']))
            except:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiCoachApp(root)
    root.mainloop()