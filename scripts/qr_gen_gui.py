"""
Tkinter GUI for the stylized QR generator.
- Live preview as you type or tweak options
- All options from qr_gen_cli.py: styles, gradients (incl. rainbow), frame+label

Requirements: pillow, qrcode, qr_gen_cli.py in same dir. Optional: a TTF font for labels.
"""
from __future__ import annotations

import webbrowser
from typing import Optional, Tuple

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox

# Import local core next to this file
try:
    import qr_gen_cli as core
except Exception as e:
    # Avoid messagebox before Tk root exists
    raise RuntimeError(f"Could not import qrGenerator.py in the same folder.\n{e}")

from PIL import Image, ImageTk

Color = Tuple[int, int, int]


def rgb_to_hex(c: Color) -> str:
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


class Debouncer:
    def __init__(self, widget: tk.Widget, delay_ms: int = 150):
        self.widget = widget
        self.delay_ms = delay_ms
        self._after_id: Optional[str] = None

    def schedule(self, fn):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
        self._after_id = self.widget.after(self.delay_ms, fn)


class QRGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QR Code Generator")
        self.geometry("1100x720")
        self.minsize(960, 640)

        self._img_tk: Optional[ImageTk.PhotoImage] = None
        self._preview_img: Optional[Image.Image] = None
        self._debounce = Debouncer(self, 150)

        self._build_ui()
        self._wire_events()
        self._update_preview()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left: controls
        left = ttk.Frame(self, padding=(10, 10))
        left.grid(row=0, column=0, sticky="nsw")

        # Right: preview
        right = ttk.Frame(self, padding=(10, 10))
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # Content
        g = ttk.LabelFrame(left, text="Content", padding=10)
        g.grid(sticky="ew")
        g.columnconfigure(1, weight=1)
        ttk.Label(g, text="Text/URL").grid(row=0, column=0, sticky="w")
        self.var_text = tk.StringVar(value="https://example.com")
        self.ent_text = ttk.Entry(g, textvariable=self.var_text, width=40)
        self.ent_text.grid(row=0, column=1, sticky="ew", pady=2)

        # QR Settings
        g2 = ttk.LabelFrame(left, text="QR Settings", padding=10)
        g2.grid(sticky="ew", pady=(10, 0))
        g2.columnconfigure(1, weight=1)

        ttk.Label(g2, text="Style").grid(row=0, column=0, sticky="w")
        self.var_style = tk.StringVar(value="squares")
        self.cbo_style = ttk.Combobox(
            g2,
            textvariable=self.var_style,
            values=[
                "squares",
                "circles",
                "rounded",
                "bars-h",
                "bars-v",
                "continuous",
                "rounded-continuous",
            ],
            state="readonly",
            width=22,
        )
        self.cbo_style.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(g2, text="EC Level").grid(row=1, column=0, sticky="w")
        self.var_ec = tk.StringVar(value="M")
        self.cbo_ec = ttk.Combobox(g2, textvariable=self.var_ec, values=["L", "M", "Q", "H"], state="readonly", width=22)
        self.cbo_ec.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(g2, text="Version (1-40 / auto)").grid(row=2, column=0, sticky="w")
        self.var_version = tk.StringVar(value="")
        self.ent_version = ttk.Entry(g2, textvariable=self.var_version, width=22)
        self.ent_version.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(g2, text="Module radius").grid(row=3, column=0, sticky="w")
        self.var_radius = tk.DoubleVar(value=0.30)
        self.sld_radius = ttk.Scale(g2, from_=0.0, to=0.5, variable=self.var_radius)
        self.sld_radius.grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(g2, text="Quiet zone (modules)").grid(row=4, column=0, sticky="w")
        self.var_border = tk.IntVar(value=4)
        self.sld_border = ttk.Scale(g2, from_=0, to=8, variable=self.var_border)
        self.sld_border.grid(row=4, column=1, sticky="ew", pady=2)

        ttk.Label(g2, text="Image size (px)").grid(row=5, column=0, sticky="w")
        self.var_size = tk.IntVar(value=800)
        self.sld_size = ttk.Scale(g2, from_=256, to=2048, variable=self.var_size)
        self.sld_size.grid(row=5, column=1, sticky="ew", pady=2)

        ttk.Label(g2, text="Extra padding (px)").grid(row=6, column=0, sticky="w")
        self.var_padding = tk.IntVar(value=0)
        self.sld_padding = ttk.Scale(g2, from_=0, to=128, variable=self.var_padding)
        self.sld_padding.grid(row=6, column=1, sticky="ew", pady=2)

        # Colors
        g3 = ttk.LabelFrame(left, text="Colors", padding=10)
        g3.grid(sticky="ew", pady=(10, 0))
        g3.columnconfigure(1, weight=1)

        ttk.Label(g3, text="Foreground").grid(row=0, column=0, sticky="w")
        self.var_fg = tk.StringVar(value="#000000")
        self.ent_fg = ttk.Entry(g3, textvariable=self.var_fg)
        self.ent_fg.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Button(g3, text="Pick", command=lambda: self._pick_color(self.var_fg)).grid(row=0, column=2, padx=4)

        ttk.Label(g3, text="Background").grid(row=1, column=0, sticky="w")
        self.var_bg = tk.StringVar(value="#ffffff")
        self.ent_bg = ttk.Entry(g3, textvariable=self.var_bg)
        self.ent_bg.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Button(g3, text="Pick", command=lambda: self._pick_color(self.var_bg)).grid(row=1, column=2, padx=4)

        ttk.Label(g3, text="Gradient").grid(row=2, column=0, sticky="w")
        self.var_gradient = tk.StringVar(value="none")
        self.cbo_gradient = ttk.Combobox(g3, textvariable=self.var_gradient, values=["none", "h", "v", "diag", "rainbow"], state="readonly")
        self.cbo_gradient.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(g3, text="Gradient To").grid(row=3, column=0, sticky="w")
        self.var_fg2 = tk.StringVar(value="#ff3b3b")
        self.ent_fg2 = ttk.Entry(g3, textvariable=self.var_fg2)
        self.ent_fg2.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Button(g3, text="Pick", command=lambda: self._pick_color(self.var_fg2)).grid(row=3, column=2, padx=4)

        # Frame & Label
        g4 = ttk.LabelFrame(left, text="Frame & Label", padding=10)
        g4.grid(sticky="ew", pady=(10, 0))
        g4.columnconfigure(1, weight=1)

        self.var_frame = tk.BooleanVar(value=False)
        ttk.Checkbutton(g4, text="Enable Frame", variable=self.var_frame, command=self._update_preview).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(g4, text="Label").grid(row=1, column=0, sticky="w")
        self.var_label = tk.StringVar(value="")
        self.ent_label = ttk.Entry(g4, textvariable=self.var_label)
        self.ent_label.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(g4, text="Label Position").grid(row=2, column=0, sticky="w")
        self.var_label_pos = tk.StringVar(value="bottom")
        self.cbo_label_pos = ttk.Combobox(g4, textvariable=self.var_label_pos, values=["top", "bottom"], state="readonly")
        self.cbo_label_pos.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(g4, text="Frame BG").grid(row=3, column=0, sticky="w")
        self.var_frame_bg = tk.StringVar(value="#ffffff")
        self.ent_frame_bg = ttk.Entry(g4, textvariable=self.var_frame_bg)
        self.ent_frame_bg.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Button(g4, text="Pick", command=lambda: self._pick_color(self.var_frame_bg)).grid(row=3, column=2, padx=4)

        ttk.Label(g4, text="Frame Border").grid(row=4, column=0, sticky="w")
        self.var_frame_border = tk.StringVar(value="#dcdcdc")
        self.ent_frame_border = ttk.Entry(g4, textvariable=self.var_frame_border)
        self.ent_frame_border.grid(row=4, column=1, sticky="ew", pady=2)
        ttk.Button(g4, text="Pick", command=lambda: self._pick_color(self.var_frame_border)).grid(row=4, column=2, padx=4)

        ttk.Label(g4, text="Frame Radius").grid(row=5, column=0, sticky="w")
        self.var_frame_radius = tk.IntVar(value=24)
        self.sld_frame_radius = ttk.Scale(g4, from_=0, to=64, variable=self.var_frame_radius)
        self.sld_frame_radius.grid(row=5, column=1, sticky="ew", pady=2)

        ttk.Label(g4, text="Frame Padding").grid(row=6, column=0, sticky="w")
        self.var_frame_pad = tk.IntVar(value=32)
        self.sld_frame_pad = ttk.Scale(g4, from_=0, to=128, variable=self.var_frame_pad)
        self.sld_frame_pad.grid(row=6, column=1, sticky="ew", pady=2)

        ttk.Label(g4, text="Label Padding").grid(row=7, column=0, sticky="w")
        self.var_label_pad = tk.IntVar(value=16)
        self.sld_label_pad = ttk.Scale(g4, from_=0, to=64, variable=self.var_label_pad)
        self.sld_label_pad.grid(row=7, column=1, sticky="ew", pady=2)

        ttk.Label(g4, text="Label Color").grid(row=8, column=0, sticky="w")
        self.var_label_color = tk.StringVar(value="#000000")
        self.ent_label_color = ttk.Entry(g4, textvariable=self.var_label_color)
        self.ent_label_color.grid(row=8, column=1, sticky="ew", pady=2)
        ttk.Button(g4, text="Pick", command=lambda: self._pick_color(self.var_label_color)).grid(row=8, column=2, padx=4)

        ttk.Label(g4, text="Font Size").grid(row=9, column=0, sticky="w")
        self.var_font_size = tk.IntVar(value=28)
        wrap = ttk.Frame(g4)
        wrap.grid(row=9, column=1, sticky="ew", pady=2)
        wrap.columnconfigure(0, weight=1)
        self.sld_font_size = ttk.Scale(wrap, from_=8, to=72, variable=self.var_font_size)
        self.sld_font_size.grid(row=0, column=0, sticky="ew")
        self.spn_font_size = ttk.Spinbox(wrap, from_=6, to=128, textvariable=self.var_font_size, width=5)
        self.spn_font_size.grid(row=0, column=1, padx=(6,0))

        # Actions
        g_actions = ttk.Frame(left, padding=(0, 10, 0, 0))
        g_actions.grid(sticky="ew")
        g_actions.columnconfigure(0, weight=1)
        ttk.Button(g_actions, text="Save PNG...", command=self._save_png).grid(row=0, column=0, sticky="ew")

        ttk.Separator(left, orient="horizontal").grid(sticky="ew", pady=8)
        ttk.Label(left, text="Tip: Keep contrast high and border ≥ 4 for reliable scanning.", foreground="#444").grid(sticky="w")

        # Preview
        topbar = ttk.Frame(right)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.columnconfigure(0, weight=1)

        self.lbl_status = ttk.Label(topbar, text="Ready")
        self.lbl_status.grid(row=0, column=0, sticky="w")
        ttk.Button(topbar, text="Open Docs", command=lambda: webbrowser.open("https://www.qrcode.com/en/about/standards.html")).grid(row=0, column=1, sticky="e")

        self.canvas = tk.Canvas(right, bg="#f4f4f6")
        self.canvas.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.canvas.bind("<Configure>", lambda e: self._debounce.schedule(self._update_preview))

    def _pick_color(self, var: tk.StringVar):
        initial = var.get()
        try:
            rgb = core.parse_color(initial)
            init_hex = rgb_to_hex(rgb)
        except Exception:
            init_hex = initial if initial else "#000000"
        color = colorchooser.askcolor(color=init_hex, parent=self)
        if color and color[1]:
            var.set(color[1])
            self._update_preview()

    def _wire_events(self):
        for var in [
            self.var_text, self.var_style, self.var_ec, self.var_version,
            self.var_fg, self.var_bg, self.var_gradient, self.var_fg2,
            self.var_label, self.var_label_pos,
        ]:
            var.trace_add("write", lambda *_: self._debounce.schedule(self._update_preview))
        for sld in [
            self.var_radius, self.var_border, self.var_size, self.var_padding,
            self.var_frame_radius, self.var_frame_pad, self.var_label_pad, self.var_font_size,
        ]:
            sld.trace_add("write", lambda *_: self._debounce.schedule(self._update_preview))

    def _render_current(self) -> Image.Image:
        text = self.var_text.get().strip()
        border = int(float(self.var_border.get()))
        size = int(float(self.var_size.get()))
        radius = float(self.var_radius.get())
        padding = int(float(self.var_padding.get()))

        ec = self.var_ec.get()
        version_str = self.var_version.get().strip()
        version = None
        if version_str:
            try:
                v = int(version_str)
                if 1 <= v <= 40:
                    version = v
            except Exception:
                pass

        mat = core.build_qr_matrix(text or " ", ec_level=ec, version=version, border=border)

        opt = core.RenderOptions(
            size=size,
            style=self._normalize_style(self.var_style.get()),
            radius=radius,
            fg=core.parse_color(self.var_fg.get()),
            bg=core.parse_color(self.var_bg.get()),
            gradient=self.var_gradient.get(),
            gradient_to=core.parse_color(self.var_fg2.get()),
            padding_px=padding,
        )

        img = core.render_qr(mat, opt)

        if self.var_frame.get() or self.var_label.get().strip():
            fopt = core.FrameOptions(
                enabled=bool(self.var_frame.get()),
                label=self.var_label.get().strip() or None,
                label_pos=self.var_label_pos.get(),
                frame_bg=core.parse_color(self.var_frame_bg.get()),
                frame_border=(None if (self.var_frame_border.get().strip().lower() == "none") else core.parse_color(self.var_frame_border.get())),
                frame_radius=int(float(self.var_frame_radius.get())),
                pad=int(float(self.var_frame_pad.get())),
                label_pad=int(float(self.var_label_pad.get())),
                label_color=core.parse_color(self.var_label_color.get()),
                font_size=int(float(self.var_font_size.get())),
                font_path=None,
            )
            img = core.add_frame(img, fopt)

        return img

    def _normalize_style(self, s: str) -> str:
        s = s.lower().strip()
        # 'continuous' means rounded modules without visible joins
        if s == "continuous":
            return "rounded"
        if s == "rounded-continuous":
            return "bars-h"
        return s

    def _update_preview(self):
        try:
            img = self._render_current()
            self._preview_img = img
            # Fit to canvas while keeping aspect
            cw = self.canvas.winfo_width() or 600
            ch = self.canvas.winfo_height() or 600
            scale = min(cw / img.width, ch / img.height, 1.0)
            disp = img if scale >= 0.999 else img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
            self._img_tk = ImageTk.PhotoImage(disp)
            self.canvas.delete("all")
            x = (cw - disp.width) // 2
            y = (ch - disp.height) // 2
            self.canvas.create_image(x, y, anchor="nw", image=self._img_tk)
            self.lbl_status.config(text=f"{img.width}x{img.height} | EC={self.var_ec.get()} | style={self.var_style.get()}")
        except Exception as e:
            self.canvas.delete("all")
            self.lbl_status.config(text=f"Error: {e}")

    def _save_png(self):
        try:
            path = filedialog.asksaveasfilename(
                parent=self,
                title="Save QR PNG",
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("All Files", "*.*")],
                initialfile="qr.png",
            )
            if not path:
                return
            img = self._render_current()
            img.save(path)
            self.lbl_status.config(text=f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))


if __name__ == "__main__":
    app = QRGUI()
    app.mainloop()