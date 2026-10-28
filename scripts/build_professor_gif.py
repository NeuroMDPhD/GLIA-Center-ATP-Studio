"""Encode the existing Professor pet's active-work row without redrawing it."""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/professor'
DURATIONS = [120, 120, 120, 120, 120, 220]


def main():
    source = ASSETS / 'source.webp'
    with Image.open(source) as opened:
        sheet = opened.convert('RGBA')
    if sheet.size != (1536, 2288):
        raise ValueError('Expected the original v2 Professor sprite sheet')
    # The v2 active-work state is row 7, columns 0–5, with 192×208 cells.
    frames = [sheet.crop((col * 192, 7 * 208, (col + 1) * 192, 8 * 208)) for col in range(6)]
    # GIF has binary transparency. Use one shared palette and reserve index 255
    # for transparent pixels to avoid background trails and palette flicker.
    strip = Image.new('RGB', (192 * len(frames), 208), '#f3f6fa')
    for col, frame in enumerate(frames):
        strip.paste(frame, (col * 192, 0), frame)
    palette = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    encoded = []
    for frame in frames:
        background = Image.new('RGBA', frame.size, '#f3f6fa')
        rgb = Image.alpha_composite(background, frame).convert('RGB')
        indexed = rgb.quantize(palette=palette, dither=Image.Dither.NONE)
        indexed.paste(255, mask=frame.getchannel('A').point(lambda a: 255 if a < 128 else 0))
        indexed.info['transparency'] = 255
        encoded.append(indexed)
    output = ASSETS / 'working.gif'
    encoded[0].save(output, save_all=True, append_images=encoded[1:], duration=DURATIONS,
                    loop=0, disposal=2, transparency=255, optimize=False)
    with Image.open(output) as gif:
        assert gif.n_frames == 6 and gif.info['loop'] == 0
    metadata = {
        'name': 'Professor', 'source_pet_id': 'pet_6abc7f9cc4188191835b7a109f4d0aa4',
        'source': 'User-selected active custom pet, downloaded through the Pets service',
        'sprite_version': 2, 'source_size_px': [1536, 2288],
        'animation': {'state': 'running (active work)', 'row_0based': 7,
                      'columns_0based': list(range(6)), 'frame_size_px': [192, 208],
                      'durations_ms': DURATIONS, 'loop': 'infinite'},
        'conversion': 'Existing pixels only; shared GIF palette, binary transparency, disposal=2. No artwork redraw.',
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, output)},
    }
    (ASSETS / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    preview = ROOT / 'docs/screenshots/professor-working.gif'
    preview.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, preview)
    print(output)


if __name__ == '__main__':
    main()
