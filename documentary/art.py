"""Draw the storyboard as original, layered storybook illustrations."""

from dataclasses import dataclass
from math import cos, sin
from random import Random

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter

W, H = 1280, 720
PALETTES = {
    # Air, light, distant terrain, near terrain, shadow and highlight.
    "dawn": ("#353e59", "#e7aa81", "#85788d", "#675662", "#332e43", "#f9d29c"),
    "amber": ("#563946", "#e3ad77", "#9b715d", "#745551", "#3b2b39", "#f8d49a"),
    "gold": ("#334b55", "#e7bc87", "#9b947e", "#6e7160", "#3c4443", "#fbdb9c"),
    "rose": ("#45394f", "#e1a49e", "#a07c84", "#735766", "#3b303f", "#f0c3a3"),
    "storm": ("#253649", "#a4a8ad", "#697785", "#4b5867", "#293441", "#d4cfb4"),
    "night": ("#1c293e", "#79808e", "#5e647b", "#42475c", "#282738", "#f8d797"),
    "mist": ("#405362", "#c2bfaa", "#8d9993", "#697978", "#3d4b52", "#eee2bb"),
    "sage": ("#304c50", "#d7caa0", "#8a9b85", "#607b6c", "#334d49", "#efe0b0"),
}

INK = "#372d37"
PAPER = "#dfbd88"
CREAM = "#f3d6a6"


@dataclass
class Brush:
    draw: ImageDraw.ImageDraw
    x: float
    y: float
    scale: float

    def xy(self, pair):
        x, y = pair
        return self.x + x * self.scale, self.y + y * self.scale

    def polygon(self, points, color):
        self.draw.polygon([self.xy(pair) for pair in points], fill=color)

    def line(self, points, color, width=1):
        self.draw.line(
            [self.xy(pair) for pair in points],
            fill=color, width=max(1, round(width * self.scale)), joint="curve",
        )

    def box(self, bounds, color, radius=0):
        x1, y1, x2, y2 = bounds
        self.draw.rounded_rectangle(
            (*self.xy((x1, y1)), *self.xy((x2, y2))), radius * self.scale, fill=color
        )

    def oval(self, x, y, rx, ry, color):
        self.draw.ellipse((*self.xy((x-rx, y-ry)), *self.xy((x+rx, y+ry))), fill=color)

    def child(self, x, y, scale=1):
        return Brush(self.draw, *self.xy((x, y)), self.scale * scale)


def arch(b, width, height, color):
    radius = width / 2
    b.box((-radius, -height + radius, radius, 0), color)
    b.oval(0, -height + radius, radius, radius, color)


def church(b, kind):
    basilica = kind == "basilica"
    w, h = (74, 71) if basilica else (47, 52)
    b.polygon([(w, 0), (w+45, -21), (w+45, -h-16), (w, -h)], "#835f58")
    b.polygon([(-w, -h), (0, -h-36), (w, -h), (w+45, -h-16), (42, -h-52)], "#75534e")
    b.polygon([(-w, 0), (-w, -h), (0, -h-32), (w, -h), (w, 0)], "#bc9576")
    b.line([(-w, -h), (0, -h-35), (w, -h)], "#efd1a3", 3)
    for y in range(-h+7, -3, 10):
        b.line([(-w+3, y), (-w+17, y)], "#947361")
        b.line([(w-22, y+4), (w-4, y+4)], "#d5ac8b")
    arch(b, 18, 30, "#5a4547")
    b.oval(0, -h-8, 7, 7, "#76585b")
    b.oval(0, -h-8, 3, 3, "#e6b77d")
    if basilica:
        b.box((w+20, -120, w+49, -22), "#bc987a")
        b.polygon([(w+17, -120), (w+35, -142), (w+53, -120)], "#6c4d4c")
        arch(b.child(w+34, -97), 12, 18, "#5e4650")
    elif kind == "porziuncola":
        b.box((-26, -h-3, 26, -h+12), "#8a7167")
        b.oval(0, -h+5, 5, 6, "#d6be9c")
    b.line([(0, -h-50), (0, -h-35)], CREAM, 2)
    b.line([(-5, -h-45), (5, -h-45)], CREAM, 2)


def town(b):
    for x, y, w, h in ((-118,-5,34,42),(-83,0,40,56),(-42,1,34,43),
                       (-13,-5,45,68),(31,0,39,52),(75,2,35,36),(107,4,27,30)):
        c = b.child(x, y)
        c.box((-w/2,-h,w/2,0), "#a88370")
        c.polygon([(-w/2-3,-h),(0,-h-11),(w/2+3,-h)], "#644955")
        for dx in (-8, 7):
            c.box((dx,-h+10,dx+4,-h+19), "#efbe88")
        c.box((-4,-11,4,0), "#634e55")
    b.box((-28,-91,-4,-15), "#987664")
    b.polygon([(-31,-91),(-16,-105),(-1,-91)], "#684956")
    b.box((-19,-84,-13,-73), "#f1c58a")


def tree(b, cypress=False):
    b.oval(0, 0, 38 if not cypress else 21, 5, "#39423f")
    b.line([(-3,0),(2,-44),(-4,-82)], "#66534d", 9)
    if cypress:
        b.polygon([(-18,-20),(-22,-51),(-13,-89),(0,-133),(14,-87),
                   (20,-55),(15,-22),(3,-13)], "#374f44")
        b.line([(0,-113),(-7,-72),(-9,-35)], "#7b8a69", 2)
        return
    for x, y in ((-27,-65),(28,-73),(-4,-87),(-42,-78),(43,-86)):
        b.line([(0,-33),(x*.5,-56),(x,y)], "#8f7663", 4)
        b.oval(x,y,28,13,"#5d735c")
        b.oval(x-4,y-5,23,10,"#8f9a70")
        for dx, dy in ((-13,-2),(-4,-7),(9,-5),(15,1)):
            b.line([(x+dx,y+dy),(x+dx+6,y+dy-3)], "#b5b68b", 2)


def person(b, kind):
    colors = {
        "friar": ("#755440","#a77956"), "speaker": ("#755440","#a77956"),
        "worker": ("#755440","#a77956"), "kneeler": ("#755440","#a77956"),
        "sitter": ("#795b4b","#b18a65"), "beggar": ("#62696c","#88918c"),
        "youth": ("#8d4d47","#c27d5d"), "friend": ("#54706c","#839484"),
        "merchant": ("#63485d","#a47780"), "woman": ("#4b5864","#788a92"),
        "bishop": ("#875363","#bd866d"), "rider": ("#647381","#9a9da0"),
        "sultan": ("#44716b","#7eab93"),
    }
    robe, rim = colors[kind]
    seated = kind in ("kneeler", "sitter", "beggar")
    height = 35 if seated else 70
    b.oval(0, 1, 32, 6, INK)
    b.polygon([(-14,-height+6),(-21,-height+22),(-29,-4),(-17,1),(25,-1),
               (20,-height+23),(10,-height+5)], robe)
    if seated:
        b.polygon([(-26,-3),(-18,-24),(14,-23),(37,-4),(18,0)], robe)
        b.line([(8,-19),(23,-13),(30,-6)], rim, 3)
    b.line([(-15,-height+25),(-19,-10)], rim, 2)
    if kind in ("friar", "speaker", "worker", "kneeler"):
        b.line([(-18,-height+32),(16,-height+29),(9,-height+7)], PAPER, 2)
    b.oval(0,-height-8,13,17,INK)
    b.oval(3,-height-7,10,13,"#cf9873")
    b.polygon([(-12,-height-16),(-4,-height-24),(10,-height-20),(12,-height-15),
               (0,-height-16),(-3,-height+1),(7,-height+7),(-13,-height+7)], robe)
    b.line([(-10,-height+1),(-9,-height-14),(0,-height-20)], rim, 2)
    if kind == "bishop":
        b.polygon([(-12,-height-16),(0,-height-39),(12,-height-16)], CREAM)
        b.line([(0,-height-33),(0,-height-19)], "#ae7957", 2)
    if kind == "sultan":
        b.oval(1,-height-22,15,8,CREAM)
        b.line([(-10,-height-22),(10,-height-19)], PAPER, 2)
    if kind in ("speaker", "worker", "beggar", "kneeler"):
        y = -height + (8 if kind == "speaker" else 19)
        b.line([(12,-height+16),(22,-height+23),(35,y)], rim, 8)
        b.oval(37,y,4,4,"#d6a281")
    else:
        b.line([(-13,-height+15),(-18,-height+30),(-13,-height+40)], rim, 6)
        b.oval(-12,-height+40,4,4,"#d6a281")


def cross(b):
    b.box((-5,-107,5,0),"#6a483c",2)
    b.box((-34,-84,34,-74),"#8d624c",2)
    b.line([(-2,-106),(-2,-4)],"#c3986d",2)
    b.line([(-31,-81),(29,-81)],"#c3986d",2)


def bird_flock(b):
    for x,y,s in ((-63,6,.8),(-37,-10,1),(0,-19,1.05),(33,-1,.7),(64,-26,.9),(98,-18,.64)):
        bird = b.child(x,y,s)
        bird.polygon([(-17,-5),(-7,-5),(0,0),(9,-7),(18,-8),(10,-1),(1,4),(-8,1)], CREAM)


def book(b):
    b.polygon([(-44,-11),(-35,-34),(-4,-28),(0,-24),(31,-35),(46,-14),(1,1)], "#744c45")
    b.polygon([(-39,-13),(-31,-33),(-2,-27),(-2,-3)], CREAM)
    b.polygon([(1,-25),(29,-33),(40,-15),(2,-3)], PAPER)
    for y in (-22,-17,-12):
        b.line([(-27,y-3),(-6,y)], "#a8896b")
        b.line([(7,y),(28,y-6)], "#97795e")


def structure(b, name):
    if name in {"chapel","porziuncola","basilica"}:
        church(b,name)
    elif name == "town":
        town(b)
    elif name == "arch":
        b.box((-61,-94,61,0),"#a48370")
        arch(b,78,83,"#5d4f56")
        for y in (-16,-32,-48,-64,-80,-92):
            b.line([(-60,y),(-39,y)], PAPER, 2)
            b.line([(39,y),(60,y)], PAPER, 2)
    elif name in {"bridge","river","path","mountain"}:
        forms = {
            "bridge":([(-83,-1),(-79,-24),(-44,-35),(20,-35),(80,-24),(83,-1)],"#a78d78"),
            "river":([(-245,56),(-168,15),(-79,-6),(41,-12),(137,-31),(229,-57),
                       (139,-21),(65,-1),(-54,15),(-119,63)],"#718e92"),
            "path":([(-132,53),(-67,15),(-24,-5),(32,-16),(52,-44),(60,-44),
                      (56,-13),(11,6),(-34,40),(-55,63)],"#a1806f"),
            "mountain":([(-172,1),(-107,-76),(-73,-82),(-17,-154),(20,-143),
                           (52,-111),(84,-116),(154,-37),(199,1)],"#68667a"),
        }
        points, color = forms[name]
        b.polygon(points,color)
        if name == "bridge":
            for x in (-50,0,50):
                arch(b.child(x,1),32,24,"#555961")
            b.line([(-78,-22),(-44,-32),(20,-32),(79,-22)], CREAM, 2)
        elif name == "mountain":
            b.polygon([(-107,-76),(-73,-82),(-17,-154),(20,-143),(31,-132),
                       (-19,-138),(-38,-107),(-55,-102)],"#a29a9d")
        elif name == "river":
            b.line([(-119,31),(-69,13),(59,-1),(159,-22)],"#a7b7aa",2)
    else:
        b.polygon([(-87,0),(-61,-47),(0,-76),(75,-46),(89,0)],"#a68168")
        b.polygon([(0,-76),(18,-2),(88,0),(75,-46)],"#705157")
        b.polygon([(-19,0),(0,-68),(17,0)],INK)
        b.line([(-87,0),(-100,0),(0,-76),(100,0)],PAPER)


def furniture(b, name):
    if name == "bars":
        b.box((-60,-112,60,0),"#252535")
        for x in range(-52,55,17):
            b.box((x,-110,x+4,0),"#836f69")
        b.line([(-58,-62),(58,-62)],"#a38978",3)
    elif name == "bed":
        b.box((-74,-40,74,0),"#765650",3)
        b.box((-76,-38,-62,6),"#936c57",3)
        b.box((62,-30,76,6),"#936c57",3)
        b.oval(-44,-37,19,8,"#e8c49c")
        b.oval(-36,-43,11,8,"#c79374")
        b.polygon([(-22,-49),(5,-42),(62,-39),(66,-7),(-27,-12)],"#867789")
        b.line([(-25,-46),(5,-38),(60,-35)],"#b8a0aa",3)
    elif name == "market":
        b.box((-60,-68,-56,0),"#79574c")
        b.box((56,-68,60,0),"#79574c")
        b.polygon([(-75,-67),(-55,-94),(51,-94),(75,-67)],"#c3876d")
        for x in (-50,-17,17,50):
            b.line([(x*.74,-94),(x,-67)],CREAM,8)
        furniture(b.child(0,-1,.83),"table")
        objects(b.child(5,-35,.65),"cloth")
    elif name == "lectern":
        b.box((-5,-74,5,0),"#90664c")
        b.polygon([(-40,-69),(-29,-90),(27,-90),(41,-69)],"#ad7d59")
        b.line([(-25,-2),(25,-2)],PAPER,4)
    elif name == "throne":
        arch(b,76,112,"#8f6369")
        arch(b,59,101,"#ad7b73")
        b.box((-52,-37,52,0),"#795347")
        b.line([(-49,-33),(50,-33)],PAPER,4)
    elif name in {"manger","cradle"}:
        b.polygon([(-53,-48),(54,-48),(38,-21),(-37,-21)],"#aa7954")
        b.line([(-50,-1),(-15,-34),(35,-3)],"#8c654c",7)
        b.line([(48,-1),(15,-34),(-32,-4)],"#8c654c",6)
        for x in range(-44,46,8):
            b.line([(x,-43),(x+6,-56),(x+12,-53)],CREAM,2)
        if name == "cradle":
            b.oval(-9,-49,11,7,"#dfab89")
            b.box((0,-53,27,-43),"#ad8680",3)
    else:
        b.box((-53,-37,54,-25),"#ac7d59",3)
        for x in (-41,36):
            b.box((x,-27,x+6,0),"#815c4d")
        b.line([(-46,-33),(46,-33)],PAPER,2)


def objects(b, name):
    if name == "book":
        book(b)
    elif name in {"cloth","cloak"}:
        for i, color in enumerate(("#976c79","#7c9390","#c98a72","#d4a879")):
            y = -3 - i*11
            b.box((-43+i*5,y-13,45-i*5,y),color,5)
            b.oval(39-i*5,y-7,6,5,PAPER)
            b.line([(-37+i*5,y-10),(34-i*5,y-10)],CREAM)
    elif name in {"basket","bowl","cup","bell"}:
        width, height = {"basket":(29,22),"bowl":(20,11),"cup":(10,17),"bell":(21,30)}[name]
        flip = -1 if name == "bell" else 1
        b.polygon([(-width*flip,-height),(width*flip,-height),(width*.65*flip,0),
                   (-width*.65*flip,0)],"#af835f")
        if name == "bell":
            b.line([(-width,0),(width,0)],CREAM,3)
            b.oval(0,2,4,4,PAPER)
        else:
            b.oval(0,-height,width,5,"#6e5148")
            if name == "basket":
                for x in range(-20,21,7):
                    b.line([(x,-height+5),(x*.76,-1)],PAPER)
            if name == "cup":
                b.oval(10,-9,6,6,PAPER)
                b.oval(10,-9,3,3,"#705151")
    elif name == "candle":
        for r, color in ((18,"#95725d"),(11,"#cc9c6f"),(6,"#efbe7b")):
            b.oval(0,-31,r,r,color)
        b.box((-5,-20,5,0),CREAM,2)
        b.polygon([(0,-46),(-5,-31),(0,-25),(4,-32)],"#ffe5a3")
    elif name in {"scroll","coins","bread"}:
        if name == "scroll":
            b.box((-29,-26,32,-3),CREAM,4)
            for y in (-21,-16,-11):
                b.line([(-20,y),(22,y)],"#a8896b")
            b.oval(-28,-15,5,12,PAPER)
            b.oval(30,-15,5,12,PAPER)
        elif name == "coins":
            for x,y in ((-17,-2),(-8,-10),(3,-5),(10,-15),(19,-2)):
                b.oval(x,y,6,3,"#e4bc76")
        else:
            b.oval(0,-9,26,11,"#bf8c5d")
            for x in (-12,-2,8):
                b.line([(x,-13),(x+5,-18)],CREAM,2)
    elif name in {"lute","shield","hammer","quill","banner"}:
        if name == "lute":
            b.oval(-12,-12,17,14,"#af7554")
            b.oval(-10,-13,5,5,INK)
            b.line([(-10,-11),(24,-48)],PAPER,5)
        elif name == "shield":
            b.polygon([(-25,-46),(25,-46),(20,-14),(0,0),(-20,-14)],"#986b65")
            b.line([(0,-43),(0,-9)],CREAM,3)
            b.line([(-16,-29),(16,-29)],CREAM,3)
        elif name == "hammer":
            b.line([(-12,0),(12,-37)],PAPER,5)
            b.polygon([(-1,-44),(6,-49),(28,-36),(22,-28)],"#73727a")
        elif name == "quill":
            b.box((-15,-13,5,0),"#79626a",2)
            b.polygon([(-5,-9),(3,-32),(33,-53),(23,-28),(10,-23)],CREAM)
            b.line([(-5,-9),(24,-43)],"#9f7f62")
        else:
            b.line([(0,0),(0,-102)],PAPER,3)
            b.polygon([(1,-98),(44,-91),(31,-80),(44,-68),(1,-70)],"#9d6570")
            b.line([(5,-93),(31,-88)],CREAM)
    elif name in {"rubble","garden","star"}:
        if name == "rubble":
            for x,y in ((-30,-6),(-14,-18),(5,-6),(23,-12),(39,-5)):
                b.polygon([(x-11,y),(x-9,y-8),(x+3,y-12),(x+11,y-6),(x+9,y)],"#a58a7e")
                b.line([(x-9,y-8),(x+3,y-12)],PAPER)
        elif name == "garden":
            for i,x in enumerate(range(-63,68,13)):
                y = -13 - (i*7)%19
                b.line([(x,0),(x+4,y)],"#9ca980",2)
                b.line([(x+2,y+8),(x-4,y+5)],"#b6ae83",2)
                b.oval(x+4,y,3,3,("#d8af83","#d9a9a1","#e5ca91")[i%3])
        else:
            b.polygon([(0,-29),(4,-5),(26,0),(4,4),(0,26),(-4,4),(-25,0),(-4,-5)],CREAM)
            b.oval(0,0,4,4,"#fff2cf")
    elif name == "seraph":
        for sign in (-1, 1):
            for height, reach in ((-34,66),(-15,81),(6,58)):
                b.polygon([(0,height+7),(sign*reach*.42,height-12),(sign*reach,height-24),
                           (sign*reach*.72,height+2),(sign*reach*.35,height+13)], "#e6bc96")
                b.line([(sign*6,height+5),(sign*reach*.92,height-20)], CREAM, 2)
        cross(b.child(0,13,.48))
        b.oval(0,-21,4,5,CREAM)
    elif name == "hearth":
        b.polygon([(-29,0),(27,0),(20,-6),(-22,-6)], "#855a4e")
        b.polygon([(-15,-5),(-12,-22),(-5,-16),(1,-40),(11,-20),(18,-22),
                   (16,-9),(7,-3)], "#e6a56f")
        b.polygon([(-4,-5),(0,-22),(7,-9),(6,-4)], CREAM)
    elif name == "moon":
        b.oval(0,0,15,15,CREAM)
        b.oval(6,-4,13,13,"#79817d")
    elif name == "horse":
        b.oval(-2,-34,43,20,"#8b6554")
        b.polygon([(21,-27),(30,-67),(47,-73),(62,-63),(61,-49),(46,-46),(35,-29)],"#8b6554")
        b.line([(32,-66),(26,-45),(19,-39)],"#b88969",5)
        b.oval(48,-63,2,2,INK)
        for x in (-30,-18,17,29):
            b.line([(x,-28),(x+3,-13),(x+1,0)],"#775447",7)
        b.line([(-40,-36),(-52,-44),(-59,-17)],"#6e4a43",6)
        b.box((-20,-48,16,-28),"#b78a73",3)
    elif name == "ship":
        b.polygon([(-82,-20),(81,-20),(57,-2),(-59,-2)],"#745450")
        b.line([(2,-19),(2,-113)],PAPER,3)
        b.polygon([(-4,-106),(-18,-72),(-61,-31),(-5,-40)],"#dfb78b")
        b.polygon([(9,-101),(18,-74),(58,-36),(9,-44)],"#edd0a0")
        b.line([(-62,3),(60,3)],"#b5b8a8",2)
    else:
        raise ValueError(f"Unknown scene element {name}")


PEOPLE = {"friar","speaker","worker","kneeler","sitter","beggar","youth","friend","merchant",
          "woman","bishop","rider","sultan"}
STRUCTURES = {"chapel","porziuncola","basilica","town","arch","bridge","river","path","mountain","tent"}
FURNITURE = {"bars","bed","market","lectern","throne","manger","cradle","table"}
SPECIAL = {"olive": tree, "cypress": lambda b: tree(b, True), "cross": cross, "birds": bird_flock}
BACKMOST = {"river","path","mountain"}


def draw_plate(setting, palette, elements, index, output):
    sky, light, far, middle, dark, highlight = PALETTES[palette]
    random = Random(1551 + index)
    # Work at full delivery size, then add restrained paper grain.
    yy, xx = np.ogrid[:H, :W]
    vertical = np.clip(yy / 560, 0, 1)[..., None]
    top, bottom = np.array(ImageColor.getrgb(sky)), np.array(ImageColor.getrgb(light))
    x_light = (342, 921, 644)[index % 3]
    falloff = np.exp(-((xx-x_light)**2 + (yy-315)**2) / (2*210**2))[..., None]
    base = top + (bottom-top)*vertical + falloff * np.array((27,18,8))
    image = Image.fromarray(np.uint8(np.clip(base, 0, 255)))
    draw = ImageDraw.Draw(image)
    b = Brush(draw, 0, 0, 1)
    if setting == "hill":
        if palette == "night":
            b.oval(x_light, 308, 22, 22, highlight)
            b.oval(x_light+8, 302, 19, 19, "#677180")
            for _ in range(48):
                x,y = random.randrange(80,1200),random.randrange(65,380)
                b.oval(x,y,1,1,"#aaa3a5")
        else:
            b.oval(x_light, 308, 25, 25, highlight)
        for layer, (height, color) in enumerate(((405,far),(474,middle),(545,dark))):
            points = [(x,height + 31*sin(x/(112+layer*32)+index/4)
                       + 16*cos(x/(59+layer*11))) for x in range(-10,W+11,8)]
            b.polygon([*points,(W+10,H),(-10,H)],color)
        for _ in range(220):
            x,y = random.randrange(W),random.randrange(450,H)
            b.line([(x,y),(x+random.randrange(2,14),y-1)], middle)
    elif setting == "street":
        b.polygon([(0,176),(239,218),(438,444),(842,444),(1041,210),(W,151),
                   (W,H),(0,H)],dark)
        for side in (0,1):
            sign = 1 if side == 0 else -1
            edge = 0 if side == 0 else W
            for i in range(3):
                x = edge + sign*i*105
                b.polygon([(x-sign*10,178+i*54),(x+sign*178,203+i*63),
                           (x+sign*178,504+i*3),(x-sign*10,570-i*4)],(far,middle,dark)[i])
                for y in (310+i*37,392+i*20):
                    arch(b.child(x+sign*86,y),27,44,sky)
        b.polygon([(0,H),(418,489),(850,489),(W,H)],middle)
        for y in (507,535,573,619,676):
            b.line([(max(0,399-(y-489)*2),y),(min(W,858+(y-489)*2),y)],far,2)
        for x in range(0,W+1,135):
            b.line([(640+(x-640)*.28,489),(x,H)],dark,2)
    elif setting == "room":
        b.box((0,217,W,535),middle)
        windows = ((97,1167),(1125,),(150,),(110,1134))[index % 4]
        for x in windows:
            arch(b.child(x,520),185,260,dark)
            arch(b.child(x,438),91,149,sky)
            arch(b.child(x,425),63,123,far)
            b.line([(x,314),(x,437)],dark,5)
            b.line([(x-46,380),(x+46,380)],dark,5)
        for y in (245,276,462,496,530):
            b.line([(0,y),(W,y)],dark,2)
            for x in range(0,W,95):
                offset = (y % 7)*10
                b.line([(x+offset,y),(x+offset,y+19)],far)
        b.polygon([(0,533),(W,533),(W,H),(0,H)],dark)
        b.polygon([(105,435),(134,435),(437,600),(312,609)],far)
        b.polygon([(1135,435),(1164,435),(981,620),(861,610)],far)
    else:
        raise ValueError(f"Unknown setting {setting}")

    # Use the authored order for interactions. Ground planes sit behind all actors.
    for name, x, y, scale in sorted(elements, key=lambda item: item[0] not in BACKMOST):
        mark = b.child(x,y,scale)
        if name in PEOPLE:
            person(mark,name)
        elif name in STRUCTURES:
            structure(mark,name)
        elif name in FURNITURE:
            furniture(mark,name)
        elif name in SPECIAL:
            SPECIAL[name](mark)
        else:
            objects(mark,name)

    image = image.filter(ImageFilter.SMOOTH)
    grain = np.random.default_rng(901+index).normal(0,1.8,(H,W,1))
    x_edge = (xx-W/2)/(W/2)
    y_edge = (yy-H/2)/(H/2)
    vignette = 1 - .10 * (x_edge*x_edge + y_edge*y_edge)
    pixels = np.asarray(image) * vignette[...,None] + grain
    Image.fromarray(np.uint8(np.clip(pixels,0,255))).save(output, compress_level=3)
