"""Bounded image decode and preprocessing; the browser preserves the original."""
import base64
import io
import re
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError
from .model import Metrics

Image.MAX_IMAGE_PIXELS = 20_000_000


def prepare_image(data_url: str) -> tuple[str, Metrics]:
    match = re.fullmatch(r'data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)', data_url)
    if not match:
        raise ValueError('Invalid image type')
    raw = base64.b64decode(match[2], validate=True)
    if len(raw) > 3_150_000:
        raise ValueError('Image too large')
    kind = match[1]
    valid = (kind == 'jpeg' and raw.startswith(b'\xff\xd8') or
             kind == 'png' and raw.startswith(b'\x89PNG\r\n\x1a\n') or
             kind == 'webp' and raw.startswith(b'RIFF') and raw[8:12] == b'WEBP')
    if not valid:
        raise ValueError('Invalid image signature')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 20_000_000 or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Unsupported image dimensions or animation')
            image.load()
            corrected = ImageOps.exif_transpose(image).convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid image') from exc
    gray = corrected.convert('L')
    gray.thumbnail((256, 256))
    values = list(gray.get_flattened_data())
    w, h = gray.size
    lap = [4 * values[y*w+x] - values[y*w+x-1] - values[y*w+x+1] - values[(y-1)*w+x] - values[(y+1)*w+x]
           for y in range(1, h-1) for x in range(1, w-1)]
    mean = sum(lap) / len(lap) if lap else 0
    sharpness = sum((n-mean)**2 for n in lap) / len(lap) if lap else 0
    metrics = Metrics(width=corrected.width, height=corrected.height,
                      brightness=ImageStat.Stat(gray).mean[0], sharpness=min(sharpness, 100000))
    corrected.thumbnail((2000, 2000))
    processed = ImageOps.autocontrast(corrected, cutoff=.5)
    output = io.BytesIO()
    processed.save(output, 'JPEG', quality=90)
    return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode(), metrics
