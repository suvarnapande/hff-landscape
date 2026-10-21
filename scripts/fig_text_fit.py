"""Keeps figure-level text (footnotes, subtitles, notes) inside the saved image.

install() wraps matplotlib's Figure.savefig so that, before every save:
  1. any figure-level text wider than the space to the right of where it starts is
     re-wrapped onto more lines, using its measured width, and
  2. the image is saved with bbox_inches="tight" plus a small pad, so text that
     sits low (e.g. a footnote placed with va="top" near the bottom) is never cropped.

Used by build_figures_v5.py, build_fcas_outcomes_v5.py, build_open_access_v5.py and
build_funder_types_v5.py: `import fig_text_fit; fig_text_fit.install()`.
"""
import textwrap

from matplotlib.figure import Figure

_MARGIN_PX = 12  # keep this many pixels clear of the right edge


def _rewrap(fig):
    renderer = fig.canvas.get_renderer()
    fig_w = fig.bbox.width
    for t in fig.texts:
        text = t.get_text()
        if not text:
            continue
        t.set_wrap(False)
        bb = t.get_window_extent(renderer)
        ha = t.get_ha()
        x_px = fig.transFigure.transform((t.get_position()[0], 0))[0]
        if ha == "left":
            avail = fig_w - x_px - _MARGIN_PX
        elif ha == "right":
            avail = x_px - _MARGIN_PX
        else:
            avail = 2 * min(x_px, fig_w - x_px) - 2 * _MARGIN_PX
        if avail <= 0 or bb.width <= avail:
            continue
        longest = max(len(line) for line in text.split("\n")) or 1
        width_chars = max(20, int(longest * avail / bb.width * 0.96))
        # Re-flow each paragraph; existing line breaks inside a paragraph are joined first.
        paras = [" ".join(p.split("\n")) for p in text.split("\n\n")]
        t.set_text("\n\n".join(textwrap.fill(p, width_chars, break_long_words=False) for p in paras))


def install():
    if getattr(Figure.savefig, "_fits_text", False):
        return
    original = Figure.savefig

    def savefig(self, *args, **kwargs):
        try:
            _rewrap(self)
        except Exception:  # never block a save over text fitting
            pass
        kwargs.setdefault("bbox_inches", "tight")
        if kwargs.get("bbox_inches") == "tight":
            kwargs.setdefault("pad_inches", 0.15)
        return original(self, *args, **kwargs)

    savefig._fits_text = True
    Figure.savefig = savefig
