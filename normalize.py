import sys
from pathlib import Path
from collections import Counter
from pypdf import PdfReader, PdfWriter, Transformation

ALIGN_SPREADS = True  # add a blank page so each split spread's left half lands on an even page

folder = Path(sys.argv[1])
out = folder / "normalized"
out.mkdir(exist_ok=True)

for pdf in sorted(folder.glob("*.pdf")):
    try:
        r, w = PdfReader(str(pdf)), PdfWriter()
        # 1) pieces: (source page, left, bottom, width, height, is_left_half_of_spread)
        pieces, splits = [], 0
        for p in r.pages:
            if p.rotation:
                p.transfer_rotation_to_content()
            L, B = float(p.mediabox.left), float(p.mediabox.bottom)
            W, H = float(p.mediabox.width), float(p.mediabox.height)
            if W > H:
                pieces.append((p, L, B, W / 2, H, True))
                pieces.append((p, L + W / 2, B, W / 2, H, False))
                splits += 1
            else:
                pieces.append((p, L, B, W, H, False))
        # 2) target size = most common size among the pieces
        target, _ = Counter((round(pw), round(ph)) for _, _, _, pw, ph, _ in pieces).most_common(1)[0]
        TW, TH = target
        # 3) write pages, adding a blank before a spread whose left half would be an odd page
        blanks = 0
        for src, L, B, pw, ph, is_left in pieces:
            if ALIGN_SPREADS and is_left and (len(w.pages) + 1) % 2 == 1:
                w.add_blank_page(TW, TH)
                blanks += 1
            s = min(TW / pw, TH / ph)
            dx, dy = (TW - pw * s) / 2, (TH - ph * s) / 2
            page = w.add_blank_page(TW, TH)
            page.merge_transformed_page(
                src, Transformation().translate(-L, -B).scale(s, s).translate(dx, dy))
        w.write(str(out / pdf.name))
        print(f"OK   {pdf.name}: {splits} wide split, {blanks} blank added, {len(w.pages)} pages, all {TW} x {TH}")
    except Exception as e:
        print(f"FAIL {pdf.name}: {e}")