#!/usr/bin/env python3
"""
LOGO-uitvoerder voor AlphaPaint.

Leest een eenvoudig LOGO-tekstbestand en voert dit uit op AlphaPaint met een
“turtle”-achtige toestand (positie + richting + penstatus).

Gebruik:
    python3 logo_runner.py PAD/NAAR/BESTAND.logo

Ondersteunde commando’s (hoofd-/kleine letters door elkaar toegestaan):
    VOORUIT <afstand>
    LINKS <graden>
    RECHTS <graden>
    PENOP
    PENNEER
    PENKLEUR <naam>   (geaccepteerd en gelogd, niet gekoppeld aan pennen)
    PENDIKTE <waarde> (geaccepteerd en gelogd, geen fysieke lijndikte)

Strikte modus:
    - Onbekende commando’s zijn fouten.
    - Verkeerd aantal argumenten is een fout.
    - Niet-numerieke waarden voor numerieke commando’s zijn fouten.
    - Fouten bevatten regelnummers en stoppen het programma met een foutcode.
"""

import math
import sys
from pathlib import Path

from alphapaint import AlphaPaint, AlphaPaintError


class LogoParseFout(Exception):
    """Fout bij het strikt parsen/uitvoeren van een LOGO-bestand."""


def log_bericht(bericht: str) -> None:
    """Schrijf statusberichten naar stderr (zichtbaar in daemon-logs/debugging)."""
    print(f"[logo_runner] {bericht}", file=sys.stderr, flush=True)


def parse_getal(token: str, regelnummer: int, commando: str) -> float:
    """Parse een numeriek argument met duidelijke foutmelding."""
    try:
        return float(token)
    except ValueError as exc:
        raise LogoParseFout(
            f"Regel {regelnummer}: {commando} verwacht een getal, maar kreeg '{token}'"
        ) from exc


def voer_logo_uit(alpha: AlphaPaint, logo_pad: Path) -> None:
    """
    Voer LOGO-commando’s uit uit een bestand op het AlphaPaint-canvas.

    Begin toestand:
    - Positie: midden van het canvas
    - Richting: 90 graden (omhoog, +Y op het canvas)
    - Pen: neer
    """
    logo_max_x = 1550  # max aantal stappen in horizontale richting
    logo_max_y = 850  # max aantal stappen in verticale richting
    # we gaan er van uit dat de linker-onderhoek (0,0) is
    logo_start_x = 600
    logo_start_y = 450

    canvas = alpha.canvas
    canvas_max_x = canvas.width
    canvas_max_y = canvas.height

    # hoeveel moeten we de logo-afstanden vergroten/verkleinen om op de canvas te passen?
    schaal_x = canvas_max_x / logo_max_x
    schaal_y = canvas_max_y / logo_max_y

    # Standaard LOGO-turtle: start naar boven; in canvas: +Y = omhoog.
    richting_graden = 90.0
    pen_is_neer = True
    # TODO: hoe weten we of canvas ook linker-onder als (0,0) heeft?
    huidige_x = logo_start_x * schaal_x
    huidige_y = logo_start_y * schaal_y

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
                        f"Regel {regelnummer}: VOORUIT verwacht 1 argument, kreeg {len(argumenten)}"
                    )
                afstand = parse_getal(argumenten[0], regelnummer, commando)
                # radians: graden * pi / 180 en cos/sin verwacht radians
                hoek_rad = math.radians(richting_graden)
                # op een cirkel met straal 1 is 'hoek_rad' het punt x=cos(hoek_rad), y=sin(hoek_rad)
                # dus vermenigvuldig met (afstand*schaal) om zoveel eenheden erbij te hebben
                nieuwe_x = huidige_x + (afstand*schaal_x) * math.cos(hoek_rad)
                nieuwe_y = huidige_y + (afstand*schaal_y) * math.sin(hoek_rad)

                if pen_is_neer:
                    alpha.draw_to(nieuwe_x, nieuwe_y, wait=False)
                else:
                    alpha.move_to(nieuwe_x, nieuwe_y, wait=False)

                huidige_x, huidige_y = nieuwe_x, nieuwe_y

            elif commando == "LINKS":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: LINKS verwacht 1 argument, kreeg {len(argumenten)}"
                    )
                graden = parse_getal(argumenten[0], regelnummer, commando)
                richting_graden += graden

            elif commando == "RECHTS":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: RECHTS verwacht 1 argument, kreeg {len(argumenten)}"
                    )
                graden = parse_getal(argumenten[0], regelnummer, commando)
                richting_graden -= graden

            elif commando == "PENOP":
                if argumenten:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: PENOP verwacht 0 argumenten, kreeg {len(argumenten)}"
                    )
                alpha.pen_up()
                pen_is_neer = False

            elif commando == "PENNEER":
                if argumenten:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: PENNEER verwacht 0 argumenten, kreeg {len(argumenten)}"
                    )
                alpha.pen_down()
                pen_is_neer = True

            elif commando == "PENKLEUR":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: PENKLEUR verwacht 1 argument, kreeg {len(argumenten)}"
                    )
                log_bericht(
                    f"Regel {regelnummer}: PENKLEUR {argumenten[0]} geaccepteerd (genegeerd: geen pen-mapping)"
                )

            elif commando == "PENDIKTE":
                if len(argumenten) != 1:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: PENDIKTE verwacht 1 argument, kreeg {len(argumenten)}"
                    )
                dikte = parse_getal(argumenten[0], regelnummer, commando)
                if dikte <= 0:
                    raise LogoParseFout(
                        f"Regel {regelnummer}: PENDIKTE moet > 0 zijn, kreeg {dikte}"
                    )
                log_bericht(
                    f"Regel {regelnummer}: PENDIKTE {dikte:g} geaccepteerd (geen fysieke lijndikte-aansturing)"
                )

            else:
                raise LogoParseFout(
                    f"Regel {regelnummer}: onbekend commando '{delen[0]}'"
                )

    alpha.flush()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Gebruik: python3 logo_runner.py PAD/NAAR/BESTAND.logo", file=sys.stderr)
        sys.exit(1)

    logo_pad = Path(sys.argv[1])

    if not logo_pad.is_file():
        print(f"Fout: bestand niet gevonden: {logo_pad}", file=sys.stderr)
        sys.exit(1)

    try:
        with AlphaPaint() as alpha:
            voer_logo_uit(alpha, logo_pad)
        log_bericht("Uitvoering succesvol afgerond")
        sys.exit(0)
    except LogoParseFout as exc:
        print(f"Parse-fout: {exc}", file=sys.stderr)
        sys.exit(2)
    except AlphaPaintError as exc:
        print(f"AlphaPaint-fout: {exc} (code={exc.code})", file=sys.stderr)
        sys.exit(3)
    except Exception as exc:
        print(f"Onverwachte fout: {exc}", file=sys.stderr)
        sys.exit(4)
