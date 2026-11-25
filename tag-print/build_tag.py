"""Build print files for the Freedom Bag Tag (V.2).

Reads tag_text.txt and writes, into the output directory (default: out/):

- freedom-bag-tag-v2.pdf        one tag per page: page 1 front (Spanish), page 2 back (English)
- freedom-bag-tag-v2-sheet.pdf  US Letter, eight tags per page: page 1 fronts, page 2 backs
                                (columns mirrored so the backs line up on long-edge duplex)
- freedom-bag-tag-v2-front.png  300 dpi image of one front
- freedom-bag-tag-v2-back.png   300 dpi image of one back

Before building it checks that the Spanish and English text in tag_text.txt match the
blockquotes on preservation.qmd word for word, so the printed tag cannot drift from the site.

Usage:
    pip install -r requirements.txt
    python build_tag.py [--out DIR]
"""
import argparse
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

# The only web address printed on the tag. Keep it to the bare domain: the .org forward
# drops any path, so a deep link would land on the home page.
WEB_ADDRESS = "copyleftcultivars.org"

TAG_W, TAG_H = 4.0 * inch, 2.5 * inch
PAD = 0.14 * inch
COLS, ROWS = 2, 4

HERE = Path(__file__).resolve().parent
SITE_PAGE = HERE.parent / "preservation.qmd"


def read_source(path):
    sections, key = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        m = re.fullmatch(r"== (\w+) ==", line.strip())
        if m:
            key = m.group(1)
            sections[key] = []
        elif key and line.strip():
            sections[key].append(line.strip())
    return {k: " ".join(v) for k, v in sections.items()}


def site_quotes(path):
    """The Spanish and English blockquotes on the tag page, without their outer quote marks."""
    text = path.read_text(encoding="utf-8")
    out = {}
    for key, heading in (("es", "Full text in Spanish"), ("en", "English translation")):
        m = re.search(r"### " + heading + r"\n\n((?:> .*\n)+)", text)
        if not m:
            sys.exit(f"could not find the '{heading}' blockquote in {path}")
        quote = " ".join(line[2:].strip() for line in m.group(1).splitlines())
        out[key] = quote.strip("“”")
    return out


def check_against_site(src):
    if not SITE_PAGE.exists():
        print(f"note: {SITE_PAGE} not found, skipping the site text check")
        return
    site = site_quotes(SITE_PAGE)
    for key in ("es", "en"):
        if src[key] != site[key]:
            sys.exit(f"tag_text.txt [{key}] does not match {SITE_PAGE.name}; fix one of them first")
    print("tag text matches preservation.qmd (es, en)")


def fitted(text, width, height, bold=False):
    """The largest font size, in 0.1 pt steps down from 8 pt, at which the text fits."""
    size = 8.0
    while size >= 4.0:
        style = ParagraphStyle(
            "t", fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size, leading=size * 1.18,
        )
        p = Paragraph(text, style)
        _, h = p.wrap(width, height)
        if h <= height:
            return p, h, size
        size = round(size - 0.1, 1)
    sys.exit("text does not fit on the tag even at 4 pt")


def draw_tag(c, x, y, title, body, footer, sizes):
    """Draw one tag with its lower-left corner at (x, y)."""
    c.setLineWidth(0.4)
    c.setStrokeGray(0.6)
    c.rect(x, y, TAG_W, TAG_H)
    inner_w = TAG_W - 2 * PAD
    top = y + TAG_H - PAD

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillGray(0)
    c.drawString(x + PAD, top - 8.5, title)

    c.setFont("Helvetica", 7)
    c.drawRightString(x + TAG_W - PAD, y + PAD, footer)

    body_top = top - 8.5 - 5
    body_h = body_top - (y + PAD + 7 + 5)
    p, h, size = fitted(body, inner_w, body_h)
    p.drawOn(c, x + PAD, body_top - h)
    sizes.append(size)


def build(src, out):
    out.mkdir(parents=True, exist_ok=True)
    title = src["title"]
    faces = [
        (f"{title} · Español", src["es"]),
        (f"{title} · English", src["en"]),
    ]
    sizes = []

    single = out / "freedom-bag-tag-v2.pdf"
    c = canvas.Canvas(str(single), pagesize=(TAG_W, TAG_H))
    c.setTitle("Freedom Bag Tag (V.2)")
    for head, body in faces:
        draw_tag(c, 0, 0, head, body, WEB_ADDRESS, sizes)
        c.showPage()
    c.save()

    sheet = out / "freedom-bag-tag-v2-sheet.pdf"
    page_w, page_h = letter
    mx = (page_w - COLS * TAG_W) / 2
    my = (page_h - ROWS * TAG_H) / 2
    c = canvas.Canvas(str(sheet), pagesize=letter)
    c.setTitle("Freedom Bag Tag (V.2), eight per page")
    for side, (head, body) in enumerate(faces):
        for r in range(ROWS):
            for col in range(COLS):
                # Backs mirror the columns so each back sits behind its front on long-edge duplex.
                cc = col if side == 0 else COLS - 1 - col
                draw_tag(c, mx + cc * TAG_W, my + r * TAG_H, head, body, WEB_ADDRESS, sizes)
        c.showPage()
    c.save()

    pngs = render_png(single, out)
    print(f"body font size: {min(sizes)}-{max(sizes)} pt")
    for f in [single, sheet, *pngs]:
        print(f"wrote {f}")


def render_png(pdf, out):
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    paths = []
    for i, name in enumerate(("front", "back")):
        img = doc[i].render(scale=300 / 72).to_pil()
        path = out / f"freedom-bag-tag-v2-{name}.png"
        img.save(path, dpi=(300, 300))
        paths.append(path)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(HERE / "out"))
    args = ap.parse_args()
    src = read_source(HERE / "tag_text.txt")
    for key in ("title", "es", "en"):
        if not src.get(key):
            sys.exit(f"tag_text.txt has no '== {key} ==' section")
    check_against_site(src)
    build(src, Path(args.out))


if __name__ == "__main__":
    main()
