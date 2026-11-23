#!/usr/bin/env python3
"""GEM RUSH — Day 1 vs Day 7. A tiny agent-built arcade game, rendered as a
vertical TikTok video (1080x1920, 24 fps, 18 s) by drawing every frame with
PIL and encoding with ffmpeg. Fully deterministic: no network, no clock, no
randomness. Output: $MAKEFUN_OUTPUT_DIR/entry.mp4 (else <repo>/output/entry.mp4).

Game: a miner jumps to grab a falling gem. The SAME simulated moment is
rendered twice — Day 1 (grey, minimal, one mechanic) and Day 7 (colour,
particles, combo, upgrades) — camera still, identical coordinates.
"""
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
DUR = 18.0
NFRAMES = int(DUR * FPS)  # 432

GROUND_Y = 1500
MINER_X = 540
MINER_W, MINER_H = 120, 120
GEM_START_Y = 260
GEM_FALL_SPEED = 620.0
JUMP_T0, JUMP_DUR, JUMP_H = 1.0, 0.9, 300.0
GRAB_T = 1.45
GRAB_Y = 1080

PLAY_CODE = "makefun-boot-rhubarb-tulip"


# ---------------------------------------------------------------- fonts
def load_font(size, bold=True):
    """Font ladder: DejaVu Bold -> DejaVu -> any sorted system ttf ->
    PIL default font scaled up (chunky but legible, always available)."""
    cands = []
    if bold:
        cands.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    cands.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    for p in cands:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    try:
        import glob
        for p in sorted(glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    except Exception:
        pass
    base = ImageFont.load_default()
    return _ScaledFont(base, max(1, size // 11))


class _ScaledFont:
    """Wraps PIL's bitmap default font so text() can render it large."""

    def __init__(self, base, scale):
        self.base = base
        self.scale = scale

    def getbbox(self, text):
        b = self.base.getbbox(text)
        return (b[0] * self.scale, b[1] * self.scale,
                b[2] * self.scale, b[3] * self.scale)

    def getlength(self, text):
        return self.base.getlength(text) * self.scale


def draw_text_scaled(d, xy, text, font, fill):
    """Draw text; if the font is a _ScaledFont, render small then upscale."""
    if isinstance(font, _ScaledFont):
        s = font.scale
        tmp = Image.new("RGBA", (int(font.base.getlength(text)) + 8, 24), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((2, 2), text, font=font.base, fill=fill)
        tmp = tmp.resize((tmp.width * s, tmp.height * s), Image.NEAREST)
        d._image.paste(tmp, (xy[0], xy[1]), tmp)
        return
    d.text(xy, text, font=font, fill=fill)


def text_size(font, text):
    if isinstance(font, _ScaledFont):
        b = font.base.getbbox(text)
        return ((b[2] - b[0]) * font.scale, (b[3] - b[1]) * font.scale)
    b = font.getbbox(text)
    return (b[2] - b[0], b[3] - b[1])


def center_text(d, cx, y, text, font, fill):
    w, _ = text_size(font, text)
    draw_text_scaled(d, (cx - w // 2, y), text, font, fill)
    return w


# ---------------------------------------------------------------- sim
def sim(t):
    """Deterministic game state at segment time t (seconds, 0..5).
    Returns dict: miner_top (feet y), gem_y, grabbed, score, combo."""
    # Miner jump: parabola peaking at u=0.5
    if JUMP_T0 <= t <= JUMP_T0 + JUMP_DUR:
        u = (t - JUMP_T0) / JUMP_DUR
        lift = JUMP_H * 4 * u * (1 - u)
    else:
        lift = 0.0
    miner_top = GROUND_Y - MINER_H - lift
    grabbed = t >= GRAB_T
    if grabbed:
        # gem rides the miner's hand down, then rests at grab height
        gem_y = GRAB_Y - lift if t <= JUMP_T0 + JUMP_DUR else GRAB_Y
    else:
        gem_y = GEM_START_Y + GEM_FALL_SPEED * t
    score = 0
    if grabbed:
        score = min(120, int((t - GRAB_T) / 1.0 * 120))
    return {"miner_top": miner_top, "gem_y": gem_y, "grabbed": grabbed,
            "score": score, "combo": 5 if grabbed else 0, "lift": lift}


def particle_pos(i, dt):
    """Deterministic burst particle i at dt seconds after grab."""
    ang = i * 2.399963  # golden angle
    speed = 120 + (i * 53) % 260
    d = speed * dt
    return (MINER_X + math.cos(ang) * d, GRAB_Y + math.sin(ang) * d - 40 * dt)


PARTICLE_COLORS = [(250, 204, 21), (244, 114, 182), (74, 222, 128),
                   (56, 189, 248), (251, 146, 60), (192, 132, 252)]

# ---------------------------------------------------------------- backgrounds
def build_day1_bg():
    img = Image.new("RGB", (W, H), (43, 43, 43))
    d = ImageDraw.Draw(img)
    # faint dot grid + a few grey platform blocks: the frame must not read
    # as dead air, while staying flat grey and minimal
    for gx in range(60, W, 120):
        for gy in range(60, GROUND_Y - 60, 120):
            d.ellipse([gx - 3, gy - 3, gx + 3, gy + 3], fill=(56, 56, 56))
    d.rectangle([120, 900, 360, 930], fill=(64, 64, 64))
    d.rectangle([720, 700, 960, 730], fill=(64, 64, 64))
    d.rectangle([120, 1150, 300, 1180], fill=(64, 64, 64))
    d.rectangle([0, GROUND_Y, W, H], fill=(58, 58, 58))
    d.rectangle([0, GROUND_Y, W, GROUND_Y + 8], fill=(70, 70, 70))
    return img


def build_day7_bg():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top, bot = (30, 58, 138), (125, 211, 252)
    bands = 96
    for i in range(bands):
        f = i / (bands - 1)
        col = tuple(int(top[c] + (bot[c] - top[c]) * f) for c in range(3))
        y0 = int(i * H / bands)
        y1 = int((i + 1) * H / bands)
        d.rectangle([0, y0, W, y1], fill=col)
    # sun + rays
    d.ellipse([820, 180, 980, 340], fill=(253, 224, 71))
    for k in range(8):
        a = k * math.pi / 4
        x0 = 900 + int(math.cos(a) * 95)
        y0 = 260 + int(math.sin(a) * 95)
        x1 = 900 + int(math.cos(a) * 125)
        y1 = 260 + int(math.sin(a) * 125)
        d.line([x0, y0, x1, y1], fill=(253, 224, 71), width=10)
    # clouds
    for (cx, cy, s) in [(200, 300, 90), (700, 520, 120), (300, 700, 80)]:
        d.ellipse([cx - s, cy - s // 2, cx + s, cy + s // 2], fill=(255, 255, 255))
        d.ellipse([cx - s // 2, cy - s // 2 - 20, cx + s // 2, cy + s // 2 - 20],
                  fill=(255, 255, 255))
    # ground
    d.rectangle([0, GROUND_Y, W, H], fill=(22, 163, 74))
    d.rectangle([0, GROUND_Y, W, GROUND_Y + 10], fill=(34, 197, 94))
    for x in range(60, W, 160):
        d.ellipse([x, GROUND_Y + 120, x + 40, GROUND_Y + 150], fill=(21, 128, 61))
    return img


DAY1_BG = None
DAY7_BG = None


def draw_miner(d, top, day7):
    x0 = MINER_X - MINER_W // 2
    y0 = int(top)
    if day7:
        d.rounded_rectangle([x0, y0, x0 + MINER_W, y0 + MINER_H], radius=18,
                            fill=(249, 115, 22), outline=(154, 52, 18), width=4)
        # helmet
        d.pieslice([x0 + 10, y0 - 18, x0 + MINER_W - 10, y0 + 30],
                   180, 360, fill=(250, 204, 21))
        d.rectangle([x0 + 10, y0 + 6, x0 + MINER_W - 10, y0 + 16], fill=(250, 204, 21))
        # eyes + smile
        d.ellipse([x0 + 28, y0 + 42, x0 + 44, y0 + 58], fill=(15, 23, 42))
        d.ellipse([x0 + 76, y0 + 42, x0 + 92, y0 + 58], fill=(15, 23, 42))
        d.arc([x0 + 40, y0 + 62, x0 + 80, y0 + 92], 10, 170,
              fill=(15, 23, 42), width=5)
    else:
        d.rectangle([x0, y0, x0 + MINER_W, y0 + MINER_H], fill=(119, 119, 119))
        d.rectangle([x0 + 28, y0 + 40, x0 + 44, y0 + 56], fill=(85, 85, 85))
        d.rectangle([x0 + 76, y0 + 40, x0 + 92, y0 + 56], fill=(85, 85, 85))


def draw_gem(d, y, day7, trail=False):
    cx, cy = MINER_X, int(y)
    if day7 and trail:
        for k in range(6, 0, -1):
            a = 200 - k * 22
            r = 34 - k * 2
            d.polygon([(cx, cy - 150 + k * 26 - r), (cx + r, cy - 150 + k * 26),
                       (cx, cy - 150 + k * 26 + r), (cx - r, cy - 150 + k * 26)],
                      fill=(34, 211, 238))
    if day7:
        d.polygon([(cx, cy - 46), (cx + 40, cy), (cx, cy + 46), (cx - 40, cy)],
                  fill=(34, 211, 238), outline=(8, 145, 178))
        d.polygon([(cx, cy - 46), (cx + 40, cy), (cx, cy + 46), (cx - 40, cy)],
                  outline=(165, 243, 252), width=3)
        d.polygon([(cx, cy - 18), (cx + 15, cy), (cx, cy + 18), (cx - 15, cy)],
                  fill=(207, 250, 254))
    else:
        d.polygon([(cx, cy - 40), (cx + 34, cy), (cx, cy + 40), (cx - 34, cy)],
                  fill=(153, 153, 153))


def draw_particles(d, t):
    dt = t - GRAB_T
    if dt < 0 or dt > 1.4:
        return
    for i in range(24):
        px, py = particle_pos(i, dt)
        r = max(3, int(12 - dt * 6))
        col = PARTICLE_COLORS[i % len(PARTICLE_COLORS)]
        d.ellipse([px - r, py - r, px + r, py + r], fill=col)


def draw_badge(d, text, x, y, fill, txtfill=(255, 255, 255)):
    f = load_font(44)
    w, h = text_size(f, text)
    pad = 22
    d.rounded_rectangle([x, y, x + w + pad * 2, y + h + pad], radius=(h + pad) // 2,
                        fill=fill)
    draw_text_scaled(d, (x + pad, y + pad // 2 - 2), text, f, txtfill)


def draw_upgrades(d):
    """Three upgrade chips along the bottom (Day 7 only)."""
    f = load_font(40)
    labels = ["MAGNET", "2x GEMS", "SHIELD"]
    cols = [(250, 204, 21), (244, 114, 182), (56, 189, 248)]
    total_w = 3 * 260 + 2 * 30
    x = (W - total_w) // 2
    y = H - 260
    for lab, col in zip(labels, cols):
        w, h = text_size(f, lab)
        d.rounded_rectangle([x, y, x + 260, y + 90], radius=20,
                            fill=(15, 23, 42), outline=col, width=4)
        draw_text_scaled(d, (x + (260 - w) // 2, y + (90 - h) // 2 - 4), lab, f, col)
        x += 290


# ---------------------------------------------------------------- scenes
def render_game_frame(t, day7):
    """One gameplay frame at segment time t (0..5). Camera identical both days."""
    bg = DAY7_BG if day7 else DAY1_BG
    img = bg.copy()
    d = ImageDraw.Draw(img)
    st = sim(t)
    if day7:
        draw_gem(d, st["gem_y"], True, trail=not st["grabbed"])
    else:
        draw_gem(d, st["gem_y"], False)
    draw_miner(d, st["miner_top"], day7)
    if day7 and st["grabbed"]:
        draw_particles(d, t)
    # labels
    if day7:
        draw_badge(d, "DAY 7", W - 260, 90, (249, 115, 22))
        f = load_font(56)
        draw_text_scaled(d, (60, 90), "SCORE %d" % st["score"], f, (255, 255, 255))
        if st["combo"]:
            cf = load_font(64)
            center_text(d, W // 2, 240, "COMBO x%d" % st["combo"], cf,
                        (250, 204, 21))
        draw_upgrades(d)
    else:
        draw_badge(d, "DAY 1", 60, 90, (90, 90, 90))
        f = load_font(56)
        draw_text_scaled(d, (W - 330, 90), "SCORE 0", f, (221, 221, 221))
    return img


def render_hook_frame():
    """Frames 0-3s: Day 1 scene dimmed under the big hook."""
    img = render_game_frame(0.5, False)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 150))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)
    f_big = load_font(118)
    f_sub = load_font(54)
    center_text(d, W // 2, 620, "DAY 1 vs DAY 7", f_big, (255, 255, 255))
    center_text(d, W // 2, 790, "same game, same jump", f_sub, (250, 204, 21))
    center_text(d, W // 2, 880, "one AI agent, zero humans", f_sub,
                (226, 232, 240))
    return img


def render_end_frame():
    """Frames 13-18s: make.fun referral end card with the play code."""
    img = Image.new("RGB", (W, H), (15, 23, 42))
    d = ImageDraw.Draw(img)
    d.ellipse([140, 240, 300, 400], outline=(56, 189, 248), width=6)
    d.ellipse([780, 1500, 940, 1660], outline=(250, 204, 21), width=6)
    f_big = load_font(130)
    f_mid = load_font(52)
    f_small = load_font(44)
    center_text(d, W // 2, 560, "make.fun", f_big, (255, 255, 255))
    center_text(d, W // 2, 760, "Your idea. AI agents build it.", f_mid,
                (226, 232, 240))
    center_text(d, W // 2, 860, "Day 1 to Day 7 in one week", f_small,
                (148, 163, 184))
    center_text(d, W // 2, 930, "of daily updates", f_small, (148, 163, 184))
    # play-code box
    f_code = load_font(48)
    w, h = text_size(f_code, PLAY_CODE)
    bx0 = (W - w) // 2 - 40
    by0, by1 = 1080, 1080 + h + 50
    d.rounded_rectangle([bx0, by0, bx0 + w + 80, by1], radius=24,
                        fill=(30, 41, 59), outline=(56, 189, 248), width=4)
    draw_text_scaled(d, (bx0 + 40, by0 + 22), PLAY_CODE, f_code, (56, 189, 248))
    center_text(d, W // 2, 1330, "Start at make.fun", load_font(52),
                (250, 204, 21))
    return img

# ---------------------------------------------------------------- encode
def resolve_out_dir():
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def encode(frames_dir, out_path):
    """Deterministic ffmpeg encode: single thread, fixed timescale, no
    creation-time metadata."""
    cmd = ["ffmpeg", "-y", "-threads", "1", "-framerate", str(FPS),
           "-i", os.path.join(frames_dir, "frame_%04d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-preset", "medium", "-movflags", "+faststart",
           "-video_track_timescale", str(FPS),
           "-metadata", "creation_time=", "-metadata", "encoder=",
           out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit("ffmpeg failed with exit %d" % r.returncode)


def main():
    global DAY1_BG, DAY7_BG
    out_dir = resolve_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.mp4")
    DAY1_BG = build_day1_bg()
    DAY7_BG = build_day7_bg()
    # The hook (0-3s) and end card (13-18s) are static: render once, reuse.
    # (First version re-rendered them every frame: 2m54s per run.)
    hook_img = render_hook_frame()
    end_img = render_end_frame()
    with tempfile.TemporaryDirectory(prefix="gemrush-frames-") as td:
        for n in range(NFRAMES):
            t = n / FPS
            if t < 3.0:
                img = hook_img
            elif t < 8.0:
                img = render_game_frame(t - 3.0, False)
            elif t < 13.0:
                img = render_game_frame(t - 8.0, True)
            else:
                img = end_img
            img.save(os.path.join(td, "frame_%04d.png" % n))
        encode(td, out_path)
    print("Wrote %s (%d frames, %dx%d, %.1fs)" % (out_path, NFRAMES, W, H, DUR))


if __name__ == "__main__":
    main()
