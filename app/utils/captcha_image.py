import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# без похожих символов: 0/O, 1/I/L
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 5

WIDTH, HEIGHT = 300, 110
FONT_SIZE = 56


def generate_code(length: int = CODE_LENGTH) -> str:
    return "".join(random.choices(ALPHABET, k=length))


def random_color(low: int, high: int) -> tuple[int, int, int]:
    return tuple(random.randint(low, high) for _ in range(3))


def render_captcha(code: str) -> bytes:
    image = Image.new("RGB", (WIDTH, HEIGHT), random_color(225, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=FONT_SIZE)

    # фоновый шум
    for _ in range(WIDTH * HEIGHT // 12):
        draw.point((random.randrange(WIDTH), random.randrange(HEIGHT)), fill=random_color(150, 230))

    # каждый символ рисуется отдельно, поворачивается и сдвигается
    step = (WIDTH - 30) // len(code)
    for index, char in enumerate(code):
        tile = Image.new("RGBA", (FONT_SIZE + 20, FONT_SIZE + 30), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((10, 5), char, font=font, fill=random_color(0, 120))
        tile = tile.rotate(random.uniform(-25, 25), resample=Image.Resampling.BICUBIC, expand=True)
        x = 15 + index * step + random.randint(-6, 6)
        y = (HEIGHT - tile.height) // 2 + random.randint(-12, 12)
        image.paste(tile, (x, y), tile)

    # перечёркивающие линии
    for _ in range(random.randint(4, 6)):
        points = [(random.randrange(WIDTH), random.randrange(HEIGHT)) for _ in range(3)]
        draw.line(points, fill=random_color(40, 160), width=random.randint(2, 3), joint="curve")

    image = image.filter(ImageFilter.SMOOTH)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
