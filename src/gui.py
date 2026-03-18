"""Desktop GUI for the threat generation tool."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import tkinter as tk
from tkinter import filedialog, messagebox, PhotoImage

import keyring
from keyring.errors import KeyringError, PasswordDeleteError
import ttkbootstrap as ttk
from ttkbootstrap.constants import PRIMARY, SECONDARY, SUCCESS
from ttkbootstrap.style import PRIMARY

from app_paths import ASSETS_DIR, CONFIG_FILE
from runtime import RuntimeConfig, run_threat_modeling

APP_NAME = "Threat Dragon AI Tool"
APP_VERSION = "1.0.1"
DOCS_URL = "https://github.com/InfosecOTB/threat-dragon-ai-tool"
BLOG_URL = "https://infosecotb.com"
THREAT_DRAGON_DOCS_URL = "https://www.threatdragon.com/docs"
ISSUES_URL = "https://github.com/InfosecOTB/threat-dragon-ai-tool/issues/new"
KEYRING_SERVICE = "threat-dragon-ai-tool"
KEYRING_USERNAME = "api_key"


class ThreatGUI:
    def __init__(self, root: ttk.Window):
        self.root = root
        self._icon_ico_path: Optional[Path] = None
        self._icon_images: List[PhotoImage] = []
        self._saved_config_state: Dict[str, Any] = {}
        self._setting_description_popup: Optional[tk.Toplevel] = None
        self._setting_description_popup_label: Optional[ttk.Label] = None
        self.root.title("Threat Dragon AI Threats & Mitigations Generator")
        self.root.geometry("1200x780")
        self._set_app_icons()

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.model_path = tk.StringVar(value="")
        self.model_file: Optional[Path] = None

        self._running = False
        self._console_inline_progress = False
        self._load_defaults_from_config()
        self._saved_config_state = self._collect_config_state()

        self._setup_style()
        self._build_menu()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit_request)

    def _set_app_icons(self) -> None:
        self._icon_ico_path = ASSETS_DIR / "favicon.ico"
        self._icon_images = []
        for size in [16, 32, 48, 64, 96, 128, 256, 512]:
            icon_path = ASSETS_DIR / f"favicon-{size}x{size}.png"
            if icon_path.exists():
                self._icon_images.append(PhotoImage(file=icon_path.as_posix()))

        self._apply_window_icon(self.root)

    def _apply_window_icon(self, window: Union[tk.Tk, tk.Toplevel]) -> None:
        if sys.platform.startswith("win"):
            if self._icon_ico_path and self._icon_ico_path.exists():
                window.iconbitmap(self._icon_ico_path.as_posix())
        if self._icon_images:
            # Apply the icon to this window and future toplevel windows.
            window.iconphoto(True, *self._icon_images)

    def _load_defaults_from_config(self) -> None:
        default_schema = "owasp.threat-dragon.schema.V2.json"
        self.default_schema_path = ASSETS_DIR / default_schema
        self.settings_vars = {
            "apiKey": tk.StringVar(value=""),
            "llmModel": tk.StringVar(value=""),
            "temperature": tk.StringVar(value="0.1"),
            "responseFormat": tk.BooleanVar(value=False),
            "apiBase": tk.StringVar(value=""),
            "logLevel": tk.StringVar(value="INFO"),
            "timeout": tk.StringVar(value="900"),
        }

        config_data = self._read_config_json()
        if config_data:
            self._apply_config(config_data)

        self._load_api_key_from_keyring()

    def _read_config_json(self) -> Dict[str, Any]:
        if not CONFIG_FILE.exists():
            return {}

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception as exc:
            messagebox.showwarning(
                "Config Warning",
                f"Could not read config file:\n{CONFIG_FILE}\n\n{exc}",
                parent=self.root,
            )
            return {}

        if not isinstance(payload, dict):
            messagebox.showwarning(
                "Config Warning",
                f"Config file must contain a JSON object:\n{CONFIG_FILE}",
                parent=self.root,
            )
            return {}

        return payload

    def _apply_config(self, payload: Dict[str, Any]) -> None:
        llm_model = str(payload.get("llmModel", "")).strip()
        if llm_model:
            self.settings_vars["llmModel"].set(llm_model)

        temperature = str(payload.get("temperature", "")).strip()
        if temperature:
            try:
                temp_value = float(temperature)
                if 0.0 <= temp_value <= 2.0:
                    self.settings_vars["temperature"].set(str(temp_value))
            except ValueError:
                pass

        if "responseFormat" in payload:
            response_format = payload["responseFormat"]
            if isinstance(response_format, bool):
                self.settings_vars["responseFormat"].set(response_format)
            elif isinstance(response_format, str):
                normalized = response_format.strip().lower()
                if normalized in {"1", "true", "yes", "on"}:
                    self.settings_vars["responseFormat"].set(True)
                elif normalized in {"0", "false", "no", "off"}:
                    self.settings_vars["responseFormat"].set(False)

        api_base = str(payload.get("apiBase", "")).strip()
        if api_base:
            self.settings_vars["apiBase"].set(api_base)

        log_level = str(payload.get("logLevel", "")).strip().upper()
        if log_level in {"INFO", "DEBUG"}:
            self.settings_vars["logLevel"].set(log_level)

        timeout = str(payload.get("timeout", "")).strip()
        if timeout.isdigit() and int(timeout) >= 1:
            self.settings_vars["timeout"].set(timeout)

    def _load_api_key_from_keyring(self) -> None:
        try:
            api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) or ""
        except KeyringError as exc:
            messagebox.showwarning(
                "Keyring Warning",
                (
                    "Could not load API key from the OS secure store.\n"
                    f"{exc}"
                ),
                parent=self.root,
            )
            return
        self.settings_vars["apiKey"].set(api_key)

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
        file_menu.add_command(label="Exit", command=self.on_exit_request)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Generate Threat & Mitigation", command=self.run_main_script)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="AI Tool Documentation", command=self.open_documentation)
        help_menu.add_command(
            label="Threat Dragon Documentation",
            command=self.open_threat_dragon_documentation,
        )
        help_menu.add_command(label="Submit an issue", command=self.open_issue_submission)
        help_menu.add_command(label="Blog", command=self.open_blog)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Run", menu=run_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_layout(self) -> None:
        left_column_min_width = 380
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        # Keep the left column width stable while resizing the window.
        main_frame.columnconfigure(0, weight=0, minsize=left_column_min_width)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)

        left = ttk.Frame(main_frame)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=5, pady=5)
        left.configure(width=left_column_min_width)
        left.columnconfigure(0, weight=1)

        logo_frame = ttk.Frame(left, padding=10)
        logo_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        row = ttk.Frame(logo_frame)
        row.pack(anchor="w")

        self.logo_img = self._try_load_logo("logo-infosecotb.png", subsample=3)
        self.td_logo = self._try_load_logo("threat-dragon-logo.png", subsample=3)

        if self.logo_img:
            ttk.Label(row, image=self.logo_img).pack(side="left", padx=(0, 8))
        if self.td_logo:
            ttk.Label(row, image=self.td_logo).pack(side="left")

        settings_frame = ttk.Labelframe(left, text="SETTINGS", padding=10)
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        settings_frame.columnconfigure(0, weight=0)
        settings_frame.columnconfigure(1, weight=1, minsize=240)

        api_key_maxlen = 1280

        def validate_api_key(action: str, value: str) -> bool:
            # Tk sends action "0" when the edit is a deletion.
            if action == "0":
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

        setting_descriptions = {
            "API Key": 'API key for accessing the LLM service',
            "LLM Model": 'LLM model identifier in the format "provider/model" (e.g., "openai/gpt-5", "anthropic/claude-sonnet-4-5", "xai/grok-4")',
            "Temperature (0-2)": 'Temperature parameter for LLM - lower values make output more deterministic, higher values increase creativity and randomness (range: 0-2)',
            "Response Format": 'Enables structured JSON output. Recommended for supported models such as openai/gpt-5 or xai/grok-4. If enabled for an unsupported model, the request may fail.',
            "API Base URL": 'Custom API base URL. Most hosted AI providers do not require this because LiteLLM handles it automatically.',
            "Log Level": 'Logging level (INFO or DEBUG)',
            "Timeout (seconds)": 'Request timeout in seconds for LLM API calls (default: 900 seconds = 15 minutes)',
        }

        settings_fields = [
            ("LLM Model", "entry", self.settings_vars["llmModel"], None),
            ("Temperature (0-2)", "entry", self.settings_vars["temperature"], vcmd_temp),
            ("Response Format", "checkbox", self.settings_vars["responseFormat"], None),
            ("API Base URL", "entry", self.settings_vars["apiBase"], None),
            ("Log Level", "dropdown", self.settings_vars["logLevel"], ["INFO", "DEBUG"]),
            ("Timeout (seconds)", "entry", self.settings_vars["timeout"], vcmd_timeout),
        ]

        row_index = 0
        self._create_setting_title(
            settings_frame, row_index, "API Key", setting_descriptions["API Key"]
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
            self._create_setting_title(
                settings_frame,
                row_index,
                label_text,
                setting_descriptions[label_text],
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
                checkbox = ttk.Checkbutton(
                    settings_frame, variable=var, onvalue=True, offvalue=False
                )
                checkbox.grid(
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

        ttk.Button(open_frame, text="Open Model", bootstyle="info", command=self.open_model).grid(
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
            bootstyle="info",
            command=self.clear_console,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(
            generate_frame,
            text="Save Config",
            bootstyle="info",
            command=self.save_config,
        ).grid(row=2, column=0, sticky="ew", pady=(6, 0))

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

    def _try_load_logo(self, asset_name: str, subsample: int = 1):
        logo_path = ASSETS_DIR / asset_name
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
            widget.bind("<Command-a>", lambda e: (widget.tag_add("sel", "1.0", "end-1c"), "break"))
        else:
            menu.add_command(label="Select All", command=lambda: widget.select_range(0, "end"))
            widget.bind("<Command-a>", lambda e: (widget.select_range(0, "end"), "break"))

        def show_menu(event) -> str:
            try:
                widget.focus_set()
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"

        # On Linux/X11, opening popup on button press can make it close on release.
        # Binding release events keeps the menu open consistently.
        widget.bind("<ButtonRelease-2>", show_menu)
        widget.bind("<ButtonRelease-3>", show_menu)
        widget.bind("<Control-ButtonRelease-1>", show_menu)

    def _create_setting_title(
        self,
        parent: tk.Widget,
        row_index: int,
        title: str,
        description: str,
    ) -> None:
        title_frame = ttk.Frame(parent)
        title_frame.grid(row=row_index, column=0, sticky="w", pady=4, padx=(0, 8))

        style = ttk.Style()
        frame_bg = style.lookup("TFrame", "background") or self.root.cget("bg")
        info_blue = getattr(getattr(style, "colors", None), "info", "#0D6EFD")
        info_icon = tk.Canvas(
            title_frame,
            width=12,
            height=12,
            highlightthickness=0,
            bd=0,
            bg=frame_bg,
            cursor="hand2",
        )
        info_icon.create_oval(1, 1, 11, 11, fill=info_blue, outline=info_blue)
        info_icon.create_text(6, 6, text="i", fill="white", font=("Segoe UI", 7, "bold"))
        info_icon.pack(side="left", padx=(0, 6))
        self._bind_setting_description(info_icon, description)

        ttk.Label(title_frame, text=title).pack(side="left")

    def _bind_setting_description(self, widget: tk.Widget, description: str) -> None:
        widget.bind(
            "<Enter>",
            lambda event: self._show_setting_description(description, event),
            add="+",
        )
        widget.bind(
            "<Motion>",
            lambda event: self._move_setting_description(event),
            add="+",
        )
        widget.bind("<Leave>", lambda _event: self._clear_setting_description(), add="+")

    def _show_setting_description(self, description: str, event: tk.Event) -> None:
        if self._setting_description_popup is None:
            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            label = ttk.Label(
                popup,
                text=description,
                justify="left",
                wraplength=460,
                padding=(8, 6),
                bootstyle=PRIMARY,
            )
            label.pack()
            self._setting_description_popup = popup
            self._setting_description_popup_label = label
        elif self._setting_description_popup_label is not None:
            self._setting_description_popup_label.configure(text=description)

        self._move_setting_description(event)

    def _move_setting_description(self, event: tk.Event) -> None:
        if self._setting_description_popup is None:
            return
        x = event.x_root + 14
        y = event.y_root + 20
        self._setting_description_popup.geometry(f"+{x}+{y}")

    def _clear_setting_description(self) -> None:
        if self._setting_description_popup is not None:
            self._setting_description_popup.destroy()
            self._setting_description_popup = None
            self._setting_description_popup_label = None

    def _append_console(self, text: str) -> None:
        self.console.configure(state="normal")
        if text.startswith("\r"):
            inline_text = text[1:]
            if self._console_inline_progress:
                line_start = self.console.index("end-1c linestart")
                line_end = self.console.index("end-1c lineend")
                self.console.delete(line_start, line_end)
                self.console.insert(line_start, inline_text)
            else:
                self.console.insert("end", inline_text)
                self._console_inline_progress = True
        else:
            if self._console_inline_progress:
                self.console.insert("end", "\n")
                self._console_inline_progress = False
            self.console.insert("end", f"{text}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def clear_console(self) -> None:
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self._console_inline_progress = False
        self.console.configure(state="disabled")

    def _log(self, text: str) -> None:
        # UI updates must run on the Tk main thread.
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
                json.load(file)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return

        self.model_file = selected
        self.model_path.set(str(selected))
        self._append_console(f"Loaded model: {selected}")

    def show_about(self) -> None:
        messagebox.showinfo(
            "About",
            (
                f"{APP_NAME}\n"
                f"Version {APP_VERSION}\n\n"
                "Desktop application for generating STRIDE threats and mitigations "
                "for OWASP Threat Dragon models using LLMs.\n\n"
                "License: Apache License 2.0\n"
                "Created by Piotr Kowalczyk\n"
                "\n"
                "Special Thanks\n"
                "A special thanks to Jon Gadsden and Leo lreading from the OWASP Threat Dragon community for their support and encouragement.\n"
                "\n"
                f"{BLOG_URL}"
            ),
            parent=self.root,
        )

    def _open_external_link(self, url: str, label: str) -> None:
        try:
            webbrowser.open(url, new=2)
        except Exception as exc:
            messagebox.showerror(
                "Error",
                f"Unable to open {label}.\n\n{exc}",
                parent=self.root,
            )

    def open_documentation(self) -> None:
        self._open_external_link(DOCS_URL, "documentation")

    def open_threat_dragon_documentation(self) -> None:
        self._open_external_link(THREAT_DRAGON_DOCS_URL, "Threat Dragon documentation")

    def open_issue_submission(self) -> None:
        self._open_external_link(ISSUES_URL, "issue submission page")

    def open_blog(self) -> None:
        self._open_external_link(BLOG_URL, "blog")

    def _show_generation_warning(self) -> bool:
        warning_text = (
            "IMPORTANT: Please read before you continue.\n\n"
            "* Make sure the Threat Dragon application is closed before updating the JSON file, as editing it while open may cause data loss.\n\n"
            "* Generating Threats and Mitigations sends the entire Threat Model to the selected AI for analysis as part of the prompt. Please review any security or privacy implications.\n\n"
            "* Currently, only the STRIDE methodology is supported. Using this tool with threat models based on other methodologies may lead to unexpected results.\n\n"
            "* Existing Threats and Mitigations will be reviewed and may be kept, updated, or removed by the AI. Consider taking a backup of your Threat Model file before continuing.\n\n"
            "* You can run the Generating Threats and Mitigations process multiple times with the same or different AI service. Each run will re-evaluate current items and may add new ones.\n\n"
            "Click Cancel to stop or OK to continue."
        )
        return messagebox.askokcancel(
            "Warning",
            warning_text,
            icon="warning",
            parent=self.root,
            default=messagebox.CANCEL,
        )

    def _parse_temperature(self) -> float:
        temperature_str = self.settings_vars["temperature"].get().strip()
        if not temperature_str:
            return 0.1
        temperature = float(temperature_str)
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("Temperature must be between 0 and 2.")
        return temperature

    def _parse_timeout(self) -> int:
        timeout_str = self.settings_vars["timeout"].get().strip()
        if not timeout_str:
            return 900
        timeout = int(timeout_str)
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second.")
        return timeout

    def _build_config_payload(self) -> Dict[str, Any]:
        return {
            "llmModel": self.settings_vars["llmModel"].get().strip(),
            "temperature": self._parse_temperature(),
            "responseFormat": self.settings_vars["responseFormat"].get(),
            "apiBase": self.settings_vars["apiBase"].get().strip(),
            "logLevel": self.settings_vars["logLevel"].get().strip().upper() or "INFO",
            "timeout": self._parse_timeout(),
        }

    def _save_api_key_to_keyring(self, api_key: str) -> None:
        if api_key:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)
            return

        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except PasswordDeleteError:
            # No previously saved key; nothing to remove.
            pass

    def _collect_config_state(self) -> Dict[str, Any]:
        return {
            "llmModel": self.settings_vars["llmModel"].get().strip(),
            "temperature": self.settings_vars["temperature"].get().strip(),
            "responseFormat": bool(self.settings_vars["responseFormat"].get()),
            "apiBase": self.settings_vars["apiBase"].get().strip(),
            "logLevel": self.settings_vars["logLevel"].get().strip().upper(),
            "timeout": self.settings_vars["timeout"].get().strip(),
            "apiKey": self.settings_vars["apiKey"].get().strip(),
        }

    def _has_unsaved_config_changes(self) -> bool:
        return self._collect_config_state() != self._saved_config_state

    def save_config(self) -> None:
        try:
            payload = self._build_config_payload()
        except Exception as exc:
            messagebox.showerror("Invalid Configuration", str(exc), parent=self.root)
            return

        api_key = self.settings_vars["apiKey"].get().strip()

        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with CONFIG_FILE.open("w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
            self._save_api_key_to_keyring(api_key)
        except KeyringError as exc:
            messagebox.showerror(
                "Save Error",
                (
                    f"Config file was saved to:\n{CONFIG_FILE}\n\n"
                    "But API key could not be saved in the OS secure store:\n"
                    f"{exc}"
                ),
                parent=self.root,
            )
            return
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc), parent=self.root)
            return

        api_key_status = (
            "API key saved in OS secure store."
            if api_key
            else "API key removed from OS secure store."
        )
        self._append_console(f"Configuration saved to: {CONFIG_FILE} | {api_key_status}")
        self._saved_config_state = self._collect_config_state()
        messagebox.showinfo(
            "Configuration Saved",
            f"Configuration saved to:\n{CONFIG_FILE}\n\n{api_key_status}",
            parent=self.root,
        )

    def _build_runtime_config(self) -> RuntimeConfig:
        if not self.model_file:
            raise ValueError("Please load a threat model JSON first.")
        if not self.settings_vars["llmModel"].get().strip():
            raise ValueError("LLM model is required.")
        timeout = self._parse_timeout()
        temperature = self._parse_temperature()

        log_level_name = self.settings_vars["logLevel"].get().strip().upper() or "INFO"
        log_level = getattr(logging, log_level_name, logging.INFO)

        return RuntimeConfig(
            llm_model=self.settings_vars["llmModel"].get().strip(),
            schema_path=self.default_schema_path,
            model_path=self.model_file,
            api_key=self.settings_vars["apiKey"].get().strip(),
            temperature=temperature,
            response_format=self.settings_vars["responseFormat"].get(),
            api_base=self.settings_vars["apiBase"].get().strip() or None,
            timeout=timeout,
            log_level=log_level,
        )

    def run_main_script(self) -> None:
        if self._running:
            return

        try:
            config = self._build_runtime_config()
        except Exception as exc:
            messagebox.showerror("Invalid Configuration", str(exc))
            return

        if not self._show_generation_warning():
            return

        self._set_api_env(config.llm_model, self.settings_vars["apiKey"].get())

        self._running = True
        self.run_button.configure(state="disabled")


        def worker() -> None:
            try:
                run_threat_modeling(config, log_callback=self._log)
            except Exception as exc:
                self._log(f"Error: {exc}")
            finally:
                self.root.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self) -> None:
        self._running = False
        self.run_button.configure(state="normal")

    def on_exit_request(self) -> None:
        has_unsaved_changes = self._has_unsaved_config_changes()
        message = "Do you want to close the application?"
        if has_unsaved_changes:
            message += "\n\nYou have unsaved configuration changes."

        should_close = messagebox.askokcancel(
            "Confirm Exit",
            message,
            icon="warning" if has_unsaved_changes else "question",
            parent=self.root,
            default=messagebox.CANCEL,
        )
        if should_close:
            self.root.destroy()


def start_gui() -> None:
    """Start the desktop app."""
    root = ttk.Window(themename="flatly")
    ThreatGUI(root)
    root.mainloop()


if __name__ == "__main__":
    start_gui()
