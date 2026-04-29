#!/usr/bin/env python3
"""Re-save existing PNG plots as PDFs for LaTeX inclusion."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

PLOTS_DIR = Path(__file__).parent.parent / "results" / "plots"
OUT_DIR = Path(__file__).parent.parent / "report" / "figuras"
OUT_DIR.mkdir(parents=True, exist_ok=True)

for png in PLOTS_DIR.glob("*.png"):
    img = mpimg.imread(str(png))
    h, w = img.shape[:2]
    fig, ax = plt.subplots(figsize=(w / 100, h / 100))
    ax.imshow(img)
    ax.axis("off")
    out = OUT_DIR / (png.stem + ".pdf")
    fig.savefig(str(out), bbox_inches="tight", pad_inches=0, dpi=150)
    plt.close(fig)
    print(f"  {png.name} -> {out.name}")

print("Done.")
