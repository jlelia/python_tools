"""
QR Code Generator with styles, colors (including rainbow), and optional framed label.

Features
- Scannable QR generation from input text/URL
- Styles: squares, circles, rounded, continuous (rounded modules, no joins), rounded-continuous, bars-v
- Colors: solid foreground/background, 2-color gradients (h/v/diag), rainbow
- Optional frame with label (top/bottom), adjustable padding and colors

Usage (CLI)
  python qr_gen_cli.py --text "https://example.com" --out qr.png \
	--style rounded-continuous --gradient rainbow --label "Example" --frame

Note
- For best scanning, keep strong contrast and include at least 4-module border (quiet zone).
- Styles that connect modules (continuous) remain scannable with adequate contrast and border.
"""

from __future__ import annotations

import argparse
import colorsys
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

try:
	import qrcode
	from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
except Exception as e:  # pragma: no cover - nicer message if missing
	raise SystemExit(
		"Missing dependency 'qrcode'. Install with: pip install qrcode[pil]"
	) from e

try:
	from PIL import Image, ImageDraw, ImageFont
except Exception as e:  # pragma: no cover
	raise SystemExit(
		"Missing dependency 'Pillow'. Install with: pip install pillow"
	) from e


# --------------------------- Utility helpers ---------------------------

Color = Tuple[int, int, int]


def parse_color(value: str) -> Color:
	"""Parse a color string (#RRGGBB, rgb(r,g,b), or named PIL color) to RGB tuple.
	Falls back to PIL's color parsing if needed.
	"""
	v = value.strip()
	if v.startswith("#") and len(v) in (4, 7):
		if len(v) == 4:  # #rgb -> #rrggbb
			r = int(v[1] * 2, 16)
			g = int(v[2] * 2, 16)
			b = int(v[3] * 2, 16)
			return (r, g, b)
		return (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))
	if v.lower().startswith("rgb(") and v.endswith(")"):
		parts = v[4:-1].split(",")
		r, g, b = [int(p.strip()) for p in parts]
		return (r, g, b)
	# Try PIL
	img = Image.new("RGB", (1, 1))
	draw = ImageDraw.Draw(img)
	try:
		draw.rectangle([0, 0, 0, 0], fill=v)
		return img.getpixel((0, 0))
	except Exception as _:
		raise argparse.ArgumentTypeError(f"Invalid color: {value}")


def lerp(a: float, b: float, t: float) -> float:
	return a + (b - a) * t


def lerp_color(c1: Color, c2: Color, t: float) -> Color:
	return (
		int(lerp(c1[0], c2[0], t)),
		int(lerp(c1[1], c2[1], t)),
		int(lerp(c1[2], c2[2], t)),
	)


def hex_color(c: Color) -> str:
	return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def relative_luminance(c: Color) -> float:
	# https://www.w3.org/TR/WCAG20/#relativeluminancedef
	def chan(u: float) -> float:
		u = u / 255.0
		return u / 12.92 if u <= 0.03928 else ((u + 0.055) / 1.055) ** 2.4

	r, g, b = c
	return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(c1: Color, c2: Color) -> float:
	L1, L2 = sorted([relative_luminance(c1), relative_luminance(c2)], reverse=True)
	return (L1 + 0.05) / (L2 + 0.05)


# --------------------------- QR generation ---------------------------


EC_MAP = {
	"L": ERROR_CORRECT_L,
	"M": ERROR_CORRECT_M,
	"Q": ERROR_CORRECT_Q,
	"H": ERROR_CORRECT_H,
}


def build_qr_matrix(text: str, ec_level: str = "M", version: int | None = None, border: int = 4) -> List[List[bool]]:
	qr = qrcode.QRCode(
		version=version,  # None -> fit automatically
		error_correction=EC_MAP.get(ec_level.upper(), ERROR_CORRECT_M),
		box_size=1,
		border=0,  # we draw our own quiet zone
	)
	qr.add_data(text)
	qr.make(fit=(version is None))
	matrix = qr.get_matrix()  # type: ignore[assignment]

	# Add quiet zone (border modules)
	if border and border > 0:
		w = len(matrix[0])
		pad_row = [False] * (w + 2 * border)
		padded = [pad_row[:] for _ in range(border)]
		for row in matrix:
			padded.append([False] * border + list(row) + [False] * border)
		padded.extend([pad_row[:] for _ in range(border)])
		return padded
	return [list(r) for r in matrix]


# --------------------------- Rendering ---------------------------


@dataclass
class RenderOptions:
	size: int = 1024
	style: str = "squares"  # squares|circles|rounded|continuous|rounded-continuous|bars-h|bars-v
	radius: float = 0.3  # rounded corners as fraction of module size (for rounded, rounded-continuous)
	fg: Color = (0, 0, 0)
	bg: Color = (255, 255, 255)
	gradient: str = "none"  # none|h|v|diag|rainbow
	gradient_to: Color | None = None
	padding_px: int = 0  # extra pixel padding around the QR (beyond quiet zone)


def _module_rect(i: int, j: int, mpx: int) -> Tuple[int, int, int, int]:
	x0 = j * mpx
	y0 = i * mpx
	return (x0, y0, x0 + mpx, y0 + mpx)


def _row_runs(row: Sequence[bool]) -> Iterable[Tuple[int, int]]:
	start = None
	for j, v in enumerate(row):
		if v and start is None:
			start = j
		elif not v and start is not None:
			yield (start, j - 1)
			start = None
	if start is not None:
		yield (start, len(row) - 1)


def _col_runs(mat: List[List[bool]], j: int) -> Iterable[Tuple[int, int]]:
	start = None
	for i in range(len(mat)):
		v = mat[i][j]
		if v and start is None:
			start = i
		elif not v and start is not None:
			yield (start, i - 1)
			start = None
	if start is not None:
		yield (start, len(mat) - 1)


def _compute_color(x: int, y: int, W: int, H: int, opt: RenderOptions) -> Color:
	if opt.gradient == "none":
		return opt.fg
	if opt.gradient == "rainbow":
		# Diagonal rainbow by default for visual interest
		t = (x + y) / float(W + H)
		r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(t, 1.0, 0.95)]
		return (r, g, b)

	if opt.gradient_to is None:
		return opt.fg

	if opt.gradient == "h":
		t = x / float(W)
	elif opt.gradient == "v":
		t = y / float(H)
	elif opt.gradient == "diag":
		t = (x + y) / float(W + H)
	else:
		t = 0.0
	return lerp_color(opt.fg, opt.gradient_to, t)


def render_qr(matrix: List[List[bool]], opt: RenderOptions) -> Image.Image:
	h_modules = len(matrix)
	w_modules = len(matrix[0])

	# choose integer module pixel size to fit within opt.size
	mpx = max(1, min(opt.size // w_modules, opt.size // h_modules))
	W = w_modules * mpx
	H = h_modules * mpx

	img = Image.new("RGB", (W + 2 * opt.padding_px, H + 2 * opt.padding_px), color=opt.bg)
	draw = ImageDraw.Draw(img)

	# precompute radius in pixels
	rr = max(0, min(0.5, opt.radius)) * mpx

	style = opt.style.lower()
	if style in ("dots", "dot"):
		style = "circles"
	if style == "rounded-continuous":
		style = "bars-h"

	# render
	for i, row in enumerate(matrix):
		for j, v in enumerate(row):
			if not v:
				continue
			x0, y0, x1, y1 = _module_rect(i, j, mpx)
			# account for extra padding
			x0 += opt.padding_px
			y0 += opt.padding_px
			x1 += opt.padding_px
			y1 += opt.padding_px

			# color at module center
			cx = (x0 + x1) // 2
			cy = (y0 + y1) // 2
			col = _compute_color(cx, cy, img.width, img.height, opt)

			if style == "squares":
				draw.rectangle([x0, y0, x1, y1], fill=col)
			elif style == "circles":
				pad = max(1, int(0.1 * mpx))
				draw.ellipse([x0 + pad, y0 + pad, x1 - pad, y1 - pad], fill=col)
			elif style == "rounded":
				if rr <= 0:
					draw.rectangle([x0, y0, x1, y1], fill=col)
				else:
					draw.rounded_rectangle([x0, y0, x1, y1], radius=int(rr), fill=col)
			elif style == "continuous":
				# Rounded modules with a slight inset so adjacent modules don't visually connect
				pad = max(1, int(0.1 * mpx))
				r = int(rr if rr > 0 else 0.25 * mpx)
				draw.rounded_rectangle([x0 + pad, y0 + pad, x1 - pad, y1 - pad], radius=r, fill=col)
			else:
				# bars-h or bars-v handled after this loop for efficiency
				pass

	if style in ("bars-h", "bars-v"):
		# Clear what we may have drawn (none so far) and redraw only bars
		img = Image.new("RGB", (W + 2 * opt.padding_px, H + 2 * opt.padding_px), color=opt.bg)
		draw = ImageDraw.Draw(img)

		if style == "bars-h":
			for i, row in enumerate(matrix):
				for (j0, j1) in _row_runs(row):
					x0, y0, _, _ = _module_rect(i, j0, mpx)
					_, _, x1, y1 = _module_rect(i, j1, mpx)
					x0 += opt.padding_px
					y0 += opt.padding_px
					x1 += opt.padding_px
					y1 += opt.padding_px
					cx = (x0 + x1) // 2
					cy = (y0 + y1) // 2
					col = _compute_color(cx, cy, img.width, img.height, opt)
					# rounded ends for "rounded-continuous" effect if rr>0
					r = int(rr) if rr > 0 else 0
					if r > 0:
						draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=col)
					else:
						draw.rectangle([x0, y0, x1, y1], fill=col)
		else:  # bars-v
			for j in range(w_modules):
				for (i0, i1) in _col_runs(matrix, j):
					x0, y0, _, _ = _module_rect(i0, j, mpx)
					_, _, x1, y1 = _module_rect(i1, j, mpx)
					x0 += opt.padding_px
					y0 += opt.padding_px
					x1 += opt.padding_px
					y1 += opt.padding_px
					cx = (x0 + x1) // 2
					cy = (y0 + y1) // 2
					col = _compute_color(cx, cy, img.width, img.height, opt)
					r = int(rr) if rr > 0 else 0
					if r > 0:
						draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=col)
					else:
						draw.rectangle([x0, y0, x1, y1], fill=col)

	return img


# --------------------------- Framing & Label ---------------------------


@dataclass
class FrameOptions:
	enabled: bool = False
	label: str | None = None
	label_pos: str = "bottom"  # top|bottom
	frame_bg: Color = (255, 255, 255)
	frame_border: Color | None = (220, 220, 220)
	frame_radius: int = 24
	pad: int = 32  # padding inside frame (px)
	label_pad: int = 16  # padding around label text
	label_color: Color = (0, 0, 0)
	font_size: int = 28
	font_path: str | None = None


def add_frame(img: Image.Image, fopt: FrameOptions) -> Image.Image:
	if not fopt.enabled and not fopt.label:
		return img

	# Load font
	font = None
	if fopt.font_path:
		try:
			font = ImageFont.truetype(fopt.font_path, fopt.font_size)
		except Exception:
			font = None
	if font is None:
		try:
			font = ImageFont.truetype("arial.ttf", fopt.font_size)
		except Exception:
			font = ImageFont.load_default()

	# Compute label area
	label_h: int = 0
	label_text = (fopt.label or "").strip()
	if label_text:
		# Measure text using a temporary draw context
		tmp_img = Image.new("RGB", (10, 10))
		tmp_draw = ImageDraw.Draw(tmp_img)
		bbox = tmp_draw.textbbox((0, 0), label_text, font=font)
		text_w = int(bbox[2] - bbox[0])
		text_h = int(bbox[3] - bbox[1])
		label_h = int(text_h + 2 * fopt.label_pad)

	# New canvas size
	W = int(img.width + 2 * fopt.pad)
	H = int(img.height + 2 * fopt.pad + (label_h if label_text else 0))
	out = Image.new("RGB", (W, H), color=fopt.frame_bg)
	draw = ImageDraw.Draw(out)

	# Rounded frame rectangle
	if fopt.frame_radius > 0:
		draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=fopt.frame_radius, fill=fopt.frame_bg)
	if fopt.frame_border is not None:
		draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=fopt.frame_radius, outline=fopt.frame_border, width=2)

	# Paste QR image
	qx = int(fopt.pad)
	qy = int(fopt.pad if fopt.label_pos == "bottom" else (fopt.pad + label_h))
	out.paste(img, (qx, qy))

	# Draw label
	if label_text:
		tx = W // 2
		if fopt.label_pos == "bottom":
			ty = img.height + fopt.pad + (fopt.label_pad // 2)
		else:  # top
			ty = fopt.label_pad // 2
		draw.text((tx, ty), label_text, fill=fopt.label_color, font=font, anchor="ma")

	return out


# --------------------------- CLI ---------------------------


def build_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(description="Generate a stylized QR code image.")
	p.add_argument("--text", required=True, help="Text/URL to encode")
	p.add_argument("--out", required=True, help="Output image path (PNG recommended)")
	p.add_argument("--size", type=int, default=1024, help="Output image size in pixels (approx)")
	p.add_argument("--border", type=int, default=4, help="Quiet zone size in modules (>=4 recommended)")
	p.add_argument("--ec", choices=["L", "M", "Q", "H"], default="M", help="Error correction level")
	p.add_argument("--version", type=int, default=None, help="QR version (1-40). Omit for auto fit")

	p.add_argument(
		"--style",
		default="squares",
		choices=[
			"squares",
			"circles",
			"dots",
			"rounded",
			"continuous",
			"rounded-continuous",
			"bars-h",
			"bars-v",
		],
		help="Rendering style",
	)
	p.add_argument("--radius", type=float, default=0.3, help="Rounded corner radius as fraction of module size")

	p.add_argument("--fg", type=parse_color, default="#000000", help="Foreground color (modules)")
	p.add_argument("--bg", type=parse_color, default="#ffffff", help="Background color")
	p.add_argument(
		"--gradient",
		choices=["none", "h", "v", "diag", "rainbow"],
		default="none",
		help="Gradient mode for foreground color",
	)
	p.add_argument("--fg2", type=parse_color, default=None, help="Second color for 2-stop gradient (used when gradient != none/rainbow)")

	p.add_argument("--padding", type=int, default=0, help="Extra pixel padding around QR (outside quiet zone)")

	p.add_argument("--frame", action="store_true", help="Wrap QR in a rounded frame")
	p.add_argument("--label", type=str, default=None, help="Optional label text to add in frame")
	p.add_argument("--label-pos", choices=["top", "bottom"], default="bottom", help="Label position in frame")
	p.add_argument("--frame-bg", type=parse_color, default="#ffffff", help="Frame background color")
	p.add_argument("--frame-border", type=parse_color, default="#dcdcdc", help="Frame border color (or 'none')")
	p.add_argument("--frame-radius", type=int, default=24, help="Frame corner radius in px")
	p.add_argument("--frame-pad", type=int, default=32, help="Inner frame padding in px")
	p.add_argument("--label-pad", type=int, default=16, help="Padding around label text in px")
	p.add_argument("--label-color", type=parse_color, default="#000000", help="Label text color")
	p.add_argument("--font-size", type=int, default=28, help="Label font size")
	p.add_argument("--font-path", type=str, default=None, help="Path to TTF/OTF font file")

	return p


def main(argv: List[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)

	# Build matrix with quiet zone
	mat = build_qr_matrix(args.text, ec_level=args.ec, version=args.version, border=args.border)

	# Render options
	opt = RenderOptions(
		size=args.size,
		style=args.style,
		radius=args.radius,
		fg=args.fg,
		bg=args.bg,
		gradient=args.gradient,
		gradient_to=args.fg2,
		padding_px=args.padding,
	)

	# Quick contrast check (approx)
	# For gradient we sample mid-point only
	sample_fg = opt.fg if opt.gradient in ("none", "rainbow") else lerp_color(opt.fg, opt.gradient_to or opt.fg, 0.5)
	cr = contrast_ratio(sample_fg, opt.bg)
	if cr < 2.0:  # WCAG recommends >=3 for large text; for QR, higher is safer
		print(
			f"Warning: Low contrast ({cr:.2f}). QR may be hard to scan. Consider darker fg or lighter bg."
		)

	img = render_qr(mat, opt)

	# Frame/label
	fopt = FrameOptions(
		enabled=bool(args.frame or args.label),
		label=args.label,
		label_pos=args.label_pos,
		frame_bg=args.frame_bg,
	frame_border=args.frame_border,
		frame_radius=args.frame_radius,
		pad=args.frame_pad,
		label_pad=args.label_pad,
		label_color=args.label_color,
		font_size=args.font_size,
		font_path=args.font_path,
	)
	if fopt.enabled or fopt.label:
		img = add_frame(img, fopt)

	# Save (PNG recommended to preserve sharp edges)
	out_path = args.out
	img.save(out_path)
	print(f"Saved QR to: {out_path}")
	return 0


if __name__ == "__main__":  # pragma: no cover
	raise SystemExit(main())

