"""Tkinter/ttkbootstrap GUI for the threat generation tool."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import List, Optional, Union
import tkinter as tk
from tkinter import filedialog, messagebox, PhotoImage

import ttkbootstrap as ttk
from ttkbootstrap.constants import PRIMARY, SECONDARY, SUCCESS
from dotenv import load_dotenv

from ai_client import AIClientOptions
from runtime import ASSETS_DIR, PROJECT_ROOT, RuntimeConfig, run_threat_modeling


class ThreatGUI:
    def __init__(self, root: ttk.Window):
        self.root = root
        self._icon_ico_path: Optional[Path] = None
        self._icon_images: List[PhotoImage] = []
        self.root.title("Threat Dragon Threats & Mitigations Generator")
        self.root.geometry("1200x670")
        self._set_app_icons()

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.model_path = tk.StringVar(value="")
        self.model_file: Optional[Path] = None
        self.model_data = None

        self._running = False
        self._load_defaults_from_env()

        self._setup_style()
        self._build_menu()
        self._build_layout()

    def _set_app_icons(self) -> None:
        self._icon_ico_path = ASSETS_DIR / "favicon.ico"
        self._icon_images = []
        for size in [16, 32, 48, 64, 96, 128]:
            icon_path = ASSETS_DIR / f"favicon-{size}x{size}.png"
            if icon_path.exists():
                self._icon_images.append(PhotoImage(file=icon_path.as_posix()))

        self._apply_window_icon(self.root)

    def _apply_window_icon(self, window: Union[tk.Tk, tk.Toplevel]) -> None:
        if sys.platform.startswith("win"):
            if self._icon_ico_path and self._icon_ico_path.exists():
                window.iconbitmap(self._icon_ico_path.as_posix())
        if self._icon_images:
            # True applies to this window and future toplevel windows on Tk.
            window.iconphoto(True, *self._icon_images)

    def _load_defaults_from_env(self) -> None:
        # Load startup defaults from app-root .env (if present).
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
        default_model = os.getenv("LLM_MODEL_NAME", "")
        default_timeout = os.getenv("THREAT_TIMEOUT", "900")
        default_schema = os.getenv("THREAT_SCHEMA_JSON", "owasp.threat-dragon.schema.V2.json")

        self.default_schema_path = ASSETS_DIR / default_schema
        self.settings_vars = {
            "apiKey": tk.StringVar(value=""),
            "llmModel": tk.StringVar(value=default_model),
            "temperature": tk.StringVar(value="0.1"),
            "responseFormat": tk.BooleanVar(value=True),
            "apiBase": tk.StringVar(value=""),
            "logLevel": tk.StringVar(value="INFO"),
            "timeout": tk.StringVar(value=default_timeout),
        }

        api_key = (os.getenv("API_KEY") or "").strip()
        if api_key:
            self.settings_vars["apiKey"].set(api_key)

        llm_model = (os.getenv("LLM_MODEL") or "").strip()
        if llm_model:
            self.settings_vars["llmModel"].set(llm_model)

        temperature = (os.getenv("TEMPERATURE") or "").strip()
        if temperature:
            try:
                temp_value = float(temperature)
                if 0.0 <= temp_value <= 2.0:
                    self.settings_vars["temperature"].set(temperature)
            except ValueError:
                pass

        response_format = (os.getenv("RESPONSE_FORMAT") or "").strip().lower()
        if response_format in {"1", "true", "yes", "on"}:
            self.settings_vars["responseFormat"].set(True)
        elif response_format in {"0", "false", "no", "off"}:
            self.settings_vars["responseFormat"].set(False)

        api_base_url = (os.getenv("API_BASE_URL") or "").strip()
        if api_base_url:
            self.settings_vars["apiBase"].set(api_base_url)

        log_level = (os.getenv("LOG_LEVEL") or "").strip().upper()
        if log_level in {"INFO", "DEBUG"}:
            self.settings_vars["logLevel"].set(log_level)

        timeout = (os.getenv("TIMEOUT") or "").strip()
        if timeout.isdigit() and int(timeout) >= 1:
            self.settings_vars["timeout"].set(timeout)

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.configure("TFrame", padding=0)
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Model (.json)", command=self.open_model)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Generate Threat & Mitigation", command=self.run_main_script)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Run", menu=run_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_layout(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1, minsize=600)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)

        left = ttk.Frame(main_frame)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=5, pady=5)
        left.columnconfigure(0, weight=1)

        logo_frame = ttk.Frame(left, padding=10)
        logo_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        row = ttk.Frame(logo_frame)
        row.pack(anchor="w")

        self.logo_img = self._try_load_logo("assets/logo-infosecotb.png", subsample=3)
        self.td_logo = self._try_load_logo("assets/threat-dragon-logo.png", subsample=3)

        if self.logo_img:
            ttk.Label(row, image=self.logo_img).pack(side="left", padx=(0, 8))
        if self.td_logo:
            ttk.Label(row, image=self.td_logo).pack(side="left")

        settings_frame = ttk.Labelframe(left, text="SETTINGS", padding=10)
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        settings_frame.columnconfigure(0, weight=0)
        settings_frame.columnconfigure(1, weight=1, minsize=280)

        api_key_maxlen = 1280

        def validate_api_key(action: str, value: str) -> bool:
            if action == "0":  # delete
                return True
            return len(value) <= api_key_maxlen

        def validate_temperature(action: str, value: str) -> bool:
            if action == "0" or value == "":
                return True
            try:
                number = float(value)
            except ValueError:
                return False
            return 0.0 <= number <= 2.0

        def validate_timeout(action: str, value: str) -> bool:
            if action == "0" or value == "":
                return True
            return value.isdigit() and int(value) >= 1

        vcmd_api_key = (self.root.register(validate_api_key), "%d", "%P")
        vcmd_temp = (self.root.register(validate_temperature), "%d", "%P")
        vcmd_timeout = (self.root.register(validate_timeout), "%d", "%P")

        settings_fields = [
            ("LLM Model", "entry", self.settings_vars["llmModel"], None),
            ("Temperature (0-2)", "entry", self.settings_vars["temperature"], vcmd_temp),
            ("Response Format", "checkbox", self.settings_vars["responseFormat"], None),
            ("API Base URL", "entry", self.settings_vars["apiBase"], None),
            ("Log Level", "dropdown", self.settings_vars["logLevel"], ["INFO", "DEBUG"]),
            ("Timeout (seconds)", "entry", self.settings_vars["timeout"], vcmd_timeout),
        ]

        row_index = 0
        ttk.Label(settings_frame, text="API Key").grid(
            row=row_index, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        self.api_key_entry = ttk.Entry(
            settings_frame,
            textvariable=self.settings_vars["apiKey"],
            show="*",
            validate="key",
            validatecommand=vcmd_api_key,
        )
        self.api_key_entry.grid(row=row_index, column=1, sticky="ew", pady=4)
        self._attach_text_context_menu(self.api_key_entry)

        self._api_key_visible = False

        def toggle_api_key_visibility() -> None:
            self._api_key_visible = not self._api_key_visible
            self.api_key_entry.config(show="" if self._api_key_visible else "*")
            toggle_btn.config(text="Hide" if self._api_key_visible else "Show")

        toggle_btn = ttk.Button(
            settings_frame,
            text="Show",
            width=5,
            command=toggle_api_key_visibility,
            bootstyle="link",
            takefocus=False,
        )
        toggle_btn.grid(row=row_index, column=2, sticky="e", padx=4)
        row_index += 1

        for label_text, field_type, var, extra in settings_fields:
            ttk.Label(settings_frame, text=label_text).grid(
                row=row_index, column=0, sticky="w", pady=4, padx=(0, 8)
            )

            if field_type == "entry":
                entry = ttk.Entry(
                    settings_frame,
                    textvariable=var,
                    validate="key",
                    validatecommand=extra if extra else None,
                )
                entry.grid(row=row_index, column=1, sticky="ew", pady=4)
                self._attach_text_context_menu(entry)

            elif field_type == "checkbox":
                ttk.Checkbutton(settings_frame, variable=var, onvalue=True, offvalue=False).grid(
                    row=row_index, column=1, sticky="w", pady=4
                )

            elif field_type == "dropdown":
                dropdown = ttk.Combobox(
                    settings_frame,
                    textvariable=var,
                    values=extra,
                    state="readonly",
                )
                dropdown.grid(row=row_index, column=1, sticky="ew", pady=4)

            row_index += 1

        open_frame = ttk.Frame(left, padding=(0, 10, 0, 0))
        open_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        open_frame.columnconfigure(1, weight=1)

        ttk.Button(open_frame, text="Open Model", bootstyle=PRIMARY, command=self.open_model).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(open_frame, textvariable=self.model_path, bootstyle=SECONDARY).grid(
            row=0, column=1, sticky="ew", padx=(10, 0)
        )

        generate_frame = ttk.Frame(left)
        generate_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        generate_frame.columnconfigure(0, weight=1)
        self.run_button = ttk.Button(
            generate_frame,
            text="Generate Threat and Mitigations",
            bootstyle=SUCCESS,
            command=self.run_main_script,
        )
        self.run_button.grid(row=0, column=0, sticky="ew")
        ttk.Button(
            generate_frame,
            text="Clear Console",
            bootstyle=SECONDARY,
            command=self.clear_console,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

        console_frame = ttk.Frame(main_frame, padding=10)
        console_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        console_frame.rowconfigure(0, weight=1)
        console_frame.columnconfigure(0, weight=1)

        self.console = tk.Text(console_frame, wrap="word", undo=True)
        scrollbar = ttk.Scrollbar(console_frame, command=self.console.yview)
        self.console.configure(yscrollcommand=scrollbar.set)
        self.console.grid(row=0, column=0, sticky="nsew")
        self.console.configure(state="disabled")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._attach_text_context_menu(self.console, allow_paste=False, allow_cut=False)

    def _try_load_logo(self, relative_path: str, subsample: int = 1):
        logo_path = PROJECT_ROOT / relative_path
        try:
            raw = tk.PhotoImage(file=str(logo_path))
            return raw.subsample(subsample, subsample) if subsample > 1 else raw
        except Exception:
            return None

    def _attach_text_context_menu(self, widget, allow_paste: bool = True, allow_cut: bool = True) -> None:
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        if allow_paste:
            menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        if allow_cut:
            menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_separator()

        if isinstance(widget, tk.Text):
            menu.add_command(
                label="Select All",
                command=lambda: widget.tag_add("sel", "1.0", "end-1c"),
            )
            widget.bind("<Control-a>", lambda e: (widget.tag_add("sel", "1.0", "end-1c"), "break"))
        else:
            menu.add_command(label="Select All", command=lambda: widget.select_range(0, "end"))

        def show_menu(event) -> None:
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Button-3>", show_menu)

    def _append_console(self, text: str) -> None:
        self.console.configure(state="normal")
        self.console.insert("end", f"{text}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def clear_console(self) -> None:
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _log(self, text: str) -> None:
        # Always marshal to the UI thread.
        self.root.after(0, lambda: self._append_console(text))

    def _set_api_env(self, model_name: str, api_key: str) -> None:
        if not api_key.strip():
            return

        provider = model_name.split("/", 1)[0].lower() if "/" in model_name else ""
        provider_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "xai": "XAI_API_KEY",
            "novita": "NOVITA_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_name = provider_map.get(provider, "OPENAI_API_KEY")
        os.environ[env_name] = api_key
        os.environ["LITELLM_API_KEY"] = api_key

    def open_model(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select model JSON",
            filetypes=[("JSON files", "*.json")],
        )
        if not file_path:
            return

        selected = Path(file_path)
        try:
            with selected.open("r", encoding="utf-8") as file:
                self.model_data = json.load(file)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return

        self.model_file = selected
        self.model_path.set(str(selected))
        self._append_console(f"Loaded model: {selected}")

    def show_about(self) -> None:
        about = tk.Toplevel(self.root)
        about.title("About")
        about.transient(self.root)
        about.resizable(False, False)
        self._apply_window_icon(about)

        container = ttk.Frame(about, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            container,
            text="Threat & Mitigation Generator",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(
            container,
            text="Created by Piotr Kowalczyk\ninfosecotb.com",
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))
        ttk.Button(container, text="OK", command=about.destroy).grid(row=2, column=0, sticky="e")

        about.grab_set()
        about.focus_set()

    def _build_runtime_config(self) -> RuntimeConfig:
        if not self.model_file:
            raise ValueError("Please load a threat model JSON first.")
        if not self.settings_vars["llmModel"].get().strip():
            raise ValueError("LLM model is required.")

        timeout_str = self.settings_vars["timeout"].get().strip()
        temp_str = self.settings_vars["temperature"].get().strip()

        timeout = int(timeout_str) if timeout_str else 900
        temperature = float(temp_str) if temp_str else 0.1

        log_level_name = self.settings_vars["logLevel"].get().strip().upper() or "INFO"
        log_level = getattr(logging, log_level_name, logging.INFO)

        ai_options = AIClientOptions(
            temperature=temperature,
            response_format=self.settings_vars["responseFormat"].get(),
            api_base=self.settings_vars["apiBase"].get().strip() or None,
            timeout=timeout,
        )

        return RuntimeConfig(
            llm_model=self.settings_vars["llmModel"].get().strip(),
            schema_path=self.default_schema_path,
            model_path=self.model_file,
            model_file_label=self.model_file.name,
            log_level=log_level,
            ai_options=ai_options,
        )

    def run_main_script(self) -> None:
        if self._running:
            return

        try:
            config = self._build_runtime_config()
            self._set_api_env(config.llm_model, self.settings_vars["apiKey"].get())
        except Exception as exc:
            messagebox.showerror("Invalid Configuration", str(exc))
            return

        self._running = True
        self.run_button.configure(state="disabled")
        self._append_console("=" * 60)
        self._append_console("Starting generation...")

        def worker() -> None:
            try:
                run_threat_modeling(config, log_callback=self._log)
                self._log("Generation completed.")
            except Exception as exc:
                self._log(f"Error: {exc}")
            finally:
                self.root.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self) -> None:
        self._running = False
        self.run_button.configure(state="normal")
        self._append_console("=" * 60)


def start_gui() -> None:
    """Launch the desktop GUI application."""
    root = ttk.Window(themename="flatly")
    ThreatGUI(root)
    root.mainloop()


if __name__ == "__main__":
    start_gui()
