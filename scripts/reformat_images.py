"""
This is a generalized image file format converter. 
It works for JPEG, PNG, GIF, TIFF, BMP, and WEBP.
"""

from pathlib import Path
from PIL import Image, UnidentifiedImageError, ImageOps
from typing import Tuple

# Map extension -> Pillow format name
FORMAT_MAP = {
    '.jpg': 'JPEG', '.jpeg': 'JPEG', '.jpe': 'JPEG',
    '.png': 'PNG',
    '.gif': 'GIF',
    '.tif': 'TIFF', '.tiff': 'TIFF',
    '.bmp': 'BMP',
    '.webp': 'WEBP',
}

def _normalize_ext(ext: str) -> str:
    ext = str(ext)
    if not ext:
        return ''
    return ('.' + ext.lstrip('.')).lower()

def convert_image_file(
    src: Path | str,
    dest_ext: str,
    overwrite: bool = False,
    quality: int = 100,
    background: Tuple[int,int,int] = (255,255,255),
    keep_exif: bool = True,
    dry_run: bool = False
) -> Path:
    """
    Convert an image file to a different format.

    Args:
        src (Path | str): Path to the file you want to reformat (including extension).
        dest_ext (str): Output extension (e.g. ".jpg").
        overwrite (bool, optional): If True, overwrite existing output if file of same path exists. Defaults to False.
        quality (int, optional): JPEG/WEBP output quality (0–100). Defaults to 100 (full quality).
        background (Tuple[int, int, int], optional): RGB background for transparency. Defaults to [255,255,255] (white)
        keep_exif (bool, optional): If True, preserve EXIF metadata. Defaults to True.
        dry_run (bool, optional): If True, simulate conversion without writing. Defaults to False.

    Returns:
        Path: Path to the converted image.
    """
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(src)
    dest_ext = _normalize_ext(dest_ext)
    if dest_ext not in FORMAT_MAP:
        raise ValueError(f"Unsupported target extension: {dest_ext}")

    dest = src.with_suffix(dest_ext)
    if dest.exists() and not overwrite:
        raise FileExistsError(f"{dest} exists (use overwrite=True)")

    fmt = FORMAT_MAP[dest_ext]

    try:
        with Image.open(src) as im:
            # Respect EXIF orientation
            im = ImageOps.exif_transpose(im)
            src_format = im.format  # for logging / decisions

            # Handle conversion to JPEG (no alpha) - composite if needed
            if fmt == 'JPEG':
                if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                    # create RGB background and paste using alpha channel as mask
                    rgba = im.convert('RGBA')
                    alpha = rgba.split()[-1]
                    bg = Image.new('RGB', rgba.size, background)
                    bg.paste(rgba, mask=alpha)
                    out_im = bg
                else:
                    out_im = im.convert('RGB')
            else:
                # For other formats keep a suitable mode; Pillow will handle conversion
                out_im = im

            save_kwargs = {}
            if fmt == 'JPEG':
                save_kwargs['quality'] = int(quality)
                if keep_exif and 'exif' in getattr(im, 'info', {}):
                    save_kwargs['exif'] = im.info['exif']

            if dry_run:
                print(f"DRY RUN: would save {src.name} -> {dest.name} as {fmt}")
                return dest

            # Save (if GIF with multiple frames you'll only save current frame unless you handle it specially)
            out_im.save(dest, fmt, **save_kwargs)

    except UnidentifiedImageError:
        raise UnidentifiedImageError(f"Cannot identify image file {src}")
    except Exception:
        # On failure, remove half-written output if present
        if dest.exists():
            try:
                dest.unlink()
            except Exception:
                pass
        raise

    # Optionally remove original if conversion produced a different extension
    if dest.suffix.lower() != src.suffix.lower():
        try:
            src.unlink()
        except Exception as e:
            print(f"Warning: couldn't remove original {src}: {e}")

    return dest

def convert_images_in_dir(
    directory: Path | str,
    old_type: str,
    new_type: str,
    overwrite: bool = False,
    quality: int = 100,
    background: Tuple[int,int,int] = (255,255,255),
    keep_exif: bool = True,
    dry_run: bool = False
):
    """
    Convert images of a specified format in a directory to a different format.

    Args:
        directory (Path | str): Path to the directory containing files requiring reformatting.
        old_type (str): input extension you want to change from (e.g. ".png").
        new_type (str): output extension you want to change to (e.g. ".webp").
        overwrite (bool, optional): If True, overwrites existing files of the same output path. Defaults to False.
        quality (int, optional): JPEG/WEBP output quality. Defaults to 100 (full quality).
        background (Tuple[int, int, int], optional): RGB background for transparency. Defaults to [255,255,255] (white)
        keep_exif (bool, optional): If True, preserve EXIF metadata. Defaults to True.
        dry_run (bool, optional): If True, simulate conversion without writing. Defaults to False.
    """
    p = Path(directory)
    if not p.is_dir():
        raise NotADirectoryError(f"{p} is not a directory")

    old = _normalize_ext(old_type)
    new = _normalize_ext(new_type)
    if new not in FORMAT_MAP:
        raise ValueError(f"Unsupported destination extension: {new}")

    for entry in p.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() != old:
            continue

        try:
            dest = convert_image_file(
                entry,
                dest_ext=new,
                overwrite=overwrite,
                quality=quality,
                background=background,
                keep_exif=keep_exif,
                dry_run=dry_run
            )
            print(f"OK: {entry.name} -> {dest.name}")
        except FileExistsError as e:
            print(f"SKIP: {entry.name}: {e}")
        except UnidentifiedImageError:
            print(f"SKIP: {entry.name}: cannot identify as image")
        except Exception as e:
            print(f"ERROR: {entry.name}: {e}")
