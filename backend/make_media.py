"""Generate the cartoon lesson media: video, poster, avatars and audio.

The lesson is an animated cartoon that teaches Newton's three laws. The frames
are drawn with Pillow (flat cartoon shapes, bold outlines, speech bubbles) and
encoded to MP4 with the ffmpeg binary bundled by imageio-ffmpeg. The narration
for every supported language is spoken by a synthesised male voice (neural
text-to-speech) that explains the three laws, so the player really has one
male narration audio source per language to switch between.

Run from the backend directory:  python make_media.py
"""

import ctypes
import math
import os
import struct
import wave

from PIL import Image, ImageDraw, ImageFont

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
VIDEO_DIR = os.path.join(MEDIA_DIR, "video")
THUMB_DIR = os.path.join(MEDIA_DIR, "thumbnails")
AUDIO_DIR = os.path.join(MEDIA_DIR, "audio")
SUB_DIR = os.path.join(MEDIA_DIR, "subtitles")
CHAR_DIR = os.path.join(MEDIA_DIR, "characters")

WIDTH, HEIGHT = 960, 540
FPS = 12
DURATION = 180
FRAMES = FPS * DURATION

# Flat cartoon palette
SKY = (126, 200, 240)
SKY_DEEP = (86, 170, 220)
GRASS = (126, 200, 120)
GRASS_DEEP = (92, 170, 90)
INK = (32, 28, 46)
FOX = (240, 140, 60)
FOX_LIGHT = (252, 190, 130)
ROBOT = (140, 160, 200)
ROBOT_DARK = (100, 120, 165)
BALL = (250, 210, 90)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 80)
PURPLE = (170, 120, 220)
RED = (230, 80, 80)
TEAL = (70, 190, 190)

for folder in (MEDIA_DIR, VIDEO_DIR, THUMB_DIR, AUDIO_DIR, SUB_DIR, CHAR_DIR):
    os.makedirs(folder, exist_ok=True)


def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_HUGE = load_font(54, bold=True)
FONT_BIG = load_font(38, bold=True)
FONT_MED = load_font(28)
FONT_SMALL = load_font(22)
FONT_TINY = load_font(18)


def rounded(draw, box, radius, fill, outline=INK, width=4):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_fox(draw, cx, cy, scale=1.0, arm_angle=0.0):
    """Newton the Cartoon Fox."""
    body_w, body_h = 120 * scale, 130 * scale
    draw.ellipse(
        [cx - body_w / 2, cy - body_h / 2, cx + body_w / 2, cy + body_h / 2],
        fill=FOX,
        outline=INK,
        width=4,
    )
    # Ears
    for sign in (-1, 1):
        ex = cx + sign * 40 * scale
        ey = cy - 62 * scale
        draw.polygon(
            [
                (ex - 22 * scale, ey + 22 * scale),
                (ex, ey - 34 * scale),
                (ex + 22 * scale, ey + 22 * scale),
            ],
            fill=FOX,
            outline=INK,
        )
        draw.polygon(
            [
                (ex - 10 * scale, ey + 16 * scale),
                (ex, ey - 16 * scale),
                (ex + 10 * scale, ey + 16 * scale),
            ],
            fill=FOX_LIGHT,
        )
    # Muzzle
    draw.ellipse(
        [cx - 38 * scale, cy - 18 * scale, cx + 38 * scale, cy + 34 * scale],
        fill=FOX_LIGHT,
        outline=INK,
        width=3,
    )
    draw.ellipse(
        [cx - 9 * scale, cy - 2 * scale, cx + 9 * scale, cy + 16 * scale], fill=INK
    )
    # Eyes
    for sign in (-1, 1):
        draw.ellipse(
            [
                cx + sign * 22 * scale - 11 * scale,
                cy - 44 * scale,
                cx + sign * 22 * scale + 11 * scale,
                cy - 22 * scale,
            ],
            fill=WHITE,
            outline=INK,
            width=3,
        )
        draw.ellipse(
            [
                cx + sign * 22 * scale - 5 * scale,
                cy - 37 * scale,
                cx + sign * 22 * scale + 5 * scale,
                cy - 27 * scale,
            ],
            fill=INK,
        )
    # Arms
    for sign in (-1, 1):
        base_x = cx + sign * 55 * scale
        base_y = cy + 4 * scale
        tip_x = base_x + sign * 44 * scale
        tip_y = base_y + math.sin(arm_angle) * 26 * scale * sign
        draw.line([(base_x, base_y), (tip_x, tip_y)], fill=INK, width=int(12 * scale))
        draw.ellipse(
            [
                tip_x - 12 * scale,
                tip_y - 12 * scale,
                tip_x + 12 * scale,
                tip_y + 12 * scale,
            ],
            fill=FOX,
            outline=INK,
            width=3,
        )


def draw_robot(draw, cx, cy, scale=1.0):
    """Rocket the Robot."""
    w, h = 110 * scale, 120 * scale
    rounded(
        draw,
        [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
        int(18 * scale),
        ROBOT,
        INK,
        4,
    )
    draw.rectangle(
        [cx - w / 2, cy - h / 2, cx + w / 2, cy - h / 2 + 26 * scale], fill=ROBOT_DARK
    )
    # Antenna
    draw.line([(cx, cy - h / 2), (cx, cy - h / 2 - 26 * scale)], fill=INK, width=4)
    draw.ellipse(
        [
            cx - 10 * scale,
            cy - h / 2 - 36 * scale,
            cx + 10 * scale,
            cy - h / 2 - 16 * scale,
        ],
        fill=RED,
        outline=INK,
        width=3,
    )
    # Eyes
    for sign in (-1, 1):
        draw.ellipse(
            [
                cx + sign * 24 * scale - 15 * scale,
                cy - 22 * scale,
                cx + sign * 24 * scale + 15 * scale,
                cy + 8 * scale,
            ],
            fill=WHITE,
            outline=INK,
            width=3,
        )
        draw.ellipse(
            [
                cx + sign * 24 * scale - 6 * scale,
                cy - 12 * scale,
                cx + sign * 24 * scale + 6 * scale,
                cy + 2 * scale,
            ],
            fill=INK,
        )
    # Mouth
    draw.arc(
        [cx - 26 * scale, cy + 10 * scale, cx + 26 * scale, cy + 40 * scale],
        start=0,
        end=180,
        fill=INK,
        width=4,
    )
    # Arms
    for sign in (-1, 1):
        draw.line(
            [
                (cx + sign * w / 2, cy),
                (cx + sign * (w / 2 + 40 * scale), cy - 18 * scale),
            ],
            fill=INK,
            width=int(10 * scale),
        )
    # Legs
    for sign in (-1, 1):
        draw.line(
            [
                (cx + sign * 26 * scale, cy + h / 2),
                (cx + sign * 26 * scale, cy + h / 2 + 26 * scale),
            ],
            fill=INK,
            width=int(10 * scale),
        )


def draw_ball(draw, cx, cy, radius=34, motion=0.0):
    """Inky the Ball."""
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=BALL,
        outline=INK,
        width=4,
    )
    # Spin lines so the movement is visible.
    for i in range(3):
        angle = motion + i * 2.1
        dx = math.cos(angle) * radius * 0.5
        dy = math.sin(angle) * radius * 0.5
        draw.ellipse(
            [cx + dx - 7, cy + dy - 7, cx + dx + 7, cy + dy + 7],
            fill=WHITE,
            outline=INK,
            width=2,
        )


def draw_bubble(draw, cx, cy, text, width=430, tail_from=None):
    lines = []
    words = text.split()
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if draw.textlength(candidate, font=FONT_MED) > width - 40:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    line_height = 34
    height = len(lines) * line_height + 28
    box = [cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2]
    rounded(draw, box, 22, WHITE, INK, 4)
    for index, line in enumerate(lines):
        text_width = draw.textlength(line, font=FONT_MED)
        draw.text(
            (cx - text_width / 2, cy - height / 2 + 14 + index * line_height),
            line,
            font=FONT_MED,
            fill=INK,
        )
    if tail_from is not None:
        draw.polygon(
            [
                (cx - 14, cy + height / 2 - 4),
                (cx + 14, cy + height / 2 - 4),
                (tail_from[0], tail_from[1]),
            ],
            fill=WHITE,
            outline=INK,
            width=3,
        )


def draw_arrow(draw, start, end, color=RED, width=8, head=22):
    draw.line([start, end], fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    left = (
        end[0] - head * math.cos(angle - 0.4),
        end[1] - head * math.sin(angle - 0.4),
    )
    right = (
        end[0] - head * math.cos(angle + 0.4),
        end[1] - head * math.sin(angle + 0.4),
    )
    draw.polygon([end, left, right], fill=color, outline=INK)


def draw_title_card(draw, t):
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=SKY_DEEP)
    for i in range(9):
        x = 40 + i * 110
        draw.ellipse(
            [x - 34, 84 - 34, x + 34, 84 + 34], fill=SKY, outline=SKY_DEEP, width=2
        )
    draw.rectangle([0, 300, WIDTH, HEIGHT], fill=GRASS)
    draw.rectangle([0, 300, WIDTH, 320], fill=GRASS_DEEP)
    bounce = int(math.sin(t * 3) * 8)
    draw_fox(draw, 300, 400 + bounce, 1.05)
    draw_robot(draw, 480, 400 - bounce, 0.95)
    draw_ball(draw, 660, 400 + bounce, 38, t * 4)
    title = "NEWTON'S THREE LAWS"
    width = draw.textlength(title, font=FONT_HUGE)
    draw.text(((WIDTH - width) / 2, 140), title, font=FONT_HUGE, fill=INK)
    subtitle = "A Cartoon Adventure with Newton the Fox"
    width = draw.textlength(subtitle, font=FONT_MED)
    draw.text(((WIDTH - width) / 2, 214), subtitle, font=FONT_MED, fill=INK)


def draw_law_one(draw, t):
    """Inertia: the ball keeps moving when nobody pushes it."""
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=SKY)
    draw.rectangle([0, 380, WIDTH, HEIGHT], fill=GRASS)
    draw.rectangle([0, 380, WIDTH, 398], fill=GRASS_DEEP)
    # Track
    draw.line([(60, 470), (900, 470)], fill=INK, width=6)
    # The fox pushes once, then the ball keeps rolling on its own.
    push_phase = t < 1.6
    ball_x = 300 + min(t, 1.6) * 110 + max(t - 1.6, 0) * 46
    if push_phase:
        draw_fox(draw, ball_x - 95, 430, 0.9, arm_angle=-0.6)
        draw_arrow(draw, (ball_x - 60, 400), (ball_x - 26, 400), RED, 8, 20)
    else:
        draw_fox(draw, 160, 430, 0.85, arm_angle=0.3)
    draw_ball(draw, ball_x, 436, 36, t * 6)
    draw_arrow(draw, (ball_x + 44, 400), (ball_x + 100, 400), TEAL, 8, 20)
    draw.text((ball_x + 108, 386), "keeps going", font=FONT_SMALL, fill=INK)

    rounded(draw, [40, 30, 560, 128], 20, WHITE, INK, 4)
    draw.text((62, 46), "LAW 1: INERTIA", font=FONT_BIG, fill=INK)
    draw.text(
        (62, 92), "Things keep moving unless a force acts.", font=FONT_MED, fill=INK
    )

    bubble_y = 210
    draw_bubble(
        draw,
        720,
        bubble_y,
        "I stopped pushing you, Inky! But you kept rolling.",
        width=380,
        tail_from=(640, 430),
    )
    draw_bubble(draw, 250, 190, "That is inertia!", width=250, tail_from=(300, 400))


def draw_law_two(draw, t):
    """F = m x a: the same force moves the light thing faster."""
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=SKY)
    draw.rectangle([0, 380, WIDTH, HEIGHT], fill=GRASS)
    draw.rectangle([0, 380, WIDTH, 398], fill=GRASS_DEEP)

    heavy_x = 240 + min(t * 26, 150)
    light_x = 640 + min(t * 95, 420)

    # Heavy crate
    rounded(draw, [heavy_x - 70, 300, heavy_x + 70, 430], 10, (188, 140, 92), INK, 4)
    draw.text((heavy_x - 44, 340), "HEAVY", font=FONT_SMALL, fill=INK)
    draw_arrow(draw, (heavy_x + 74, 340), (heavy_x + 140, 340), RED, 9, 24)

    # Light balloon
    draw.ellipse(
        [light_x - 34, 250, light_x + 34, 322], fill=PURPLE, outline=INK, width=4
    )
    draw.line([(light_x, 322), (light_x, 360)], fill=INK, width=3)
    draw_arrow(draw, (light_x + 40, 290), (light_x + 100, 290), RED, 9, 24)

    draw_robot(
        draw,
        130,
        400,
        0.8,
    )

    rounded(draw, [40, 26, 640, 124], 20, WHITE, INK, 4)
    draw.text((62, 42), "LAW 2: F = m x a", font=FONT_BIG, fill=INK)
    draw.text(
        (62, 88), "Same force, more mass, less acceleration.", font=FONT_MED, fill=INK
    )

    draw.text((300, 470), "big mass = slow", font=FONT_SMALL, fill=INK)
    draw.text((700, 470), "small mass = fast", font=FONT_SMALL, fill=INK)


def draw_law_three(draw, t):
    """Action and reaction: every push gets a push back."""
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=SKY_DEEP)
    draw.rectangle([0, 400, WIDTH, HEIGHT], fill=GRASS_DEEP)
    draw.ellipse([120, 250, 260, 390], fill=(120, 180, 235), outline=INK, width=4)
    draw.ellipse([700, 250, 840, 390], fill=(235, 150, 120), outline=INK, width=4)

    rocket_x = 470 + min(t * 55, 300)
    draw_robot(draw, 470, 330, 0.7)
    # Rocket
    draw.polygon(
        [(rocket_x - 30, 300), (rocket_x + 30, 300), (rocket_x, 250)],
        fill=WHITE,
        outline=INK,
    )
    flame = 18 + int(abs(math.sin(t * 8)) * 16)
    draw.polygon(
        [(rocket_x - 18, 300), (rocket_x + 18, 300), (rocket_x, 300 + flame)],
        fill=YELLOW,
        outline=INK,
    )
    draw_arrow(draw, (rocket_x, 320), (rocket_x + 110, 320), TEAL, 9, 24)
    draw.text((rocket_x + 120, 306), "pushes the rocket", font=FONT_SMALL, fill=INK)
    draw_arrow(draw, (rocket_x - 100, 320), (rocket_x - 24, 320), RED, 9, 24)
    draw.text((rocket_x - 250, 306), "rocket pushes back", font=FONT_SMALL, fill=INK)

    rounded(draw, [40, 26, 660, 124], 20, WHITE, INK, 4)
    draw.text((62, 42), "LAW 3: ACTION - REACTION", font=FONT_BIG, fill=INK)
    draw.text(
        (62, 88),
        "Every force has an equal force the other way.",
        font=FONT_MED,
        fill=INK,
    )

    draw_bubble(
        draw, 480, 190, "Forces always come in pairs!", width=380, tail_from=(470, 280)
    )


def draw_outro(draw, t):
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=SKY_DEEP)
    draw.rectangle([0, 320, WIDTH, HEIGHT], fill=GRASS)
    draw.rectangle([0, 320, WIDTH, 338], fill=GRASS_DEEP)
    bounce = int(math.sin(t * 3.4) * 10)
    draw_fox(draw, 250, 420 + bounce, 1.0)
    draw_robot(draw, 480, 420 - bounce, 0.95)
    draw_ball(draw, 700, 420 + bounce, 38, t * 5)
    draw.text((240, 90), "NOW YOU KNOW NEWTON'S", font=FONT_BIG, fill=WHITE)
    draw.text((210, 140), "THREE LAWS OF MOTION!", font=FONT_HUGE, fill=YELLOW)
    draw.text(
        (300, 220),
        "Inertia  -  F = m x a  -  Action & Reaction",
        font=FONT_MED,
        fill=WHITE,
    )


def render_frame(index):
    t = index / FPS
    image = Image.new("RGB", (WIDTH, HEIGHT), SKY)
    draw = ImageDraw.Draw(image)
    if t < 6:
        draw_title_card(draw, t)
    elif t < 60:
        draw_law_one(draw, t - 6)
    elif t < 120:
        draw_law_two(draw, t - 60)
    elif t < 170:
        draw_law_three(draw, t - 120)
    else:
        draw_outro(draw, t - 170)
    return image


def build_video():
    import imageio.v2 as imageio
    import numpy as np

    path = os.path.join(VIDEO_DIR, "newtons-laws.mp4")
    writer = imageio.get_writer(
        path,
        fps=FPS,
        codec="libx264",
        quality=8,
        macro_block_size=16,
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )
    for index in range(FRAMES):
        writer.append_data(np.asarray(render_frame(index)))
    writer.close()
    print("wrote", path)


def build_poster():
    image = render_frame(int(FPS * 8))
    draw = ImageDraw.Draw(image)
    rounded(draw, [330, 240, 760, 330], 18, WHITE, INK, 4)
    draw.text((358, 258), "LAW 1: INERTIA", font=FONT_BIG, fill=INK)
    path = os.path.join(THUMB_DIR, "newtons-laws-poster.png")
    image.save(path)
    print("wrote", path)


def build_avatars():
    specs = [
        ("newton-fox.png", "fox"),
        ("inky-ball.png", "ball"),
        ("rocket-robot.png", "robot"),
    ]
    for name, kind in specs:
        image = Image.new("RGB", (256, 256), SKY)
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 190, 256, 256], fill=GRASS)
        if kind == "fox":
            draw_fox(draw, 128, 120, 0.95)
        elif kind == "ball":
            draw_ball(draw, 128, 128, 62, 1.0)
        else:
            draw_robot(draw, 128, 120, 0.95)
        path = os.path.join(CHAR_DIR, name)
        image.save(path)
        print("wrote", path)


# Male narration voices, one per lesson language: gTTS language/accent pair.
# gTTS has no Luxembourgish voice, so the German voice reads the
# Luxembourgish script - the closest available voice. Every voice is
# pitch-deepened with ffmpeg so the narrator sounds male.
TTS_VOICES = {
    "en": ("en", "com.au"),
    "es": ("es", "es"),
    "fr": ("fr", "fr"),
    "de": ("de", "de"),
    "lb": ("de", "de"),
    "pt": ("pt", "pt"),
}

# The male voice explains the three laws of motion in every language.
NARRATIONS = {
    "en": (
        "Hello! I am Newton the Fox, and today we will learn my three laws of motion. "
        "Law one: inertia. An object at rest stays at rest, and an object in motion "
        "keeps moving, unless a force acts on it. Watch Inky the Ball: I push him once, "
        "and he keeps rolling all by himself! "
        "Law two: force equals mass times acceleration. The same push moves the light "
        "balloon fast, but the heavy crate hardly moves at all. More mass means less "
        "acceleration for the same force. "
        "Law three: for every action there is an equal and opposite reaction. The rocket "
        "pushes the flames down, and the flames push the rocket up! Forces always come "
        "in pairs. Now you know Newton's three laws of motion. Well done!"
    ),
    "es": (
        "Hola! Soy Newton el Zorro, y hoy aprenderemos mis tres leyes del movimiento. "
        "Ley uno: la inercia. Un objeto en reposo sigue en reposo, y un objeto en "
        "movimiento sigue moviendose, a menos que una fuerza actue sobre el. Miren a "
        "Inky la Pelota: la empujo una vez, y sigue rodando sola! "
        "Ley dos: la fuerza es igual a la masa por la aceleracion. El mismo empujon "
        "mueve rapido el globo ligero, pero la caja pesada casi no se mueve. Mas masa "
        "significa menos aceleracion con la misma fuerza. "
        "Ley tres: a cada accion corresponde una reaccion igual y opuesta. El cohete "
        "empuja las llamas hacia abajo, y las llamas empujan el cohete hacia arriba! "
        "Las fuerzas siempre vienen en pares. Ya conocen las tres leyes de Newton! "
        "Bien hecho!"
    ),
    "fr": (
        "Bonjour! Je suis Newton le Renard, et aujourd'hui nous allons apprendre mes "
        "trois lois du mouvement. Loi numero un: l'inertie. Un objet au repos reste au "
        "repos, et un objet en mouvement continue a bouger, sauf si une force agit sur "
        "lui. Regardez Inky la Balle: je la pousse une seule fois, et elle continue a "
        "rouler toute seule! "
        "Loi numero deux: la force egale la masse fois l'acceleration. La meme poussee "
        "deplace vite le ballon leger, mais la lourde caisse bouge a peine. Plus de "
        "masse signifie moins d'acceleration pour la meme force. "
        "Loi numero trois: a chaque action correspond une reaction egale et opposee. "
        "La fusee pousse les flammes vers le bas, et les flammes poussent la fusee vers "
        "le haut! Les forces vont toujours par paires. Vous connaissez maintenant les "
        "trois lois de Newton. Bravo!"
    ),
    "de": (
        "Hallo! Ich bin Newton der Fuchs, und heute lernen wir meine drei "
        "Bewegungsgesetze. Gesetz eins: die Traegheit. Ein ruhender Koerper bleibt in "
        "Ruhe, und ein bewegter Koerper bewegt sich weiter, wenn keine Kraft auf ihn "
        "wirkt. Schaut euch Inky den Ball an: Ich stosse ihn einmal an, und er rollt "
        "ganz von allein weiter! "
        "Gesetz zwei: Kraft ist gleich Masse mal Beschleunigung. Derselbe Stoss bewegt "
        "den leichten Luftballon schnell, aber die schwere Kiste bewegt sich kaum. Mehr "
        "Masse bedeutet weniger Beschleunigung bei gleicher Kraft. "
        "Gesetz drei: Zu jeder Wirkung gibt es eine gleiche, entgegengesetzte "
        "Gegenwirkung. Die Rakete stoest die Flammen nach unten, und die Flammen "
        "stossen die Rakete nach oben! Kraefte treten immer paarweise auf. Jetzt kennt "
        "ihr Newtons drei Bewegungsgesetze. Gut gemacht!"
    ),
    "lb": (
        "Hallo! Ech sinn den Newton de Fuuss, an haut leiere mir meng drei "
        "Beweegungsgesetzer. Gesetz eent: d'Traegheet. E Kierper a Rou bleift a Rou, "
        "an e Kierper a Beweegung beweegt sech weider, wann keng Kraaft op hien "
        "wierkt. Kuckt iech den Inky de Ball un: Ech stoussen hien eemol un, an hien "
        "rullt ganz eleng weider! "
        "Gesetz zwee: Kraaft ass glaich Mass mol Beschleunegung. Dee selwechte Stouss "
        "beweegt de liichte Ballon seier, mei dei schweiier Kescht beweegt sech kaum. "
        "Mei Mass bedeit manner Beschleunegung bei derselwechter Kraaft. "
        "Gesetz drei: Zu all Wierkung gett et eng glaich, entgeintgesate "
        "Geigewierkung. D'Rakeit steisst d'Flamen no ennen, an d'Flamen stoussen "
        "d'Rakeit no uewen! Kraeften trieden emmer a Koppelen op. Elo kennt Dir dem "
        "Newton seng drei Beweegungsgesetzer. Gutt gemaach!"
    ),
    "pt": (
        "Ola! Eu sou o Newton, a Raposa, e hoje vamos aprender as minhas tres leis do "
        "movimento. Lei um: a inercia. Um objeto em repouso permanece em repouso, e um "
        "objeto em movimento continua a mover-se, a menos que uma forca aja sobre ele. "
        "Vejam o Inky, a Bola: empurro-o uma vez, e ele continua a rolar sozinho! "
        "Lei dois: a forca e igual a massa vezes a aceleracao. O mesmo empurrao move "
        "rapido o balao leve, mas a caixa pesada quase nao se move. Mais massa "
        "significa menos aceleracao para a mesma forca. "
        "Lei tres: a cada acao corresponde uma reacao igual e oposta. O foguetao "
        "empurra as chamas para baixo, e as chamas empurram o foguetao para cima! As "
        "forcas surgem sempre aos pares. Agora ja conhecem as tres leis de Newton. "
        "Muito bem!"
    ),
}


def _build_audio_fallback():
    """A narration-ish tone bed per language, so the switch stays audible.

    Used only when the neural text-to-speech service cannot be reached; the
    normal output is the male voice narration built by build_audio.
    """
    import numpy as np

    rate = 22050
    specs = [
        ("en", 261.63, 0.0),
        ("es", 293.66, 0.15),
        ("fr", 329.66, 0.30),
        ("de", 311.13, 0.10),
        ("lb", 349.23, 0.20),
        ("pt", 392.00, 0.05),
    ]
    for code, base, detune in specs:
        samples = np.zeros(rate * DURATION, dtype=np.float32)
        time_axis = np.arange(len(samples)) / rate
        for index in range(DURATION):
            start = index * rate
            end = min(start + rate, len(samples))
            segment_t = time_axis[start:end] - start / rate
            # A little melody that changes every 2 seconds.
            note = base * (1.0 + detune) * (2 ** (index % 4) / 2)
            envelope = 0.28 * (0.5 + 0.5 * math.sin(index))
            wave_data = envelope * (
                0.6 * np.sin(2 * np.pi * note * segment_t)
                + 0.25 * np.sin(2 * np.pi * note * 1.5 * segment_t)
                + 0.15 * np.sin(2 * np.pi * note * 0.5 * segment_t)
            )
            samples[start:end] = wave_data
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
        path = os.path.join(AUDIO_DIR, f"newtons-laws-{code}.mp3")
        # imageio-ffmpeg ships an ffmpeg binary; use it to write the mp3.
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        import subprocess

        raw_path = os.path.join(AUDIO_DIR, f"newtons-laws-{code}.wav")
        with wave.open(raw_path, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(rate)
            handle.writeframes(pcm.tobytes())
        subprocess.run(
            [exe, "-y", "-i", raw_path, "-codec:a", "libmp3lame", "-b:a", "96k", path],
            check=True,
            capture_output=True,
        )
        os.remove(raw_path)
        print("wrote", path)


def build_audio():
    """Male voice narration per language, explaining the three laws.

    Each language gets a male-sounding narration mp3 reading that language's
    script (synthesised TTS, pitch-deepened so it sounds like a male teacher).
    The 3-minute lesson video plays the chosen language's mp3 alongside it, so
    switching the audio language switches the voice the students hear. Falls
    back to a tone bed only when TTS is unreachable.
    """
    import subprocess
    import tempfile

    try:
        from gtts import gTTS
    except ImportError:
        _build_audio_fallback()
        return

    def _masculinise(raw_path, out_path):
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        stretched = os.path.join(AUDIO_DIR, "tmp-masculine.mp3")
        subprocess.run(
            [
                exe, "-y", "-i", raw_path,
                "-filter:a",
                # Lower the pitch ~15% for a male-sounding voice, then pad/trim
                # to the full lesson length so the narration covers the video.
                f"asetrate=44100*0.87,aresample=44100,apad=whole_dur={DURATION},atrim=0:{DURATION}",
                "-b:a", "96k", stretched,
            ],
            check=True,
            capture_output=True,
        )
        os.replace(stretched, out_path)
        print("wrote", out_path)

    try:
        for code, text in NARRATIONS.items():
            lang, tld = TTS_VOICES[code]
            path = os.path.join(AUDIO_DIR, f"newtons-laws-{code}.mp3")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                raw = tmp.name
            try:
                gTTS(text, lang=lang, tld=tld, slow=False).save(raw)
                _masculinise(raw, path)
            finally:
                if os.path.exists(raw):
                    os.remove(raw)
    except Exception as exc:
        print("TTS failed, using tone fallback:", exc)
        _build_audio_fallback()


def build_subtitles():
    texts = {
        "en": [
            (0, 6, "Newton's Three Laws of Motion - a cartoon adventure"),
            (
                6,
                20,
                "Law 1: Inertia. An object stays at rest or in motion unless a force acts on it.",
            ),
            (
                20,
                36,
                "I stopped pushing you, Inky, but you kept rolling. That is inertia!",
            ),
            (
                36,
                60,
                "Inertia is why a bus full of people lurches forward when the brakes kick in.",
            ),
            (60, 78, "Law 2: Force equals mass times acceleration. F = m x a."),
            (
                78,
                100,
                "The same push moves the light balloon quickly, but the heavy crate barely moves.",
            ),
            (100, 120, "More mass means less acceleration for the very same force."),
            (
                120,
                140,
                "Law 3: For every action there is an equal and opposite reaction.",
            ),
            (
                140,
                170,
                "The rocket pushes the flame down, and the flame pushes the rocket up.",
            ),
            (170, 180, "Now you know Newton's three laws of motion!"),
        ],
        "es": [
            (0, 6, "Las tres leyes de Newton - una aventura de dibujos animados"),
            (
                6,
                20,
                "Ley 1: Inercia. Un objeto quieto o en movimiento sigue igual si no actua una fuerza.",
            ),
            (20, 36, "Deje de empujarte, Inky, pero seguiste rodando. Eso es inercia!"),
            (
                36,
                60,
                "La inercia explica por que un bus lleno de personas se inclina al frenar.",
            ),
            (60, 78, "Ley 2: Fuerza igual a masa por aceleracion. F = m x a."),
            (
                78,
                100,
                "El mismo empuje mueve rapido el globo ligero, pero apenas mueve la caja pesada.",
            ),
            (100, 120, "Mas masa significa menos aceleracion para la misma fuerza."),
            (
                120,
                140,
                "Ley 3: A cada accion corresponde una reaccion igual y opuesta.",
            ),
            (
                140,
                170,
                "El cohete empuja la llama hacia abajo, y la llama empuja el cohete hacia arriba.",
            ),
            (170, 180, "Ahora ya conoces las tres leyes de Newton!"),
        ],
        "fr": [
            (0, 6, "Les trois lois de Newton - une aventure cartoon"),
            (
                6,
                20,
                "Loi 1: L'inertie. Un objet reste au repos ou en mouvement sans force agissante.",
            ),
            (
                20,
                36,
                "J'ai arrete de te pousser, Inky, mais tu as continue a rouler. C'est l'inertie!",
            ),
            (36, 60, "L'inertie explique pourquoi un bus bondit quand il freine."),
            (60, 78, "Loi 2: Force egale a la masse fois l'acceleration. F = m x a."),
            (
                78,
                100,
                "La meme poussee deplace vite le ballon leger, mais a peine la caisse lourde.",
            ),
            (
                100,
                120,
                "Plus de masse signifie moins d'acceleration pour la meme force.",
            ),
            (
                120,
                140,
                "Loi 3: A chaque action correspond une reaction egale et opposee.",
            ),
            (
                140,
                170,
                "La fusee pousse la flamme vers le bas, et la flamme pousse la fusee vers le haut.",
            ),
            (170, 180, "Vous connaissez maintenant les trois lois de Newton!"),
        ],
        "de": [
            (0, 6, "Newtons drei Bewegungsgesetze - ein Cartoon-Abenteuer"),
            (
                6,
                20,
                "Gesetz 1: Traegheit. Ein Koerper bleibt in Ruhe oder Bewegung, wenn keine Kraft wirkt.",
            ),
            (
                20,
                36,
                "Ich habe dich nicht mehr geschubst, Inky, aber du bist weitergerollt. Das ist Traegheit!",
            ),
            (
                36,
                60,
                "Traegheit erklaert, warum ein voller Bus beim Bremsen nach vorne stuerzt.",
            ),
            (60, 78, "Gesetz 2: Kraft ist gleich Masse mal Beschleunigung. F = m x a."),
            (
                78,
                100,
                "Derselbe Stoss bewegt den leichten Ballon schnell, aber die schwere Kiste kaum.",
            ),
            (100, 120, "Mehr Masse bedeutet weniger Beschleunigung bei gleicher Kraft."),
            (
                120,
                140,
                "Gesetz 3: Zu jeder Wirkung gehoert eine gleiche, entgegengesetzte Gegenwirkung.",
            ),
            (
                140,
                170,
                "Die Rakete stoest die Flammen nach unten, und die Flammen stossen die Rakete nach oben.",
            ),
            (170, 180, "Jetzt kennt ihr Newtons drei Bewegungsgesetze!"),
        ],
        "lb": [
            (0, 6, "Dem Newton seng drei Beweegungsgesetzer - en Cartoon-Abenteuer"),
            (
                6,
                20,
                "Gesetz 1: D'Traegheet. E Kierper bleift a Rou oder Beweegung, wann keng Kraaft wierkt.",
            ),
            (
                20,
                36,
                "Ech hunn dech net mei gestouss, Inky, mee du bass weidergerullt. Dat ass Traegheet!",
            ),
            (
                36,
                60,
                "D'Traegheet erkläert, firwat e volle Bus beim Bremsen no vir faellt.",
            ),
            (60, 78, "Gesetz 2: Kraaft ass glaich Mass mol Beschleunegung. F = m x a."),
            (
                78,
                100,
                "Dee selwechte Stouss beweegt de liichte Ballon seier, mei d'schweiier Kescht kaum.",
            ),
            (100, 120, "Mei Mass bedeit manner Beschleunegung bei derselwechter Kraaft."),
            (
                120,
                140,
                "Gesetz 3: Zu all Wierkung gehéiert eng glaich, entgéintgesate Geigewierkung.",
            ),
            (
                140,
                170,
                "D'Rakeit steisst d'Flamen no ennen, an d'Flamen stoussen d'Rakeit no uewen.",
            ),
            (170, 180, "Elo kennt Dir dem Newton seng drei Beweegungsgesetzer!"),
        ],
        "pt": [
            (0, 6, "As tres leis de Newton - uma aventura de desenhos animados"),
            (
                6,
                20,
                "Lei 1: Inercia. Um objeto permanece em repouso ou movimento se nenhuma forca agir.",
            ),
            (
                20,
                36,
                "Deixei de te empurrar, Inky, mas continuaste a rolar. Isso e inercia!",
            ),
            (
                36,
                60,
                "A inercia explica por que um autocarro cheio se inclina ao travar.",
            ),
            (60, 78, "Lei 2: Forca igual a massa vezes aceleracao. F = m x a."),
            (
                78,
                100,
                "O mesmo empurrao move rapido o balao leve, mas quase nao move a caixa pesada.",
            ),
            (100, 120, "Mais massa significa menos aceleracao para a mesma forca."),
            (
                120,
                140,
                "Lei 3: A cada acao corresponde uma reacao igual e oposta.",
            ),
            (
                140,
                170,
                "O foguetao empurra as chamas para baixo, e as chamas empurram o foguetao para cima.",
            ),
            (170, 180, "Agora ja conhecem as tres leis de Newton!"),
        ],
    }
    for code, cues in texts.items():
        lines = ["WEBVTT", ""]
        for index, (start, end, text) in enumerate(cues, start=1):

            def stamp(value):
                hours, rest = divmod(value, 3600)
                minutes, seconds = divmod(rest, 60)
                return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.000"

            lines.append(str(index))
            lines.append(f"{stamp(start)} --> {stamp(end)}")
            lines.append(text)
            lines.append("")
        path = os.path.join(SUB_DIR, f"newtons-laws-{code}.vtt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        print("wrote", path)


if __name__ == "__main__":
    build_video()
    build_poster()
    build_avatars()
    build_audio()
    build_subtitles()
    print("media generation complete")
