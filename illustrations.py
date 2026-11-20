"""Deterministic, full-frame illustrative plates for the devotional test."""

from math import cos, sin
from random import Random

from PIL import Image, ImageColor, ImageDraw, ImageFilter

WIDTH, HEIGHT = 1280, 720
SCALE = 2

# Sky, horizon, far hills, near hills, ground, and position of the light.
PALETTES = (
    ("#343c61", "#edb384", "#82788e", "#655664", "#433b48", (286, 260)),
    ("#37474c", "#d9c48f", "#8d9177", "#626e60", "#3c4b46", (1015, 216)),
    ("#333e54", "#eda779", "#987d76", "#776261", "#4d414b", (355, 215)),
    ("#314851", "#e0cba0", "#879989", "#617c72", "#394e49", (1015, 254)),
    ("#3b3454", "#e5a994", "#9f7e89", "#78627a", "#45394a", (470, 249)),
    ("#283951", "#e2ae83", "#88788b", "#65596f", "#3e384d", (870, 222)),
)


def illustration(index: int) -> Image.Image:
    sky, horizon, far, near, ground, (sun_x, sun_y) = PALETTES[index]
    random = Random(1700 + index)
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(image)

    def point(x, y):
        return round(x * SCALE), round(y * SCALE)

    def line(points, color, width=1):
        draw.line([point(x, y) for x, y in points], fill=color, width=round(width * SCALE))

    def polygon(points, color):
        draw.polygon([point(x, y) for x, y in points], fill=color)

    def ellipse(x, y, rx, ry, color):
        draw.ellipse((*point(x - rx, y - ry), *point(x + rx, y + ry)), fill=color)

    top = ImageColor.getrgb(sky)
    bottom = ImageColor.getrgb(horizon)
    for row in range(HEIGHT * SCALE):
        t = min(1, row / (540 * SCALE))
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        draw.line((0, row, WIDTH * SCALE, row), fill=color)

    glow = Image.new("L", image.size)
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((*point(sun_x - 105, sun_y - 105), *point(sun_x + 105, sun_y + 105)), fill=210)
    image.paste("#ffdf9b", mask=glow.filter(ImageFilter.GaussianBlur(94 * SCALE)))
    ellipse(sun_x, sun_y, 32, 32, "#f9dda5")
    for _ in range(110):
        x, y = random.randrange(WIDTH), random.randrange(75, 350)
        length = random.randrange(7, 70)
        line([(x, y), (x + length, y - 2)], "#c49d8e")

    for depth, (height, color) in enumerate(((396, far), (466, near), (542, ground))):
        ridge = [
            (x, height + 27 * sin(x / (90 + depth * 40) + index) + 17 * cos(x / 55 + depth))
            for x in range(-20, WIDTH + 21, 10)
        ]
        polygon([*ridge, (WIDTH + 20, HEIGHT), (-20, HEIGHT)], color)
        for _ in range(130):
            x, y = random.randrange(WIDTH), random.randrange(height + 44, HEIGHT)
            line([(x, y), (x + random.randrange(2, 12), y - 1)], color=near if depth == 0 else far)

    def chapel(x, y, size):
        def shape(points, fill):
            polygon([(x + a * size, y + b * size) for a, b in points], fill)
        shape([(-78, 0), (-78, -65), (-21, -109), (36, -65), (36, 0)], "#574650")
        shape([(36, 0), (82, -18), (82, -75), (36, -65)], "#392f3c")
        shape([(45, -63), (45, -123), (59, -140), (73, -123), (73, -72)], "#473945")
        shape([(-13, 0), (-13, -32), (-5, -42), (5, -42), (13, -32), (13, 0)], "#f4cb8a")
        line([(x - 21 * size, y - 127 * size), (x - 21 * size, y - 99 * size)], "#574650", 3)
        line([(x - 30 * size, y - 119 * size), (x - 12 * size, y - 119 * size)], "#574650", 3)

    def cypress(x, y, height):
        polygon([(x - 14, y), (x - 17, y - height * .36), (x - 11, y - height * .74),
                 (x, y - height), (x + 10, y - height * .72), (x + 16, y - height * .3),
                 (x + 11, y)], "#303a39")
        line([(x, y - height * .85), (x - 4, y - 8)], "#596255", 2)

    if index in (0, 2, 5):
        chapel(294 if index != 5 else 984, 481, 1.12 if index == 2 else .86)
    for x in ((104, 143, 1134) if index % 2 == 0 else (134, 1118, 1168)):
        cypress(x, 558, random.randrange(110, 190))
    if index == 3:
        polygon([(900, 548), (926, 475), (942, 470), (956, 545)], "#67676b")
        polygon([(965, 548), (980, 493), (1016, 490), (1042, 548)], "#535b60")

    # Francis is fully within the picture and above the caption band.
    x, y = ((837, 405), (491, 379), (696, 390), (524, 390), (778, 370), (433, 393))[index]
    robe, light, shade = "#62453e", "#906551", "#3c3035"
    ellipse(x, y + 143, 78, 12, "#382f39")
    if index == 2:
        polygon([(x - 34, y + 25), (x - 47, y + 80), (x - 93, y + 120),
                 (x - 75, y + 139), (x + 53, y + 139), (x + 39, y + 72),
                 (x + 28, y + 26)], robe)
        line([(x + 24, y + 47), (x + 65, y + 32), (x + 72, y + 9)], light, 15)
        ellipse(x + 73, y + 8, 7, 10, "#c38f72")
        line([(x - 40, y + 105), (x - 63, y + 129)], light, 3)
    else:
        polygon([(x - 32, y + 23), (x - 42, y + 54), (x - 61, y + 138),
                 (x - 26, y + 143), (x + 60, y + 139), (x + 41, y + 52),
                 (x + 30, y + 24)], robe)
        polygon([(x + 10, y + 49), (x + 15, y + 116), (x + 31, y + 139),
                 (x + 59, y + 139), (x + 40, y + 55)], shade)
        line([(x - 27, y + 62), (x + 28, y + 65)], "#d3ac85", 3)
        line([(x + 14, y + 65), (x + 8, y + 106)], "#d3ac85", 2)
        line([(x - 25, y + 79), (x - 34, y + 133)], light, 4)
        if index in (1, 3, 4):
            line([(x + 25, y + 35), (x + 59, y + 55), (x + 94, y + 24)], light, 15)
            ellipse(x + 97, y + 23, 9, 6, "#c38f72")
        else:
            line([(x - 31, y + 37), (x - 44, y + 75)], light, 11)
            ellipse(x - 44, y + 78, 6, 8, "#c38f72")
    ellipse(x - 3, y - 4, 26, 32, shade)
    ellipse(x + 6, y - 3, 17, 23, "#c38f72")
    polygon([(x - 25, y - 1), (x - 18, y - 25), (x + 14, y - 29),
             (x + 24, y - 17), (x - 2, y - 16), (x - 5, y + 22),
             (x + 25, y + 32), (x - 20, y + 34)], robe)
    line([(x - 21, y + 12), (x - 17, y - 15), (x - 4, y - 24)], light, 3)

    if index in (1, 3, 4):
        for i in range(5):
            bx, by = x + 125 + i * 40, y - 29 - i * 17 + random.randrange(-11, 11)
            line([(bx - 13, by - 5), (bx - 6, by - 6), (bx, by),
                  (bx + 7, by - 7), (bx + 14, by - 9)], "#efe0c4", 2)

    for _ in range(360):
        gx, gy = random.randrange(WIDTH), random.randrange(549, HEIGHT)
        length = random.randrange(2, 15)
        line([(gx, gy), (gx + random.randrange(-6, 7), gy - length)],
             random.choice((ground, "#57504e", "#8c7366")))
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
