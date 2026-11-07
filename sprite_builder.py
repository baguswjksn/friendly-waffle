#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    sys.exit("Pillow belum terpasang. Jalankan:  pip install pillow")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
SHEET = "sprite.webp"
LANCZOS = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
WEBP_MAX = 16383  # batas lebar/tinggi gambar format WebP


# --------------------------------------------------------------------------- #
# Util
# --------------------------------------------------------------------------- #
def parse_size(text: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*(?:[xX]\s*(\d+))?\s*", text)
    if not m:
        raise argparse.ArgumentTypeError("format ukuran: 96 atau 120x80")
    w, h = int(m.group(1)), int(m.group(2) or m.group(1))
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("ukuran harus > 0")
    return w, h


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "img"


def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(p))]


def num(v: float) -> int | float:
    """Bulatkan ke 4 desimal; bilangan bulat ditulis tanpa '.0'."""
    v = round(v, 4)
    return int(v) if v == int(v) else v


def human_bytes(n: int) -> str:
    return f"{n / 1048576:.2f} MB" if n >= 1048576 else f"{n / 1024:.1f} KB"


def log(*args) -> None:
    sys.stdout.flush()  # jaga urutan tampil saat stdout dan stderr sama-sama ke terminal
    print(*args, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Gambar
# --------------------------------------------------------------------------- #
@dataclass
class Item:
    name: str
    path: Path
    img: Image.Image | None = None


def collect(inputs: list[str], skip: Path) -> list[Item]:
    """skip = sheet hasil build sebelumnya, supaya tidak ikut digabung."""
    files: list[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            files += sorted((f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS),
                            key=natural_key)
        elif p.is_file():
            files.append(p)
        else:
            log(f"[peringatan] tidak ditemukan: {raw}")

    used: set[str] = set()
    items: list[Item] = []
    for f in files:
        if f.resolve() == skip:
            continue
        base = slugify(f.stem)
        name, n = base, 2
        while name in used:
            name, n = f"{base}-{n}", n + 1
        used.add(name)
        items.append(Item(name=name, path=f))
    return items


def load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as im:
        im.seek(0)  # GIF animasi: frame pertama
        im = ImageOps.exif_transpose(im)  # foto HP yang diputar via EXIF
        return im.convert("RGBA")


def fit_image(img: Image.Image, w: int, h: int, fit: str) -> Image.Image:
    # resize di mode premultiplied (RGBa) supaya tepi transparan tidak jadi hitam
    if fit == "cover":  # crop tengah sampai sel penuh
        return ImageOps.fit(img.convert("RGBa"), (w, h), LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
    r = min(w / img.width, h / img.height, 1.0)  # contain: muat utuh, tidak diperbesar
    size = (max(1, round(img.width * r)), max(1, round(img.height * r)))
    return img if size == img.size else img.convert("RGBa").resize(size, LANCZOS).convert("RGBA")


def build_sheet(items: list[Item], cw: int, ch: int) -> Image.Image:
    """Susun semua gambar dari atas ke bawah dalam satu kolom: gambar ke-i ada di y = i * ch."""
    sheet = Image.new("RGBA", (cw, ch * len(items)), (0, 0, 0, 0))
    for i, it in enumerate(items):
        sheet.alpha_composite(it.img, ((cw - it.img.width) // 2, i * ch + (ch - it.img.height) // 2))
        it.img = None  # bebaskan memori
    return sheet


# --------------------------------------------------------------------------- #
# CSS & HTML
# --------------------------------------------------------------------------- #
def build_css(items: list[Item], file: str, cw: int, ch: int) -> str:
    """Sheet vertikal berisi n gambar: background-size 100% (n*100)%, posisi ke-i = i/(n-1)*100%.
    Semuanya persen, jadi crop tetap tepat di ukuran tampil berapa pun."""
    n = len(items)
    base = ".spr{display:inline-block;vertical-align:middle;max-width:100%;background-repeat:no-repeat}"
    group = ",\n".join(f".spr-{it.name}" for it in items) + f'{{background-image:url("{file}")}}'
    rules = [f".spr-{it.name}{{width:{cw}px;aspect-ratio:{cw}/{ch};background-size:100% {n * 100}%;"
             f"background-position:0 {num(i / (n - 1) * 100) if n > 1 else 0}%}}"
             for i, it in enumerate(items)]
    return "\n\n".join([base, group, "\n".join(rules)]) + "\n"


def build_html(items: list[Item]) -> str:
    """Satu <span> per gambar; ganti aria-label dengan deskripsi gambarnya."""
    return "".join(f'<span class="spr spr-{it.name}" role="img" aria-label="{it.name}"></span>\n'
                   for it in items)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Gabung banyak gambar jadi sprite sheet + CSS (CSS sprite ala McMaster-Carr).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Contoh:" + __doc__.split("Contoh:", 1)[1],
    )
    ap.add_argument("inputs", nargs="+", help="folder dan/atau file gambar")
    ap.add_argument("--cell", type=parse_size, default=(96, 96), help="ukuran sel px, mis. 96 atau 576x324 (default 96)")
    ap.add_argument("--fit", choices=["contain", "cover"], default="contain",
                    help="contain = muat utuh; cover = crop tengah sampai penuh (default contain)")
    ap.add_argument("--quality", type=int, default=85, help="kualitas WebP 1-100, 100 = lossless (default 85)")
    args = ap.parse_args(argv)
    if not 1 <= args.quality <= 100:
        ap.error("--quality harus 1-100")

    sheet_path = Path.cwd() / SHEET
    items = collect(args.inputs, sheet_path)
    if not items:
        log("Tidak ada gambar ditemukan.")
        return 1

    cw, ch = args.cell
    original_bytes = 0
    ready: list[Item] = []
    for it in items:
        try:
            img = load_rgba(it.path)
        except Exception as exc:  # file rusak / bukan gambar
            log(f"[lewati] {it.path}: {exc}")
            continue
        it.img = fit_image(img, cw, ch, args.fit)
        original_bytes += it.path.stat().st_size
        ready.append(it)
    if not ready:
        log("Semua gambar gagal dibaca.")
        return 1

    sw, sh = cw, ch * len(ready)
    if max(sw, sh) > WEBP_MAX:
        log(f"[error] sheet {sw}x{sh}px melebihi batas WebP {WEBP_MAX}px. Dengan --cell {cw}x{ch} "
            f"maksimal {WEBP_MAX // ch} gambar; kecilkan --cell atau kurangi jumlah gambar.")
        return 1
    build_sheet(ready, cw, ch).save(sheet_path, "WEBP", quality=args.quality, method=6,
                                    lossless=args.quality >= 100)

    size = sheet_path.stat().st_size
    log(f"OK: {len(ready)} gambar -> 1 sprite sheet ({human_bytes(size)}, "
        f"asli {human_bytes(original_bytes)}), hemat {len(ready) - 1} request")
    log(f"   {sheet_path}   {sw}x{sh}px")

    log("\n== CSS: tempel ke <style> ==")
    print(build_css(ready, SHEET, cw, ch))  # print() menambah baris kosong pemisah CSS dan HTML
    log(f"== HTML: cara pakai (taruh {SHEET} satu folder dengan file HTML; "
        f'ukuran: style="width:48px" atau style="height:32px;width:auto") ==')
    print(build_html(ready), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
