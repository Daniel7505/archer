"""make_assets.py - PIL-drawn textures: the original Aldermoor banner emblem (run before chapter2_scene.py)."""
import os, math
CH = os.path.dirname(os.path.abspath(__file__))
def emblem_image():
    """original Aldermoor emblem: a gold alder leaf over three silver waves on a deep-blue field."""
    p = os.path.join(CH, "aldermoor_banner.png")
    if not os.path.exists(p):
        from PIL import Image, ImageDraw
        W_, H_ = 256, 512; im = Image.new("RGB", (W_, H_), (22, 44, 120)); d = ImageDraw.Draw(im)
        d.rectangle((10, 10, W_ - 10, H_ - 10), outline=(230, 190, 70), width=8)
        cx, cy = W_ // 2, 200
        leaf = [(cx, cy - 120)]
        for i in range(1, 9):              # serrated alder-leaf outline
            t = i / 9; r = 70 * math.sin(math.pi * t) ** 0.8; y = cy - 120 + 230 * t
            leaf.append((cx + r + (8 if i % 2 else 0), y))
        leaf.append((cx, cy + 110))
        for i in range(8, 0, -1):
            t = i / 9; r = 70 * math.sin(math.pi * t) ** 0.8; y = cy - 120 + 230 * t
            leaf.append((cx - r - (8 if i % 2 else 0), y))
        d.polygon(leaf, fill=(236, 196, 72)); d.line((cx, cy - 100, cx, cy + 150), fill=(150, 110, 30), width=6)
        for j in range(4):
            d.line((cx, cy - 60 + j * 45, cx + 40, cy - 85 + j * 45), fill=(150, 110, 30), width=4)
            d.line((cx, cy - 60 + j * 45, cx - 40, cy - 85 + j * 45), fill=(150, 110, 30), width=4)
        for k in range(3):                 # waves
            y0 = 380 + k * 30
            pts = [(x, y0 + 9 * math.sin(x / 18.0)) for x in range(24, W_ - 23, 4)]
            d.line(pts, fill=(215, 225, 240), width=7)
        # swallow-tail notch
        d.polygon([(0, H_), (W_ // 2, H_ - 50), (W_, H_)], fill=(0, 0, 0))
        im.save(p)
    return p


if __name__ == "__main__":
    print(emblem_image())
