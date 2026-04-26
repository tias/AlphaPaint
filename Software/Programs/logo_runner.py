#!/usr/bin/env python3
"""
Leest een .logo-bestand en laat de robot tekenen, of toont een voorbeeld op je scherm.

Hoe te gebruiken (in een terminal):
    python3 logo_runner.py  pad/naar/mijn_tekening.logo
    python3 logo_runner.py  pad/naar/mijn_tekening.logo  --preview
    python3 logo_runner.py  pad/naar/mijn_tekening.logo  --preview  300  200
    python3 logo_runner.py  pad/naar/mijn_tekening.logo  --zoom 1.2

--zoom  vergroot of verkleint de tekening op het vel (1.0 = normaal, 1.2 = 20% groter,
0.5 = half zo klein). Werkt bij de robot en bij --preview.

--preview  toont de tekening in je normale beeldbekijker in plaats van echt
te tekenen (er wordt geen PNG in je map bewaard). Met twee
getallen (breed, hoog, in millimeter) kies je zelf de grootte. Zonder getallen
leest het programma de grootte van het tekenveld op de machine.

Commando’s in het .logo-bestand (grote of kleine letters mag):
    VOORUIT <stappen>   — rechtdoor
    LINKS <graden>      — draai naar links
    RECHTS <graden>     — draai naar rechts
    PENOP               — pen omhoog (geen streep)
    PENNEER             — pen omlaag (wel streep)
    PENKLEUR <naam>     — wordt genoteerd, de robot wisselt geen stift
    PENDIKTE <getal>    — wordt genoteerd, de lijndikte op papier blijft gelijk

Bij een fout: je ziet in welke regel van het .logo-bestand iets mis is.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Union

from alphapaint import AlphaPaint, AlphaPaintError
from alphapreview import AlphaPreview


class LogoParseFout(Exception):
    """Fout in het .logo-bestand (onbekend commando, verkeerd aantal stukjes, …)."""


def log_bericht(bericht: str) -> None:
    """Berichten voor ouders / debug: op de scherm-uitvoer (niet in het .logo)."""
    print(f"[logo_runner] {bericht}", file=sys.stderr, flush=True)


def parse_getal(token: str, regelnummer: int, commando: str) -> float:
    try:
        return float(token)
    except ValueError as exc:
        raise LogoParseFout(
            f"Regel {regelnummer}: bij {commando} hoort een getal, niet '{token}'"
        ) from exc


def voer_logo_uit(
    alpha: Union[AlphaPaint, AlphaPreview], logo_pad: Path, zoom: float = 1.0
) -> None:
    """
    Voer LOGO-commando’s uit op het tekenveld (robot of preview).

    ``zoom`` vermenigvuldigt alle afstanden in millimeter: 1.2 is 1,2× groter,
    0,5 is half zo klein. Startpositie en alle ``VOORUIT``-stappen schalen mee.
    """
    logo_max_x = 1550  # max aantal stappen in horizontale richting
    logo_max_y = 850  # max aantal stappen in verticale richting
    # de linker-onderhoek is (0,0): 0=left/bottom
    logo_start_x = 600
    logo_start_y = 450

    canvas = alpha.canvas
    canvas_max_x = canvas.width
    canvas_max_y = canvas.height

    # Herschaal zodat hoogte (y-as) overeenkomt met canvas-hoogte
    schaal = (canvas_max_y / logo_max_y)

    # Standaard LOGO-turtle: start naar boven; in canvas: +Y = omhoog.
    richting_graden = 90.0
    pen_is_neer = True
    huidige_x = logo_start_x * schaal * zoom
    huidige_y = logo_start_y * schaal * zoom

    alpha.move_to(huidige_x, huidige_y)
    alpha.pen_down()

    with logo_pad.open("r", encoding="utf-8") as bestand:
        for regelnummer, ruwe_regel in enumerate(bestand, start=1):
            regel = ruwe_regel.strip()
            if not regel:
                continue

            delen = regel.split()
            commando = delen[0].upper()
            argumenten = delen[1:]

            if commando == "VOORUIT":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: bij VOORUIT hoort precies één getal, niet {len(argumenten)}"
                    )
                afstand = parse_getal(argumenten[0], regelnummer, commando)
                # radians: graden * pi / 180 en cos/sin verwacht radians
                hoek_rad = math.radians(richting_graden)
                # op een cirkel met straal 1 is 'hoek_rad' het punt x=cos(hoek_rad), y=sin(hoek_rad)
                # dus vermenigvuldig met (afstand*schaal) om zoveel eenheden erbij te hebben
                nieuwe_x = huidige_x + (afstand*schaal*zoom) * math.cos(hoek_rad)
                nieuwe_y = huidige_y + (afstand*schaal*zoom) * math.sin(hoek_rad)

                if pen_is_neer:
                    alpha.draw_to(nieuwe_x, nieuwe_y, wait=False)
                else:
                    alpha.move_to(nieuwe_x, nieuwe_y, wait=False)

                huidige_x, huidige_y = nieuwe_x, nieuwe_y

            elif commando == "LINKS":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: bij LINKS hoort precies één getal, niet {len(argumenten)}"
                    )
                graden = parse_getal(argumenten[0], regelnummer, commando)
                richting_graden += graden

            elif commando == "RECHTS":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: bij RECHTS hoort precies één getal, niet {len(argumenten)}"
                    )
                graden = parse_getal(argumenten[0], regelnummer, commando)
                richting_graden -= graden

            elif commando == "PENOP":
                if argumenten:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: na PENOP mag niets meer staan, hier staan {len(argumenten)} extra woord(en)"
                    )
                alpha.pen_up()
                pen_is_neer = False

            elif commando == "PENNEER":
                if argumenten:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: na PENNEER mag niets meer staan, hier staan {len(argumenten)} extra woord(en)"
                    )
                alpha.pen_down()
                pen_is_neer = True

            elif commando == "PENKLEUR":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: bij PENKLEUR hoort precies één woord, niet {len(argumenten)}"
                    )
                log_bericht(
                    f"Regel {regelnummer}: kleur {argumenten[0]} genoteerd (robot wisselt geen stift)"
                )

            elif commando == "PENDIKTE":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: bij PENDIKTE hoort precies één getal, niet {len(argumenten)}"
                    )
                dikte = parse_getal(argumenten[0], regelnummer, commando)
                if dikte <= 0:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: PENDIKTE moet groter dan 0, niet {dikte}"
                    )
                log_bericht(
                    f"Regel {regelnummer}: dikte {dikte:g} genoteerd (op papier blijft dezelfde lijn)"
                )

            else:
                raise LogoParseFout(
                    f"Regel {regelnummer}: onbekend woord: '{delen[0]}' (kende dat niet)"
                )

    alpha.flush()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Teken op de robot, of kijk eerst op het scherm met een preview-plaatje."
    )
    p.add_argument(
        "logo",
        type=Path,
        help="Je .logo-bestand (waar je commando’s in staan).",
    )
    p.add_argument(
        "--preview",
        nargs="*",
        default=None,
        metavar=("BREED", "HOOG"),
        help="Geen echt tekenen: toon een voorbeeld in je beeldbekijker. Optioneel: breedte en hoogte in mm. "
        "Zonder cijfers: de grootte van het tekenveld op de machine gebruiken.",
    )
    p.add_argument(
        "--zoom",
        type=float,
        default=1.0,
        metavar="FACTOR",
        help="Grootte van de tekening: 1.0 = normaal, 1.2 = 20%% groter, 0.5 = half. "
        "Geldt voor de robot en voor --preview.",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(None)

    logo_pad: Path = args.logo
    if not logo_pad.is_file():
        print(f"Ik kan dat bestand niet vinden: {logo_pad}", file=sys.stderr)
        sys.exit(1)

    prev = args.preview
    if prev is not None and len(prev) not in (0, 2):
        print(
            "Bij --preview: geen cijfers, óf precies twee (breedte en hoogte in millimeter).",
            file=sys.stderr,
        )
        sys.exit(1)

    z = args.zoom
    if z <= 0 or not math.isfinite(z):
        print("Bij --zoom: het getal moet groter dan 0 (en een normaal cijfer).", file=sys.stderr)
        sys.exit(1)

    try:
        if prev is None:
            with AlphaPaint() as alpha:
                voer_logo_uit(alpha, logo_pad, zoom=z)
            log_bericht("Klaar, de robot is klaar met tekenen.")
            sys.exit(0)

        if len(prev) == 0:
            with AlphaPaint() as ap:
                w, h = ap.canvas.width, ap.canvas.height
        else:
            try:
                w, h = float(prev[0]), float(prev[1])
            except ValueError:
                print("Bij --preview: breedte en hoogte moeten leesbare getallen zijn.", file=sys.stderr)
                sys.exit(1)
            if w <= 0 or h <= 0:
                print("Bij --preview: breedte en hoogte moeten groter dan 0.", file=sys.stderr)
                sys.exit(1)

        with AlphaPreview(w, h) as preview:
            voer_logo_uit(preview, logo_pad, zoom=z)
        log_bericht("Voorbeeld geopend in je beeldbekijker (geen bestand in je map).")
        sys.exit(0)

    except LogoParseFout as exc:
        print(f"Fout in je .logo-bestand: {exc}", file=sys.stderr)
        sys.exit(2)
    except AlphaPaintError as exc:
        print(
            f"Fout op de teken-robot (AlphaPaint): {exc} (code {exc.code})",
            file=sys.stderr,
        )
        sys.exit(3)
    except Exception as exc:
        print(f"Er ging iets mis: {exc}", file=sys.stderr)
        sys.exit(4)
