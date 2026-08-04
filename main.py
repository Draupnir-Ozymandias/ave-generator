import numpy as np
from scipy.io.wavfile import write
import imageio
from PIL import Image, ImageDraw
import subprocess

# ---------------- CONFIG ----------------
DURATION = 180
SR = 44100
FPS = 60
SIZE = 1024
MAX_HZ = 360
CARRIER = 528

# ---------------- AUDIO ----------------
t = np.linspace(0, DURATION, int(SR * DURATION), endpoint=False)
freq = MAX_HZ * (t / DURATION)

def smoothstep(x, a, b):
    y = np.clip((x - a) / (b - a), 0, 1)
    return y * y * (3 - 2 * y)

w12 = smoothstep(freq, 36, 44)
w23 = smoothstep(freq, 76, 84)

w1 = 1 - w12
w2 = w12 * (1 - w23)
w3 = w23

norm = w1 + w2 + w3
w1 /= norm
w2 /= norm
w3 /= norm

def organ_tone(base, t):
    return (
        np.sin(2 * np.pi * base * t)
        + 0.6 * np.sin(2 * np.pi * 2 * base * t)
        + 0.4 * np.sin(2 * np.pi * 3 * base * t)
        + 0.2 * np.sin(2 * np.pi * 4 * base * t)
    )

p1L = organ_tone(CARRIER, t)
p1R = organ_tone(CARRIER + np.minimum(freq, 40), t)

pulse = 0.5 * (1 + np.sin(2 * np.pi * np.clip(freq, 40, 80) * t))
p2 = organ_tone(CARRIER, t) * pulse

p3 = organ_tone(CARRIER, t) * (0.5 * (1 + np.sin(2 * np.pi * freq * t)))

left = w1 * p1L + w2 * p2 + w3 * p3
right = w1 * p1R + w2 * p2 + w3 * p3

mx = max(np.max(np.abs(left)), np.max(np.abs(right)))
left /= mx
right /= mx

audio = np.vstack((left, right)).T
audio = (audio * 32767).astype(np.int16)

write("output/audio.wav", SR, audio)

# ---------------- VIDEO ----------------
def draw_yinyang(angle):
    img = Image.new("RGB", (SIZE, SIZE), "black")
    d = ImageDraw.Draw(img)

    d.ellipse((0, 0, SIZE, SIZE), fill="white")
    d.pieslice((0, 0, SIZE, SIZE), 90, 270, fill="black")

    d.ellipse((SIZE//4, 0, SIZE*3//4, SIZE//2), fill="white")
    d.ellipse((SIZE//4, SIZE//2, SIZE*3//4, SIZE), fill="black")

    r = SIZE // 12
    d.ellipse((SIZE//2 - r, SIZE//4 - r, SIZE//2 + r, SIZE//4 + r), fill="black")
    d.ellipse((SIZE//2 - r, SIZE*3//4 - r, SIZE//2 + r, SIZE*3//4 + r), fill="white")

    return img.rotate(-angle)

writer = imageio.get_writer("output/video.mp4", fps=FPS)

for i in range(DURATION * FPS):
    t_sec = i / FPS
    hz = MAX_HZ * (t_sec / DURATION)
    rpm = hz * 60

    angle = 180 * MAX_HZ * (t_sec ** 2) / DURATION

    img = draw_yinyang(angle)
    d = ImageDraw.Draw(img)

    if hz <= 40:
        phase = "Binaural"
        overtones = ""
    elif hz <= 80:
        phase = "Isochronic"
        overtones = ""
    else:
        phase = "Harmonic"
        overtones = "Overtones: 1056 Hz, 1584 Hz"

    y = 10
    d.text((10, y), f"{hz:.1f} Hz | {rpm:.0f} RPM", fill="gold"); y += 20
    d.text((10, y), f"{phase} Phase", fill="gold"); y += 20
    d.text((10, y), "Carrier: 528 Hz", fill="gold"); y += 20
    if overtones:
        d.text((10, y), overtones, fill="gold")

    writer.append_data(np.array(img))

writer.close()

# ---------------- MUX ----------------
subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/video.mp4",
    "-i", "output/audio.wav",
    "-c:v", "copy",
    "-c:a", "aac",
    "-b:a", "192k",
    "output/final.mp4"
])