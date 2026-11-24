"""Optional Pillow-backed visual QA and non-destructive image optimization."""
from __future__ import annotations
from pathlib import Path


def _pillow():
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return None
    return Image, ImageChops, ImageStat


def compare_images(reference: Path, actual: Path, *, tolerance: float = 0.02) -> dict:
    if not 0 <= tolerance <= 1:
        raise ValueError('tolerance must be in [0, 1]')
    pkg = _pillow()
    if pkg is None:
        return {'status': 'blocked', 'reason': 'Pillow missing; install pillow to compare screenshots'}
    Image, ImageChops, ImageStat = pkg
    with Image.open(reference) as r, Image.open(actual) as a:
        if r.size != a.size:
            return {'status':'failed','reason':'different_dimensions','reference':list(r.size),'actual':list(a.size)}
        if r.width * r.height > 24_000_000:
            raise ValueError('Screenshot pixel limit exceeded')
        diff = ImageChops.difference(r.convert('RGBA'), a.convert('RGBA'))
        means = ImageStat.Stat(diff).mean
        mae = sum(means) / (len(means) * 255.0)
        return {'status':'passed' if mae <= tolerance else 'failed',
                'mae':round(mae,8), 'tolerance':tolerance, 'dimensions':list(r.size),
                'note':'Pixel MAE only; not semantic, motion, color profile or accessibility verification'}


def optimize_image(source: Path, dest: Path, *, quality: int = 85, approve: bool = False) -> dict:
    if not 1 <= quality <= 100:
        raise ValueError('quality must be between 1 and 100')
    source, dest = source.resolve(), dest.resolve()
    if source == dest:
        raise ValueError('Must not overwrite original')
    if dest.exists():
        raise FileExistsError('Destination exists')
    pkg = _pillow()
    if pkg is None:
        return {'status':'blocked','reason':'Pillow missing; install pillow'}
    if source.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'} or dest.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
        raise ValueError('Unsupported image format')
    with pkg[0].open(source) as img:
        if img.width*img.height > 36_000_000:
            raise ValueError('Image pixel limit exceeded')
        if dest.suffix.lower() in {'.jpg','.jpeg'} and img.mode in {'RGBA','LA','P'}:
            raise ValueError('JPEG cannot safely preserve transparency')
        if not approve:
            return {'status':'dry-run','source':str(source),'destination':str(dest),
                    'source_bytes':source.stat().st_size,'quality':quality,'required':'--approve'}
        dest.parent.mkdir(parents=True, exist_ok=True)
        opts = {'optimize':True}
        if dest.suffix.lower() in {'.jpg','.jpeg','.webp'}:
            opts['quality'] = quality
        img.save(dest, **opts)
        size = dest.stat().st_size
        return {'status':'completed','source_bytes':source.stat().st_size,'output_bytes':size,
                'saved_bytes':source.stat().st_size-size,'source':str(source),'output':str(dest),
                'note':'Visually review optimized output before adopting'}
