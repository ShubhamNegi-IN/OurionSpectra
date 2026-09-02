"""
Main OurionSpectra application window.

UI is built in small `_build_*` methods (header, input card, analysis
card, features card, info card, footer) so each section is easy to find
and edit independently. Data/recovery logic lives in its own section
below the UI builders.
"""

import csv
import os
import re
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .config import (
    NAVY, NAVY_DEEP, BLUE_ACCENT, BG, CARD_BG, TEXT_SUB, GREEN, AMBER,
    GRAY_LINE, LOGO_PATH, BORDER,
    STATUS_GREEN, STATUS_AMBER, STATUS_GRAY, WAVELENGTH_UNIT_TO_NM,
)
from .science import (
    rmse, mae, moving_average, generate_sample_spectrum,
    normalize_series, guess_column,
)
from .model import run_recovery_model, detect_atmospheric_features, MODEL_NAME
from . import composition_model
from .widgets import CanvasSlider, icon_badge, bordered_card, CsvColumnMappingDialog, WorkflowIndicator
from . import storage
from .report import export_report_pdf
from .parser import sniff_and_read_csv, parse_spectrum_data, extract_target_metadata, is_float


APP_STATES = {
    "NO_DATA": ("Awaiting data", NAVY, STATUS_GRAY),
    "DATA_LOADED": ("Data loaded", NAVY, STATUS_AMBER),
    "PREPROCESSING": ("Preprocessing", NAVY, STATUS_AMBER),
    "RECOVERING": ("Recovering spectrum", NAVY, STATUS_AMBER),
    "RECOVERY_COMPLETE": ("Recovery complete", GREEN, STATUS_GREEN),
    "ERROR": ("Error", "#b42318", "#b42318"),
}


@dataclass
class AppState:
    """Single source of truth for data, status, metadata and run results."""
    status: str = "NO_DATA"
    target: str = "Not specified"
    dataset: str = ""
    instrument: str = ""
    wavelengths: list = field(default_factory=list)
    noisy_spec: list = field(default_factory=list)
    raw_flux: list = field(default_factory=list)
    reference_spec: list = field(default_factory=list)
    recovered_spec: list = field(default_factory=list)
    full_recovered_spec: list = field(default_factory=list)
    unc_lower: list = field(default_factory=list)
    unc_upper: list = field(default_factory=list)
    full_unc_lower: list = field(default_factory=list)
    full_unc_upper: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    features: list = field(default_factory=list)
    noise_level: float = 0.30
    restore_pct: float = 100.0
    has_reference: bool = False
    has_exported: bool = False
    selected_session_id: str = None
    highlight_wl: float = None


class OurionSpectraApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OURIONSPECTRA — Exoplanet Atmospheric Spectrum Recovery")
        self.geometry("1180x900")
        self.configure(bg=BG)
        self.minsize(980, 760)
        self._set_app_icon()

        # ---- centralized application state ----
        self.state = AppState()
        self.logo_img_ref = None
        self._noise_reload_job = None
        self.noise_var = tk.DoubleVar(value=0.30)
        self.restore_var = tk.DoubleVar(value=100.0)


        self._build_style()
        self._build_main()
        self._build_footer()
        self._render_chart()
        self._update_workflow()
        self._sync_controls()

    # =============================================================
    # CENTRAL STATE ACCESSORS
    # =============================================================
    @property
    def wavelengths(self): return self.state.wavelengths
    @wavelengths.setter
    def wavelengths(self, value): self.state.wavelengths = value

    @property
    def true_spec(self): return self.state.reference_spec
    @true_spec.setter
    def true_spec(self, value): self.state.reference_spec = value

    @property
    def noisy_spec(self): return self.state.noisy_spec
    @noisy_spec.setter
    def noisy_spec(self, value): self.state.noisy_spec = value

    @property
    def recovered_spec(self): return self.state.recovered_spec
    @recovered_spec.setter
    def recovered_spec(self, value): self.state.recovered_spec = value

    @property
    def unc_lower(self): return self.state.unc_lower
    @unc_lower.setter
    def unc_lower(self, value): self.state.unc_lower = value

    @property
    def unc_upper(self): return self.state.unc_upper
    @unc_upper.setter
    def unc_upper(self, value): self.state.unc_upper = value

    @property
    def has_data(self): return bool(self.state.wavelengths and self.state.noisy_spec)
    @property
    def has_recovery(self): return bool(self.state.recovered_spec)
    @property
    def has_reference(self): return self.state.has_reference
    @has_reference.setter
    def has_reference(self, value): self.state.has_reference = bool(value)
    @property
    def has_exported(self): return self.state.has_exported
    @has_exported.setter
    def has_exported(self, value): self.state.has_exported = bool(value)
    @property
    def is_recovering(self): return self.state.status == "RECOVERING"
    @property
    def source_label(self): return self.state.dataset
    @source_label.setter
    def source_label(self, value): self.state.dataset = value
    @property
    def highlight_wl(self): return self.state.highlight_wl
    @highlight_wl.setter
    def highlight_wl(self, value): self.state.highlight_wl = value
    @property
    def _current_features(self): return self.state.features
    @_current_features.setter
    def _current_features(self, value): self.state.features = value

    # =============================================================
    # APP / WINDOW ICON (titlebar + taskbar)
    # =============================================================
    def _set_app_icon(self):
        # .ico works for the window titlebar + taskbar on Windows.
        ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "ourionspectra.ico")
        try:
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
                return
        except Exception:
            pass
        # Fallback (also works cross-platform): a PNG via iconphoto.
        png_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon_64.png")
        try:
            if PIL_AVAILABLE and os.path.exists(png_path):
                self._icon_img_ref = ImageTk.PhotoImage(Image.open(png_path))
                self.iconphoto(True, self._icon_img_ref)
        except Exception:
            pass

    # =============================================================
    # STYLE
    # =============================================================
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=CARD_BG)
        style.configure("Treeview", background="white", fieldbackground="white",
                         rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))

    # =============================================================
    # SCROLLABLE MAIN AREA
    # =============================================================
    def _build_main(self):
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=main, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_resize(e):
            canvas.itemconfig(window_id, width=e.width)

        main.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_canvas_resize)

        def on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._build_header(main)
        self._build_input_card(main)
        self._build_analysis_card(main)
        self._build_features_card(main)
        self._build_history_card(main)
        self._build_info_card(main)

    # =============================================================
    # HEADER
    # =============================================================
    def _build_header(self, parent):
        header = tk.Frame(parent, bg="white")
        header.pack(fill="x", side="top")

        row = tk.Frame(header, bg="white")
        row.pack(fill="x", padx=28, pady=(20, 16))

        left = tk.Frame(row, bg="white")
        left.pack(side="left", anchor="w")

        used_image_logo = False
        try:
            if PIL_AVAILABLE and os.path.exists(LOGO_PATH):
                img = Image.open(LOGO_PATH)
                img.thumbnail((300, 84), Image.LANCZOS)
                self.logo_img_ref = ImageTk.PhotoImage(img)
                tk.Label(left, image=self.logo_img_ref, bg="white").pack(anchor="w")
                used_image_logo = True
        except Exception:
            used_image_logo = False

        if not used_image_logo:
            tk.Label(left, text="OURIONSPECTRA", bg="white", fg=NAVY,
                     font=("Segoe UI", 22, "bold")).pack(anchor="w")

        # ---- title hierarchy: product name, subtitle, tagline ----
        tk.Label(left, text="Exoplanet Atmospheric Spectrum Recovery", bg="white", fg=NAVY,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(6, 1))
        tk.Label(left, text="AI-assisted recovery and analysis of noisy exoplanet spectra",
                 bg="white", fg=TEXT_SUB, font=("Segoe UI", 10)).pack(anchor="w")

        right = tk.Frame(row, bg="white")
        right.pack(side="right", anchor="ne")

        top_right = tk.Frame(right, bg="white")
        top_right.pack(anchor="e")
        tk.Label(top_right, text="Exoplanet AI Lab", bg="white", fg=NAVY,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 10))
        help_canvas = tk.Canvas(top_right, width=24, height=24, bg="white", highlightthickness=0)
        help_canvas.pack(side="left")
        help_canvas.create_oval(2, 2, 22, 22, outline=NAVY, width=1.4)
        help_canvas.create_text(12, 12, text="?", fill=NAVY, font=("Segoe UI", 9, "bold"))

        # ---- application status pill + target readout ----
        status_row = tk.Frame(right, bg="white")
        status_row.pack(anchor="e", pady=(14, 0))
        self.header_target_lbl = tk.Label(status_row, text="Target: Not specified", bg="white", fg=TEXT_SUB,
                                           font=("Segoe UI", 9))
        self.header_target_lbl.pack(side="left", padx=(0, 14))

        pill = tk.Frame(status_row, bg="#eef2f7")
        pill.pack(side="left")
        self.header_status_dot = tk.Canvas(pill, width=10, height=10, bg="#eef2f7", highlightthickness=0)
        self.header_status_dot.pack(side="left", padx=(10, 6), pady=5)
        self._header_status_dot_id = self.header_status_dot.create_oval(1, 1, 9, 9, fill=STATUS_GRAY, outline="")
        self.header_status_lbl = tk.Label(pill, text="Awaiting data", bg="#eef2f7", fg=NAVY,
                                           font=("Segoe UI", 9, "bold"))
        self.header_status_lbl.pack(side="left", padx=(0, 10), pady=5)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        # ---- 5-step workflow indicator ----
        wf_wrap = tk.Frame(parent, bg="white")
        wf_wrap.pack(fill="x")
        wf_inner = tk.Frame(wf_wrap, bg="white")
        wf_inner.pack(fill="x", padx=28, pady=(10, 4))
        self.workflow = WorkflowIndicator(
            wf_inner,
            steps=["LOAD DATA", "PREPROCESS", "RECOVER", "ANALYZE", "EXPORT"],
            bg="white",
        )
        self.workflow.pack(fill="x")
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    # =============================================================
    # GENERIC CARD HELPER
    # =============================================================
    def _card(self, parent, title, icon="activity"):
        outer, card = bordered_card(parent, bg=CARD_BG)
        outer.pack(fill="x", padx=20, pady=8)
        header = tk.Frame(card, bg=CARD_BG)
        header.pack(fill="x", padx=20, pady=(16, 8))
        icon_badge(header, icon, bg=CARD_BG).pack(side="left", padx=(0, 8))
        tk.Label(header, text=title, bg=CARD_BG, fg=NAVY,
                  font=("Segoe UI", 12, "bold")).pack(side="left")
        body = tk.Frame(card, bg=CARD_BG)
        body.pack(fill="x", padx=20, pady=(0, 18))
        return card, header, body

    # =============================================================
    # INPUT CARD
    # =============================================================
    def _build_input_card(self, parent):
        _, _, body = self._card(parent, "INPUT SPECTRUM", icon="activity")
        grid = tk.Frame(body, bg=CARD_BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        upload = tk.Frame(grid, bg=CARD_BG)
        upload.grid(row=0, column=0, sticky="nsew", padx=(0, 16), ipady=10)
        icon_badge(upload, "upload", bg=CARD_BG, size=44).pack(pady=(8, 6))
        tk.Label(upload, text="Upload your telescope spectrum", bg=CARD_BG,
                  font=("Segoe UI", 11, "bold")).pack(pady=(0, 2))
        tk.Label(upload, text="CSV — columns: wavelength_nm, normalized_flux",
                  bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 9)).pack(pady=(0, 10))
        self.upload_btn = tk.Button(upload, text="📄  Upload CSV", bg=NAVY, fg="white", relief="flat",
                  activebackground=BLUE_ACCENT, activeforeground="white", cursor="hand2",
                  font=("Segoe UI", 10, "bold"), padx=18, pady=7,
                  command=self.upload_csv)
        self.upload_btn.pack()
        divider = tk.Frame(upload, bg=CARD_BG)
        divider.pack(fill="x", pady=8, padx=30)
        tk.Frame(divider, bg=BORDER, height=1).pack(side="left", fill="x", expand=True)
        tk.Label(divider, text="  or  ", bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 9)).pack(side="left")
        tk.Frame(divider, bg=BORDER, height=1).pack(side="left", fill="x", expand=True)
        self.sample_btn = tk.Button(upload, text="📊  Use Sample Spectrum", bg="white", fg=NAVY,
                  relief="solid", bd=1, cursor="hand2",
                  font=("Segoe UI", 10, "bold"), padx=16, pady=6,
                  command=self.load_sample)
        self.sample_btn.pack(pady=(0, 10))

        noise = tk.Frame(grid, bg=CARD_BG)
        noise.grid(row=0, column=1, sticky="nsew")
        tk.Label(noise, text="Restoration Amount (%)", bg=CARD_BG,
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 6))

        restore_row = tk.Frame(noise, bg=CARD_BG)
        restore_row.pack(fill="x")

        self.restore_slider = CanvasSlider(
            restore_row, from_=0.0, to=100.0, value=self.restore_var.get(),
            command=self._on_restore_change, resolution=1.0, bg=CARD_BG, width=200,
        )
        self.restore_slider.pack(side="left", fill="x", expand=True)

        self.restore_value_lbl = tk.Label(restore_row, text=f"{int(self.restore_var.get())}%",
                                           bg="#fafbfc", fg=NAVY, font=("Segoe UI", 10, "bold"),
                                           width=6, relief="solid", bd=1)
        self.restore_value_lbl.pack(side="left", padx=(10, 0))

        restore_scale_row = tk.Frame(noise, bg=CARD_BG)
        restore_scale_row.pack(fill="x", pady=(6, 12))
        tk.Label(restore_scale_row, text="0% · Raw Observation", bg=CARD_BG, fg=TEXT_SUB,
                  font=("Segoe UI", 8)).pack(side="left")
        tk.Label(restore_scale_row, text="50% · Balanced", bg=CARD_BG, fg=TEXT_SUB,
                  font=("Segoe UI", 8)).pack(side="left", expand=True)
        tk.Label(restore_scale_row, text="100% · Full AI Recovery", bg=CARD_BG, fg=TEXT_SUB,
                  font=("Segoe UI", 8)).pack(side="right")

        self.recover_btn = tk.Button(
            noise, text="▶  RECOVER SPECTRUM", bg=NAVY, fg="white", relief="flat",
            activebackground=BLUE_ACCENT, activeforeground="white", cursor="hand2",
            font=("Segoe UI", 11, "bold"), padx=16, pady=12,
            command=self.run_recovery,
        )
        self.recover_btn.pack(fill="x", pady=(12, 6))
        tk.Button(noise, text="Reset to initial state", bg=CARD_BG, fg=TEXT_SUB,
                  relief="flat", cursor="hand2", font=("Segoe UI", 9, "underline"),
                  command=self.reset_all).pack()



    # =============================================================
    # ANALYSIS CARD
    # =============================================================
    def _build_analysis_card(self, parent):
        _, header, body = self._card(parent, "SPECTRUM ANALYSIS", icon="bars")
        self.export_btn = tk.Menubutton(header, text="⬇ Export Results ▾", bg="white", fg=NAVY,
                                    relief="solid", bd=1, cursor="hand2",
                                    font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.export_menu = tk.Menu(self.export_btn, tearoff=0)
        self.export_menu.add_command(label="Download recovered CSV", command=self.export_csv)
        self.export_menu.add_command(label="Download graph as PNG", command=self.export_png)
        self.export_menu.add_command(label="Download full report (PDF)", command=self.export_pdf)
        self.export_btn.configure(menu=self.export_menu)
        self.export_btn.pack(side="right")

        # Legend is rebuilt from real state in _render_legend() so a line
        # never appears in the key unless it's actually plottable right now.
        self.legend_frame = tk.Frame(body, bg=CARD_BG)
        self.legend_frame.pack(pady=(0, 6))

        chart_frame = tk.Frame(body, bg=CARD_BG)
        chart_frame.pack(fill="x")
        self.fig = Figure(figsize=(9.5, 3.6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        self.canvas.mpl_connect("scroll_event", self._on_chart_scroll)

        # ---- metric cards ----
        # Defined as a data-driven list (id -> layout) so a teammate can add
        # a new ML metric later (e.g. "chi2") by appending one entry here,
        # rather than redesigning this section.
        self.metric_defs = [
            {"id": "rmse_before", "icon": "activity", "label": "RMSE Before", "sub": "Higher error (noisier)"},
            {"id": "rmse_after", "icon": "activity", "label": "RMSE After", "sub": "Lower error (better)"},
            {"id": "mae", "icon": "activity", "label": "MAE", "sub": "Lower error (better)"},
            {"id": "recovery_improvement", "icon": "target", "label": "Recovery Improvement", "sub": "(RMSE before − after) / before"},
        ]
        stats = tk.Frame(body, bg=CARD_BG)
        stats.pack(fill="x", pady=(14, 0))
        stats.columnconfigure(tuple(range(len(self.metric_defs))), weight=1)
        self.metric_lbls = {}
        for col, m in enumerate(self.metric_defs):
            self.metric_lbls[m["id"]] = self._stat_card(stats, col, m["icon"], "--", m["label"], m["sub"])
        # Back-compat aliases used elsewhere (history save/load, PDF export).
        self.rmse_before_lbl = self.metric_lbls["rmse_before"]
        self.rmse_after_lbl = self.metric_lbls["rmse_after"]
        self.recovery_pct_lbl = self.metric_lbls["recovery_improvement"]

    def _legend_item(self, parent, color, text, style="line"):
        item = tk.Frame(parent, bg=CARD_BG)
        item.pack(side="left", padx=10)
        if style == "line":
            tk.Frame(item, bg=color, width=18, height=3).pack(side="left", padx=(0, 6))
        elif style == "dotted":
            dots = tk.Canvas(item, width=18, height=6, bg=CARD_BG, highlightthickness=0)
            dots.pack(side="left", padx=(0, 6))
            for x in (1, 6, 11, 16):
                dots.create_oval(x, 2, x + 2, 4, fill=color, outline=color)
        elif style == "swatch":
            tk.Frame(item, bg=color, width=14, height=10).pack(side="left", padx=(0, 6))
        tk.Label(item, text=text, bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 9, "bold")).pack(side="left")

    def _render_legend(self):
        """Only shows a legend entry for a line that is actually plottable
        right now, so an unused key never implies data that isn't there."""
        for w in self.legend_frame.winfo_children():
            w.destroy()
        if not self.has_data:
            return
        self._legend_item(self.legend_frame, GRAY_LINE, "Observed (Noisy)")
        if self.has_reference:
            self._legend_item(self.legend_frame, TEXT_SUB, "Reference / Ground Truth", style="dotted")
        if self.has_recovery:
            self._legend_item(self.legend_frame, BLUE_ACCENT, "Uncertainty (±1σ)", style="swatch")
            self._legend_item(self.legend_frame, NAVY, "AI Recovered")

    def _stat_card(self, parent, col, icon_kind, value, label, sub):
        stat_bg = "#f7f9fb"
        outer, box = bordered_card(parent, bg=stat_bg)
        outer.grid(row=0, column=col, sticky="nsew", padx=6)
        icon_badge(box, icon_kind, bg=stat_bg).pack(pady=(14, 4))
        val_lbl = tk.Label(box, text=value, bg=stat_bg, fg=NAVY, font=("Segoe UI", 18, "bold"))
        val_lbl.pack(pady=(0, 0))
        tk.Label(box, text=label, bg=stat_bg, fg=TEXT_SUB, font=("Segoe UI", 10, "bold")).pack(pady=(2, 0))
        tk.Label(box, text=sub, bg=stat_bg, fg=TEXT_SUB, font=("Segoe UI", 8)).pack(pady=(0, 14))
        return val_lbl

    # =============================================================
    # FEATURES CARD
    # =============================================================
    def _build_features_card(self, parent):
        _, header, body = self._card(parent, "DETECTED ATMOSPHERIC FEATURES", icon="target")
        chip = tk.Label(header, text="AI-assisted predictions", bg="#eef2f7", fg=NAVY,
                         font=("Segoe UI", 8, "bold"), padx=10, pady=4)
        chip.pack(side="right")

        self.features_placeholder = tk.Label(
            body, text="Run spectrum recovery to generate atmospheric feature predictions.",
            bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 10, "italic")
        )
        self.features_placeholder.pack(anchor="w", pady=4)

        cols = ("molecule", "wl", "status", "confidence")
        self.features_tree = ttk.Treeview(body, columns=cols, show="headings", height=4)
        for c, w in zip(cols, (120, 160, 140, 200)):
            self.features_tree.heading(c, text={
                "molecule": "Molecule", "wl": "Approx. Wavelength",
                "status": "Status", "confidence": "AI Confidence"
            }[c])
            self.features_tree.column(c, width=w, anchor="w")
        self.features_tree.tag_configure("detected", foreground=STATUS_GREEN)
        self.features_tree.tag_configure("tentative", foreground=STATUS_AMBER)
        self.features_tree.tag_configure("not_detected", foreground=STATUS_GRAY)
        self.features_tree.bind("<<TreeviewSelect>>", self._on_feature_row_selected)

        self.features_hint = tk.Label(
            body, text="Click a row to highlight its wavelength region on the graph above.",
            bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 8, "italic")
        )

        tk.Label(
            body,
            text="These are AI-assisted predictions derived from the recovered spectrum, not "
                 "confirmed scientific detections. Cross-validation against peer-reviewed "
                 "analysis is recommended before scientific use.",
            bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 8, "italic"),
            wraplength=1000, justify="left"
        ).pack(anchor="w", pady=(8, 0))

    # =============================================================
    # HISTORY CARD
    # =============================================================
    def _build_history_card(self, parent):
        _, header, body = self._card(parent, "SESSION HISTORY", icon="bars")
        tk.Label(header, text="Saved locally on this device", bg=CARD_BG, fg=TEXT_SUB,
                 font=("Segoe UI", 8, "italic")).pack(side="right")

        self.history_placeholder = tk.Label(
            body, text="Run a recovery to start building history.",
            bg=CARD_BG, fg=TEXT_SUB, font=("Segoe UI", 10, "italic")
        )
        self.history_placeholder.pack(anchor="w", pady=4)

        cols = ("label", "saved_at", "recovery")
        self.history_tree = ttk.Treeview(body, columns=cols, show="headings", height=5)
        for c, w, txt in zip(cols, (300, 220, 140), ("Dataset", "Saved At", "Recovery Improvement")):
            self.history_tree.heading(c, text=txt)
            self.history_tree.column(c, width=w, anchor="w")

        btn_row = tk.Frame(body, bg=CARD_BG)
        tk.Button(btn_row, text="Load Selected", bg=NAVY, fg="white", relief="flat",
                  cursor="hand2", font=("Segoe UI", 9, "bold"), padx=12, pady=5,
                  command=self.load_selected_history).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Delete Selected", bg="white", fg=NAVY, relief="solid",
                  bd=1, cursor="hand2", font=("Segoe UI", 9, "bold"), padx=12, pady=5,
                  command=self.delete_selected_history).pack(side="left")
        self._history_btn_row = btn_row

        self._refresh_history_list()

    def _refresh_history_list(self):
        sessions = storage.list_sessions()
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        if not sessions:
            self.history_tree.pack_forget()
            self._history_btn_row.pack_forget()
            self.history_placeholder.pack(anchor="w", pady=4)
            return
        self.history_placeholder.pack_forget()
        for s in sessions:
            pct = f"{s['recovery_improvement']:.1f}%" if s.get("recovery_improvement") is not None else "—"
            self.history_tree.insert("", "end", iid=s["id"],
                                     values=(s["label"], s["saved_at"], pct))
        self.history_tree.pack(fill="x", pady=4)
        self._history_btn_row.pack(anchor="w", pady=(8, 0))

    def load_selected_history(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected", "Select a saved session first.")
            return
        session_id = sel[0]
        try:
            data = storage.load_session(session_id)
        except FileNotFoundError:
            messagebox.showerror("Session not found",
                                 "This session's file is missing (it may have been deleted outside the app).")
            self._refresh_history_list()
            return
        except Exception as e:
            messagebox.showerror("Couldn't load session",
                                 f"The saved file may be corrupted.\n\nDetails: {e}")
            return

        if not data.get("wavelengths") or not data.get("noisy_spec"):
            messagebox.showerror(
                "Incomplete session",
                "This saved session is missing required spectrum data and can't be loaded."
            )
            return

        # Restore the exact saved run. Never re-run feature detection or
        # regenerate metrics on session load; that could create stale/random
        # results that do not correspond to the completed run.
        self.state.wavelengths = data["wavelengths"]
        self.state.noisy_spec = data["noisy_spec"]
        self.state.reference_spec = data.get("reference_spec", data.get("true_spec", []))
        self.state.recovered_spec = data.get("recovered_spec", [])
        self.state.full_recovered_spec = list(self.state.recovered_spec)
        self.state.unc_lower = data.get("unc_lower", [])
        self.state.unc_upper = data.get("unc_upper", [])
        self.state.full_unc_lower = list(self.state.unc_lower)
        self.state.full_unc_upper = list(self.state.unc_upper)
        self.state.dataset = data.get("dataset", data.get("source_label", "Loaded session"))
        self.state.target = data.get("target", "Not specified")
        self.state.instrument = data.get("instrument", "User-supplied CSV")
        self.state.has_reference = bool(data.get("has_reference", False))
        self.state.has_exported = False
        self.state.selected_session_id = session_id
        self.state.highlight_wl = None
        self.state.noise_level = data.get("noise_level", 0.3)
        self.noise_var.set(self.state.noise_level)
        self.noise_value_lbl.config(text=f"{self.state.noise_level:.2f}")
        self.state.restore_pct = data.get("restore_pct", 100.0)
        self.restore_var.set(self.state.restore_pct)
        if hasattr(self, "restore_slider"):
            self.restore_slider.set(self.state.restore_pct)
        if hasattr(self, "restore_value_lbl"):
            self.restore_value_lbl.config(text=f"{int(self.state.restore_pct)}%")
        self.state.features = data.get("features", []) if self.state.recovered_spec else []

        self.state.metrics = {}
        saved_metrics = data.get("metrics", {})
        if self.state.recovered_spec:
            for key in ("rmse_before", "rmse_after", "mae", "recovery_improvement"):
                if saved_metrics.get(key) is not None:
                    self.state.metrics[key] = saved_metrics[key]
            # Backward compatibility for sessions created by the old version,
            # but only trust a percentage when the session explicitly recorded
            # that a real reference existed.
            if not self.state.metrics.get("recovery_improvement") and data.get("metrics_reference_available"):
                legacy_pct = data.get("recovery_pct")
                if legacy_pct is not None:
                    self.state.metrics["recovery_improvement"] = legacy_pct

        self._apply_metric_labels()
        self._clear_features_table()
        if self.state.features:
            self._render_features_from_state()
        self._set_state("RECOVERY_COMPLETE" if self.state.recovered_spec else "DATA_LOADED")
        self._render_info()
        self._render_chart()
        self._update_workflow()
        self._sync_controls()

    def delete_selected_history(self):
        sel = self.history_tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected", "Select a saved session first.")
            return
        session_id = sel[0]
        label = self.history_tree.item(session_id)["values"][0]
        confirmed = messagebox.askyesno(
            "Delete session?",
            f"Delete the saved session \"{label}\"? This can't be undone."
        )
        if not confirmed:
            return
        try:
            storage.delete_session(session_id)
        except Exception as e:
            messagebox.showerror("Couldn't delete session", str(e))
            return

        # If the deleted run is currently displayed, clear the dashboard so
        # the UI cannot continue showing a result that no longer exists.
        if self.state.selected_session_id == session_id:
            self.reset_all()
        self._refresh_history_list()

    def _save_current_session(self, noise_level):
        session = {
            "wavelengths": list(self.wavelengths),
            "noisy_spec": list(self.noisy_spec),
            "reference_spec": list(self.true_spec) if self.has_reference else [],
            "recovered_spec": list(self.recovered_spec),
            "unc_lower": list(self.unc_lower),
            "unc_upper": list(self.unc_upper),
            "dataset": self.source_label,
            "target": self.state.target,
            "instrument": self.state.instrument,
            "noise_level": noise_level,
            "restore_pct": self.state.restore_pct,
            "has_reference": self.has_reference,
            "features": list(self._current_features),
            "metrics": dict(self.state.metrics),
            "metrics_reference_available": self.has_reference,
        }

        session_id = storage.save_session(session)
        if session_id:
            self.state.selected_session_id = session_id
        # Save/load operates on the completed run currently on screen.
        # The storage layer assigns the session id; refresh history afterward.
        self._refresh_history_list()

    @staticmethod
    def _is_float(s):
        try:
            float(s)
            return True
        except (TypeError, ValueError):
            return False

    # =============================================================
    # INFO CARD
    # =============================================================
    def _build_info_card(self, parent):
        _, header, body = self._card(parent, "DATASET & MODEL INFO", icon="bars")
        grid = tk.Frame(body, bg=CARD_BG)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2), weight=1)
        self.info_target = self._info_item(grid, 0, 0, "Target", value="Not specified")
        self.info_dataset = self._info_item(grid, 0, 1, "Dataset", value="—")
        self.info_instrument = self._info_item(grid, 0, 2, "Instrument")
        self.info_points = self._info_item(grid, 1, 0, "Data Points")
        self.info_range = self._info_item(grid, 1, 1, "Wavelength Range")
        self._info_item(grid, 2, 0, "Recovery Model", value=MODEL_NAME)
        self.info_status = self._info_item(grid, 2, 2, "Status", value="Awaiting data")

    def _info_item(self, parent, row, col, label, value="—"):
        item = tk.Frame(parent, bg=CARD_BG)
        item.grid(row=row, column=col, sticky="w", padx=6, pady=4)
        tk.Label(item, text=label.upper(), bg=CARD_BG, fg=TEXT_SUB,
                  font=("Segoe UI", 8, "bold")).pack(anchor="w")
        val = tk.Label(item, text=value, bg=CARD_BG, fg=NAVY, font=("Segoe UI", 11, "bold"))
        val.pack(anchor="w")
        return val

    # =============================================================
    # FOOTER
    # =============================================================
    def _build_footer(self):
        footer = tk.Frame(self, bg=NAVY_DEEP, height=36)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer, text="OurionSpectra v1.0", bg=NAVY_DEEP, fg="#cfd9e6",
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=20, pady=6)
        tk.Label(footer, text="AI-Powered  •  Astronomy  •  Discovery",
                  bg=NAVY_DEEP, fg="#8ea2bd", font=("Segoe UI", 9, "bold")).pack(side="right", padx=20, pady=6)

    # =============================================================
    # DATA / RECOVERY LOGIC
    # =============================================================
    def _extract_target_metadata(self, sample_text, headers=None, data_rows=None):
        return extract_target_metadata(sample_text, headers, data_rows)

    @staticmethod
    def _is_float(s):
        return is_float(s)

    def load_sample(self):
        if self.is_recovering:
            return
        self._set_state("PREPROCESSING")
        self.update_idletasks()
        try:
            noise_level = self.noise_var.get()
            wavelengths, reference, noisy = generate_sample_spectrum(noise_level)
            self.state.wavelengths = wavelengths
            self.state.reference_spec = reference
            self.state.noisy_spec = noisy
            self.state.raw_flux = list(noisy)
            self.state.recovered_spec = []
            self.state.unc_lower = []
            self.state.unc_upper = []
            self.state.dataset = "Sample Spectrum (simulated near-IR transit)"
            self.state.target = "Not specified"
            self.state.instrument = "Simulated NIR spectrograph"
            self.state.has_reference = True
            self.state.has_exported = False
            self.state.selected_session_id = None
            self.state.noise_level = noise_level
            self.state.metrics = {}
            self.state.features = []
            self.state.highlight_wl = None
            self._set_state("DATA_LOADED")
            self._after_data_change()
        except Exception as e:
            self._handle_error(e, "Couldn't load sample spectrum")

    def upload_csv(self):
        if self.is_recovering:
            return
        path = filedialog.askopenfilename(
            title="Select spectrum CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except Exception as e:
            self._handle_error(e, "Couldn't read file")
            return

        try:
            parsed_info = sniff_and_read_csv(content)
            headers = parsed_info["headers"]
            data_rows = parsed_info["data_rows"]
            target = parsed_info["target"]

            n_cols = len(headers)
            if n_cols == 2:
                wl_idx, flux_idx = 0, 1
                unit_label = "nm (nanometers)"
                normalize = False
            else:
                wl_idx = guess_column(headers, ("wavelength", "wl", "lambda", "wave"))
                flux_idx = guess_column(headers, ("flux", "flam", "fnu", "flux_norm", "value"),
                                         exclude=wl_idx)
                unit_hint = " ".join(headers).lower()
                default_unit = "µm (microns)" if (
                    "micron" in unit_hint or "_micron" in unit_hint or "um" in unit_hint
                ) else "nm (nanometers)"
                unit_options = list(WAVELENGTH_UNIT_TO_NM.keys())
                unit_options.remove(default_unit)
                unit_options.insert(0, default_unit)

                dlg = CsvColumnMappingDialog(
                    self, headers, data_rows[:5], unit_options,
                    guessed_wl_idx=wl_idx, guessed_flux_idx=flux_idx,
                    suggest_normalize=True,
                )
                self.wait_window(dlg)
                if dlg.result is None:
                    return
                wl_idx, flux_idx, unit_label, normalize = dlg.result

            # Keep the physical input flux separately from the normalized
            # display/recovery signal. The atmospheric-composition model was
            # trained on physical flux values, while the recovery UI expects
            # normalized flux. Conflating these two domains produces wildly
            # incorrect abundance predictions.
            wavelengths, raw_flux_values, skipped = parse_spectrum_data(
                data_rows, wl_idx=wl_idx, flux_idx=flux_idx, unit=unit_label, normalize=False
            )
            flux_values = normalize_series(raw_flux_values) if normalize else list(raw_flux_values)

            self._set_state("PREPROCESSING")
            self.update_idletasks()
            self.state.wavelengths = wavelengths
            self.state.noisy_spec = flux_values
            self.state.raw_flux = list(raw_flux_values)
            self.state.reference_spec = []
            self.state.recovered_spec = []
            self.state.unc_lower = []
            self.state.unc_upper = []
            self.state.dataset = os.path.basename(path)
            self.state.target = target
            self.state.instrument = "User-supplied CSV"
            self.state.has_reference = False
            self.state.has_exported = False
            self.state.selected_session_id = None
            self.state.metrics = {}
            self.state.features = []
            self.state.highlight_wl = None
            self._set_state("DATA_LOADED")
            self._after_data_change()

            warnings = []
            if skipped > 0:
                warnings.append(f"{skipped} row(s) were skipped (missing or non-numeric values).")
            numeric_row_count = sum(
                1 for row in data_rows
                if len(row) > max(wl_idx, flux_idx)
                and is_float(row[wl_idx]) and is_float(row[flux_idx])
            )
            if numeric_row_count > len(wavelengths) and len(wavelengths) >= 3:
                warnings.append(
                    f"Detected a repeated wavelength grid in the uploaded file. "
                    f"Loaded the first complete spectrum ({len(wavelengths)} points) "
                    f"for single-spectrum analysis instead of interleaving the batch."
                )
            wl_lo, wl_hi = self.wavelengths[0], self.wavelengths[-1]
            if wl_lo < 300 or wl_hi > 30000:
                warnings.append(
                    f"Wavelength range ({wl_lo:.0f}–{wl_hi:.0f} nm) looks unusual — "
                    f"double check the unit you selected."
                )
            if warnings:
                messagebox.showinfo("Loaded with warnings", "\n\n".join(warnings))
        except Exception as e:
            self._handle_error(e, "Couldn't load spectrum")

    def _after_data_change(self):
        self.state.metrics = {}
        self.state.features = []
        self.state.recovered_spec = []
        self.state.unc_lower = []
        self.state.unc_upper = []
        self.state.has_exported = False
        self._apply_metric_labels()
        self._clear_features_table()
        self._render_info()
        self._render_chart()
        self._update_workflow()
        self._sync_controls()

    def _on_noise_change(self, val):
        val = float(val)
        self.noise_var.set(val)
        self.noise_value_lbl.config(text=f"{val:.2f}")
        self.state.noise_level = val
        if self.has_data and self.source_label.startswith("Sample Spectrum") and not self.is_recovering:
            if self._noise_reload_job is not None:
                self.after_cancel(self._noise_reload_job)
            self._noise_reload_job = self.after(180, self.load_sample)

    def _on_restore_change(self, val):
        val = float(val)
        self.restore_var.set(val)
        if hasattr(self, "restore_value_lbl"):
            self.restore_value_lbl.config(text=f"{int(val)}%")
        self.state.restore_pct = val

        # If we already have a recovery run, dynamically re-blend and update the display in real-time
        if self.state.full_recovered_spec and self.has_data:
            self._apply_restoration_blend()
            self._apply_metric_labels()
            self._render_features_from_state()
            self._render_chart()

    def _apply_restoration_blend(self):
        """Blend between noisy input and model recovered spectrum according to restore_pct."""
        if not self.state.full_recovered_spec or not self.noisy_spec:
            return

        alpha = max(0.0, min(1.0, self.state.restore_pct / 100.0))
        full_rec = self.state.full_recovered_spec
        noisy = self.noisy_spec

        blended_rec = [
            (1.0 - alpha) * n + alpha * r
            for n, r in zip(noisy, full_rec)
        ]
        self.state.recovered_spec = blended_rec

        if self.state.full_unc_lower and self.state.full_unc_upper:
            # Scale uncertainty band with restoration amount
            unc_width = [
                (u - l) * 0.5 * alpha
                for l, u in zip(self.state.full_unc_lower, self.state.full_unc_upper)
            ]
            self.state.unc_lower = [r - w for r, w in zip(blended_rec, unc_width)]
            self.state.unc_upper = [r + w for r, w in zip(blended_rec, unc_width)]
        else:
            self.state.unc_lower = []
            self.state.unc_upper = []

        # Recalculate metrics based on current blended spectrum
        self.state.metrics = {}
        if self.has_reference and self.true_spec and len(self.true_spec) == len(blended_rec):
            before = rmse(self.noisy_spec, self.true_spec)
            after = rmse(blended_rec, self.true_spec)
            after_mae = mae(blended_rec, self.true_spec)
            self.state.metrics["rmse_before"] = before
            self.state.metrics["rmse_after"] = after
            self.state.metrics["mae"] = after_mae
            if before:
                self.state.metrics["recovery_improvement"] = (1.0 - after / before) * 100.0

        # Update features
        self._render_features(self.state.noise_level)

    def run_recovery(self):
        if not self.has_data:
            messagebox.showinfo("No data loaded", "Load a spectrum first.")
            return
        if self.is_recovering:
            return
        self.state.has_exported = False
        self._set_state("RECOVERING")
        self.recover_btn.config(state="disabled", text="PROCESSING…")
        self._sync_controls()
        self._update_workflow()
        self.update_idletasks()
        self.after(700, self._finish_recovery)

    def _finish_recovery(self):
        if not self.has_data or self.state.status != "RECOVERING":
            return
        try:
            noise_level = self.noise_var.get()
            recovered, unc_lower, unc_upper = run_recovery_model(
                self.wavelengths, self.noisy_spec, noise_level, restore_pct=100.0
            )
            self.state.full_recovered_spec = list(recovered)
            self.state.full_unc_lower = list(unc_lower) if unc_lower else []
            self.state.full_unc_upper = list(unc_upper) if unc_upper else []
            self.state.noise_level = noise_level
            self.state.restore_pct = self.restore_var.get()
            self.state.has_exported = False

            # Apply the user-selected restoration percentage blend
            self._apply_restoration_blend()


            self._apply_metric_labels()
            self._render_chart()
            self._set_state("RECOVERY_COMPLETE")
            self._render_info()
            self._update_workflow()
            self._sync_controls()
            self._save_current_session(noise_level)
        except Exception as e:
            self.state.recovered_spec = []
            self.state.full_recovered_spec = []
            self.state.unc_lower = []
            self.state.unc_upper = []
            self.state.full_unc_lower = []
            self.state.full_unc_upper = []
            self.state.metrics = {}
            self._set_state("ERROR")
            self._render_info()
            self._render_chart()
            self._update_workflow()
            self._sync_controls()
            messagebox.showerror("Recovery failed", str(e))


    def _clear_features_table(self):
        self.features_tree.pack_forget()
        self.features_hint.pack_forget()
        self.features_placeholder.config(
            text="Run spectrum recovery to generate AI-assisted atmospheric feature predictions."
        )
        self.features_placeholder.pack(anchor="w", pady=4)
        for row in self.features_tree.get_children():
            self.features_tree.delete(row)
        self.state.features = []
        self._clear_highlight()

    def _render_features(self, noise_level):
        # detect_atmospheric_features is a line-detection placeholder that
        # intentionally returns no scientific line detections (see model.py).
        # The trained composition model is a separate regression model that
        # predicts bulk log-abundances; merge its output in here so the GUI
        # actually surfaces it instead of leaving the panel empty.
        features = list(detect_atmospheric_features(
            self.wavelengths, self.recovered_spec, noise_level
        ))
        features.extend(self._composition_feature_rows())
        self.state.features = features
        self._render_features_from_state()

    def _composition_feature_rows(self):
        """Run the trained composition model on the current spectrum and
        return rows in the same shape the features table expects. Reports
        predicted log-abundance as text in the status column rather than a
        fabricated detection confidence, since this model outputs a
        continuous log-abundance value, not a per-line detection score."""
        if not self.has_data or not self.state.raw_flux:
            return []
        try:
            wl_um = [w / 1000.0 for w in self.wavelengths]
            result = composition_model.predict_composition(wl_um, self.state.raw_flux)
        except FileNotFoundError:
            return [{
                "name": "Composition model", "wl_nm": None,
                "status": "Model files not installed", "confidence": None,
            }]
        except ValueError as e:
            return [{
                "name": "Composition model", "wl_nm": None,
                "status": str(e), "confidence": None,
            }]
        except Exception as e:
            return [{
                "name": "Composition model", "wl_nm": None,
                "status": f"Error: {e}", "confidence": None,
            }]

        rows = []
        for p in result["parameters"]:
            rows.append({
                "name": p["molecule"],
                "wl_nm": None,
                "status": f"log\u2081\u2080 abundance: {p['log_abundance']:+.2f}",
                "confidence": None,
            })
        return rows

    def _render_features_from_state(self):
        for row in self.features_tree.get_children():
            self.features_tree.delete(row)

        if not self.state.features:
            self.features_tree.pack_forget()
            self.features_hint.pack_forget()
            self.features_placeholder.config(
                text="No atmospheric feature predictions available."
            )
            self.features_placeholder.pack(anchor="w", pady=4)
            return

        self.features_placeholder.pack_forget()
        tag_map = {"Detected": "detected", "Tentative": "tentative", "Not Detected": "not_detected"}
        for f in self.state.features:
            status = f.get("status", "Not Detected")
            display_status = "Not detected" if status == "Not Detected" else status
            conf = f.get("confidence")
            conf_text = f"{conf:.0f}%" if isinstance(conf, (int, float)) else "--"
            wl = f.get("wl_nm")
            wl_text = f"{wl:.0f} nm" if isinstance(wl, (int, float)) else "--"
            self.features_tree.insert(
                "", "end", tags=(tag_map.get(status, "not_detected"),),
                values=(f.get("name", "--"), wl_text, display_status, conf_text)
            )
        self.features_tree.pack(fill="x", pady=4)
        self.features_hint.pack(anchor="w", pady=(2, 0))

    def _apply_metric_labels(self):
        for key in ("rmse_before", "rmse_after", "mae", "recovery_improvement"):
            value = self.state.metrics.get(key)
            label = self.metric_lbls[key]
            label.config(text=f"{value:.3f}" if value is not None and key != "recovery_improvement"
                         else (f"{value:.1f}%" if value is not None else "--"))

    def _on_feature_row_selected(self, event=None):
        sel = self.features_tree.selection()
        if not sel:
            return
        idx = self.features_tree.index(sel[0])
        if idx >= len(self._current_features):
            return
        wl = self._current_features[idx].get("wl_nm")
        if isinstance(wl, (int, float)):
            self.highlight_wl = wl
            self._render_chart()

    def _clear_highlight(self):
        self.highlight_wl = None

    def _render_info(self):
        if not self.has_data:
            self.info_target.config(text="Not specified")
            self.info_dataset.config(text="—")
            self.info_instrument.config(text="—")
            self.info_points.config(text="—")
            self.info_range.config(text="—")
            self._apply_state_to_status_widgets()
            self.header_target_lbl.config(text="Target: Not specified")
            return

        self.info_target.config(text=self.state.target or "Not specified")
        self.info_dataset.config(text=self.state.dataset or "—")
        self.info_instrument.config(text=self.state.instrument or "—")
        self.info_points.config(text=str(len(self.wavelengths)))
        if self.wavelengths:
            self.info_range.config(text=f"{self.wavelengths[0]:.0f} – {self.wavelengths[-1]:.0f} nm")
        self.header_target_lbl.config(text=f"Target: {self.state.target or 'Not specified'}")
        self._apply_state_to_status_widgets()

    # =============================================================
    # CENTRAL STATUS STATE
    # =============================================================
    def _set_state(self, state_name):
        if state_name not in APP_STATES:
            raise ValueError(f"Unknown application state: {state_name}")
        self.state.status = state_name
        self._apply_state_to_status_widgets()
        if hasattr(self, "workflow"):
            self._update_workflow()
        if hasattr(self, "recover_btn"):
            self._sync_controls()

    def _apply_state_to_status_widgets(self):
        text, text_color, dot_color = APP_STATES[self.state.status]
        if hasattr(self, "info_status"):
            self.info_status.config(text=text, fg=text_color)
        if hasattr(self, "header_status_lbl"):
            self.header_status_lbl.config(text=text, fg=text_color)
            self.header_status_dot.itemconfig(self._header_status_dot_id, fill=dot_color)

    def _set_status(self, text, text_color, dot_color):
        """Compatibility shim: all status changes now go through state."""
        for name, value in APP_STATES.items():
            if value[0] == text:
                self._set_state(name)
                return
        self._set_state("ERROR")

    def _handle_error(self, error, title="Error"):
        self._set_state("ERROR")
        self._render_info()
        self._update_workflow()
        self._sync_controls()
        messagebox.showerror(title, str(error))

    def _sync_controls(self):
        recovering = self.state.status == "RECOVERING"
        has_data = self.has_data
        has_recovery = self.has_recovery

        if hasattr(self, "upload_btn"):
            self.upload_btn.config(state="disabled" if recovering else "normal")
        if hasattr(self, "sample_btn"):
            self.sample_btn.config(state="disabled" if recovering else "normal")
        if hasattr(self, "slider"):
            self.slider.config(state="disabled" if recovering else "normal")
        if hasattr(self, "restore_slider"):
            self.restore_slider.config(state="disabled" if recovering else "normal")
        if hasattr(self, "recover_btn"):
            self.recover_btn.config(
                state="disabled" if (recovering or not has_data) else "normal",
                text="PROCESSING…" if recovering else "▶  RECOVER SPECTRUM"
            )

        if hasattr(self, "export_menu"):
            export_state = "normal" if has_recovery and not recovering else "disabled"
            for idx in range(3):
                self.export_menu.entryconfig(idx, state=export_state)

    def _update_workflow(self):
        completed = set()
        active = 0
        status = self.state.status

        if status == "NO_DATA":
            active = 0
        elif status == "PREPROCESSING":
            completed.add(0)
            active = 1
        elif status == "DATA_LOADED":
            completed.update({0, 1})
            active = 2
        elif status == "RECOVERING":
            completed.update({0, 1})
            active = 2
        elif status == "RECOVERY_COMPLETE":
            completed.update({0, 1, 2})
            active = 3
        elif status == "ERROR":
            # Preserve completed data steps if data is still present, but
            # don't claim recovery completed.
            if self.has_data:
                completed.update({0, 1})
                active = 2
            else:
                active = 0

        if self.has_exported and status == "RECOVERY_COMPLETE":
            completed.update({0, 1, 2, 3, 4})
            active = 4

        self.workflow.update_state(completed=completed, active=active)

    def _on_chart_scroll(self, event):
        """Sensible, safe zoom: scroll to zoom in/out on wavelength axis,
        centered on the cursor, clamped so you can't zoom past the data."""
        if not self.has_data or event.xdata is None:
            return
        lo, hi = self.ax.get_xlim()
        data_lo, data_hi = min(self.wavelengths), max(self.wavelengths)
        span = hi - lo
        factor = 0.85 if event.button == "up" else (1 / 0.85)
        new_span = max((data_hi - data_lo) * 0.05, min(data_hi - data_lo, span * factor))
        frac = (event.xdata - lo) / span if span else 0.5
        new_lo = event.xdata - frac * new_span
        new_hi = new_lo + new_span
        if new_lo < data_lo:
            new_lo, new_hi = data_lo, data_lo + new_span
        if new_hi > data_hi:
            new_hi, new_lo = data_hi, data_hi - new_span
        self.ax.set_xlim(new_lo, new_hi)
        self.canvas.draw_idle()

    def _render_chart(self):
        self.ax.clear()
        if self.has_data:
            if self.has_reference and self.true_spec:
                self.ax.plot(self.wavelengths, self.true_spec, color=TEXT_SUB,
                              linewidth=1.3, linestyle=":", label="Reference / Ground Truth")
            self.ax.plot(self.wavelengths, self.noisy_spec, color=GRAY_LINE,
                          linewidth=1.2, linestyle="--", marker="o", markersize=2,
                          label="Observed (Noisy)")
            if self.has_recovery:
                if self.unc_lower and self.unc_upper:
                    self.ax.fill_between(self.wavelengths, self.unc_lower, self.unc_upper,
                                          color=BLUE_ACCENT, alpha=0.18, label="Uncertainty (±1σ)")
                self.ax.plot(self.wavelengths, self.recovered_spec, color=NAVY,
                              linewidth=2.2, label="AI Recovered")
            if self.highlight_wl is not None:
                self.ax.axvspan(self.highlight_wl - 25, self.highlight_wl + 25,
                                 color=AMBER, alpha=0.15, zorder=0)
                self.ax.axvline(self.highlight_wl, color=AMBER, linewidth=1, linestyle="--", alpha=0.7)
            self.ax.set_xlabel("Wavelength (nm)", fontsize=9, color=TEXT_SUB)
            self.ax.set_ylabel("Normalized Flux", fontsize=9, color=TEXT_SUB)
            wl_lo, wl_hi = min(self.wavelengths), max(self.wavelengths)
            pad = max((wl_hi - wl_lo) * 0.02, 1)
            self.ax.set_xlim(wl_lo - pad, wl_hi + pad)
            self.ax.set_ylim(0.0, 1.2)
            self.ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
        else:
            self.ax.text(0.5, 0.5, "Upload a spectrum or load the sample dataset to begin",
                          ha="center", va="center", color=TEXT_SUB, fontsize=10, style="italic",
                          transform=self.ax.transAxes)
            self.ax.set_xlim(1000, 2500)
            self.ax.set_ylim(0.0, 1.2)
            self.ax.set_xticks([1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400])
            self.ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2])

        self.ax.grid(True, color="#eef1f5", linewidth=0.7)
        self.ax.set_axisbelow(True)
        for spine in self.ax.spines.values():
            spine.set_color("#d7dee6")
        self.ax.tick_params(colors=TEXT_SUB, labelsize=8)

        self.fig.tight_layout()
        self.canvas.draw()
        self._render_legend()

    def reset_all(self):
        if self._noise_reload_job is not None:
            self.after_cancel(self._noise_reload_job)
            self._noise_reload_job = None

        self.state = AppState()
        self.noise_var.set(0.30)
        self.restore_var.set(100.0)
        if hasattr(self, "slider"):
            self.slider.set(0.30)
        if hasattr(self, "noise_value_lbl"):
            self.noise_value_lbl.config(text="0.30")
        if hasattr(self, "restore_slider"):
            self.restore_slider.set(100.0)
        if hasattr(self, "restore_value_lbl"):
            self.restore_value_lbl.config(text="100%")
        self._apply_metric_labels()

        self._clear_features_table()
        self._render_info()
        self._render_chart()
        self._set_state("NO_DATA")
        self._refresh_history_list()
        self._sync_controls()

    def export_csv(self):
        if not self.has_recovery:
            messagebox.showinfo("Nothing to export", "Run spectrum recovery first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="ourionspectra_recovered_spectrum.csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["wavelength_nm", "observed_noisy_flux", "ai_recovered_flux",
                              "uncertainty_lower", "uncertainty_upper"])
            for i in range(len(self.wavelengths)):
                writer.writerow([
                    self.wavelengths[i],
                    f"{self.noisy_spec[i]:.4f}",
                    f"{self.recovered_spec[i]:.4f}",
                    f"{self.unc_lower[i]:.4f}",
                    f"{self.unc_upper[i]:.4f}",
                ])
        self._mark_exported()
        messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def export_png(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile="ourionspectra_spectrum_graph.png",
            filetypes=[("PNG image", "*.png")]
        )
        if not path:
            return
        self.fig.savefig(path, dpi=150)
        if self.has_recovery:
            self._mark_exported()
        messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def export_pdf(self):
        if not self.has_data:
            messagebox.showinfo("Nothing to export", "Load a spectrum first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile="ourionspectra_report.pdf",
            filetypes=[("PDF file", "*.pdf")]
        )
        if not path:
            return
        features_rows = [self.features_tree.item(iid)["values"]
                          for iid in self.features_tree.get_children()]
        try:
            export_report_pdf(
                path, self.wavelengths, self.noisy_spec, self.recovered_spec,
                self.unc_lower, self.unc_upper, self.source_label,
                self.state.metrics.get("rmse_before"),
                self.state.metrics.get("rmse_after"),
                self.state.metrics.get("recovery_improvement"),
                features_rows,
                colors={"navy": NAVY, "blue_accent": BLUE_ACCENT, "gray_line": GRAY_LINE, "text_sub": TEXT_SUB},
                mae_val=self.state.metrics.get("mae"),
                reference_spec=self.true_spec if self.has_reference else None,
            )
        except Exception as e:
            messagebox.showerror("Couldn't export report", str(e))
            return
        if self.has_recovery:
            self._mark_exported()
        messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def _mark_exported(self):
        """EXPORT step only completes once a real export has succeeded."""
        self.has_exported = True
        self._update_workflow()