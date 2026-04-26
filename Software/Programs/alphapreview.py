"""
Maakt op de computer dezelfde tekening als de echte robot, maar
alleen op een afbeelding. Geen machine nodig.

We hergebruiken `Canvas` uit `alphapaint` (zelfde vorm, zelfde getallen).
Andere dingen die de robot wél kán maar logo_runner niet gebruikt: als je die
zou aanroepen, krijg je `NotImplementedError` (voor ontwikkelaars).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from alphapaint import Canvas

# Foto: langste kant in pixels; vorm (breed:hoog) blijft gelijk met het echt tekenveld.
_MAX_PREVIEW_PIXELS = 1000
# Dikke rode rand (pixels) rond het tekenveld op het voorbeeldplaatje.
_RAND_ROOD_DIK_PX = 8
_RAND_ROOD = (255, 0, 0)


class AlphaPreview:
    """
    Telt in millimeter, tekent straks zwarte lijnen op een wit beeld, alsof (0,0)
    linksonder is en y omhoog telt, net als op de robot.

    * ``out_path`` is een bestand: daar wordt een PNG bewaard.
    * Geen ``out_path`` (standaard): het voorbeeld opent in je normale
      foto- / beeldbekijker; er blijft geen bestand in je map.
    """

    def __init__(self, width: float, height: float, out_path: Path | None = None) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Breedte en hoogte moeten groter dan 0 (millimeter).")
        self._canvas = Canvas((0.0, 0.0), (float(width), float(height)))
        self._pen_is_down: bool = False
        self._x: float = 0.0
        self._y: float = 0.0
        self._segments: List[Tuple[float, float, float, float]] = []
        self._out_path: Path | None = out_path
        self._flushed: bool = False

    @property
    def canvas(self) -> Canvas:
        return self._canvas

    @property
    def pen_is_down(self) -> bool:
        return self._pen_is_down

    def __enter__(self) -> AlphaPreview:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            self.done()
        except Exception:
            pass
        return False

    # -- Niet geïmplementeerd (niet nodig voor logo_runner) -------------------------

    def query_machine(self) -> Dict:
        raise NotImplementedError

    def query_position(self) -> Dict:
        raise NotImplementedError

    def pen_up_fast(self) -> None:
        raise NotImplementedError

    def pickup_pen(self, pen_index: int) -> None:
        raise NotImplementedError

    def return_pen(self, pen_index: int) -> None:
        raise NotImplementedError

    def draw_arc(
        self,
        x: float,
        y: float,
        i: float,
        j: float,
        clockwise: bool = True,
        feedrate: Optional[float] = None,
        wait: bool = True,
    ) -> None:
        raise NotImplementedError

    def move_to_normalized(self, x: float, y: float, wait: bool = True) -> None:
        raise NotImplementedError

    def draw_to_normalized(
        self, x: float, y: float, feedrate: Optional[float] = None, wait: bool = True
    ) -> None:
        raise NotImplementedError

    def move_to_machine(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        wait: bool = True,
    ) -> None:
        raise NotImplementedError

    def draw_to_machine(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        feedrate: Optional[float] = None,
        wait: bool = True,
    ) -> None:
        raise NotImplementedError

    def set_feedrate(self, feedrate: float) -> None:
        raise NotImplementedError

    # -- Geïmplementeerd -------------------------------------------------------

    def pen_up(self) -> None:
        self._pen_is_down = False

    def pen_down(self) -> None:
        self._pen_is_down = True

    def move_to(self, x: float, y: float, wait: bool = True) -> None:
        self._x, self._y = x, y

    def draw_to(
        self, x: float, y: float, feedrate: Optional[float] = None, wait: bool = True
    ) -> None:
        if self._pen_is_down:
            self._segments.append((self._x, self._y, x, y))
        self._x, self._y = x, y

    def flush(self) -> None:
        self._export_png(self._out_path)
        self._flushed = True

    def done(self, lift_pen: bool = True) -> None:
        if not self._flushed:
            self.flush()

    def _export_png(self, out: Path | None) -> None:
        from PIL import Image, ImageDraw

        w_mm = self._canvas.width
        h_mm = self._canvas.height
        if w_mm >= h_mm:
            pw = _MAX_PREVIEW_PIXELS
            ph = max(1, int(round(_MAX_PREVIEW_PIXELS * h_mm / w_mm)))
        else:
            ph = _MAX_PREVIEW_PIXELS
            pw = max(1, int(round(_MAX_PREVIEW_PIXELS * w_mm / h_mm)))

        img = Image.new("RGB", (pw, ph), (255, 255, 255))
        dr = ImageDraw.Draw(img)
        for x0, y0, x1, y1 in self._segments:
            px0, py0 = _mm_to_pixel(x0, y0, w_mm, h_mm, pw, ph)
            px1, py1 = _mm_to_pixel(x1, y1, w_mm, h_mm, pw, ph)
            dr.line((px0, py0, px1, py1), fill=(0, 0, 0), width=2)

        dik = min(_RAND_ROOD_DIK_PX, max(1, (min(pw, ph) - 1) // 2))
        dr.rectangle(
            (0, 0, pw - 1, ph - 1),
            outline=_RAND_ROOD,
            width=dik,
        )

        if out is not None:
            p = Path(out)
            p.parent.mkdir(parents=True, exist_ok=True)
            img.save(p, format="PNG")
        else:
            try:
                img.show()
            except Exception as exc:
                raise RuntimeError(
                    "Kon het voorbeeld niet openen. Draait dit op een bureaublad "
                    "en is er een standaard app voor afbeeldingen?"
                ) from exc


def _mm_to_pixel(
    x: float, y: float, w_mm: float, h_mm: float, pw: int, ph: int
) -> Tuple[int, int]:
    """
    Zet tekenveld-coördinaten om naar pixels: op papier telt y omhoog,
    in een beeld telt y naar beneden, daarom omdraaien.
    """
    if w_mm <= 0 or h_mm <= 0:
        return 0, 0
    x = min(max(0.0, x), w_mm)
    y = min(max(0.0, y), h_mm)
    px = int(round((x / w_mm) * (pw - 1)))
    py = int(round((1.0 - y / h_mm) * (ph - 1)))
    px = min(max(0, px), pw - 1)
    py = min(max(0, py), ph - 1)
    return px, py
