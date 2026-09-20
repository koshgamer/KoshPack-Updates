from PIL import Image, ImageDraw

# Exact geometry from the live site's .meridian-mark:
# outer square rotated 45deg, two cross-lines, inner telemetry square.
SCALE = 4
SIZE = 256
CANVAS = SIZE * SCALE

COPPER = (208, 121, 64, 255)      # site --copper
TELEMETRY = (82, 188, 175, 255)   # site --telemetry
TRANSPARENT = (0, 0, 0, 0)

img = Image.new("RGBA", (CANVAS, CANVAS), TRANSPARENT)
d = ImageDraw.Draw(img)

def sc(v: float) -> int:
    return round(v * SCALE)

cx = cy = SIZE / 2
r = 69
ext = 91
inner = 31

outer = [
    (sc(cx), sc(cy - r)),
    (sc(cx + r), sc(cy)),
    (sc(cx), sc(cy + r)),
    (sc(cx - r), sc(cy)),
]
d.line(outer + [outer[0]], fill=COPPER, width=sc(8), joint="curve")

d.line((sc(cx - ext), sc(cy - ext), sc(cx + ext), sc(cy + ext)), fill=COPPER, width=sc(5))
d.line((sc(cx + ext), sc(cy - ext), sc(cx - ext), sc(cy + ext)), fill=COPPER, width=sc(5))

inside = [
    (sc(cx), sc(cy - inner)),
    (sc(cx + inner), sc(cy)),
    (sc(cx), sc(cy + inner)),
    (sc(cx - inner), sc(cy)),
]
d.line(inside + [inside[0]], fill=TELEMETRY, width=sc(8), joint="curve")

# Downsample for smooth edges while preserving the site's geometry.
img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

img.save("launcher/meridian.png")
img.save(
    "launcher/meridian.ico",
    format="ICO",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)],
)
print("Generated exact Project Meridian site mark")
