"""Genera docs/demo.svg: la barra en uso, reconstruida con los colores y textos de hooks/register.tsx.

Uso: python tools/escena_demo.py

Historia: escribes un mensaje y lo envias; mientras Claude responde suben los tokens, el costo y el
uso (el semanal pasa de ambar a rojo); el contexto pasa de 300k y aparece el aviso; pulsas Compactar
y el aviso se va. Todos los datos son inventados.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Mismos valores que hooks/register.tsx
SEGMENTS = 5
EMPTY_COLOR = "#888780"
WARNING_COLOR = "#EF9F27"
DIVIDER_COLOR = "#3A3A38"


def color_for(p):
    if p >= 90:
        return "#E24B4A"
    if p >= 70:
        return WARNING_COLOR
    return "#D85A30"


def token_text(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


# Colores de la app (tema oscuro), tomados de docs/barra.png
FONDO, PANEL, CAJA, BORDE_CAJA = "#1C1C1B", "#2A2A28", "#2F2E2C", "#3D3C39"
TENUE, CLARO, PLACEHOLDER = "#A6A49C", "#ECEAE3", "#8C8A84"
FUENTE = "'Segoe UI',system-ui,-apple-system,sans-serif"

W, H = 780, 160
PROMPT_Y, PROMPT_H = 104, 46
BANDA_ABAJO = PROMPT_Y - 8


def texto(x, y, spans, ancla="start", tam=13.5):
    negrita = ' font-weight="600"'
    partes = "".join(f'<tspan fill="{c}"{negrita if b else ""}>{t}</tspan>' for t, c, b in spans)
    return (f'<text x="{x}" y="{y}" font-size="{tam}" font-family="{FUENTE}" '
            f'text-anchor="{ancla}">{partes}</text>')


def limite(etiqueta, usado, reinicio):
    llenos = round(usado / 100 * SEGMENTS)
    c = color_for(usado)
    return [(f"{etiqueta}  ", TENUE, False), ("■" * llenos, c, False),
            ("□" * (SEGMENTS - llenos) + "  ", EMPTY_COLOR, False),
            (f"{round(usado)}%", c, True), (f"  ↻ {reinicio}", TENUE, False)]


def cuadro(cinco, semanal, tokens, usd, contexto=None, boton="normal", escrito="", chat=""):
    aviso = contexto is not None
    alto = 84 if aviso else 40
    arriba = BANDA_ABAJO - alto
    p = [f'<rect class="g" x="0" y="0" width="{W}" height="{H}" rx="10" fill="{FONDO}"/>']
    # La ultima linea del chat; cuando la banda crece con el aviso, el chat sube y queda tapado
    if chat and not aviso:
        p.append(texto(22, 34, [("● ", "#D85A30", False), (chat, CLARO, False)], tam=14.5))
    p.append(f'<rect class="g" x="8" y="{arriba}" width="{W - 16}" height="{alto}" rx="9" fill="{PANEL}"/>')
    fila = (limite("5h", cinco, "2h 40m") + [("   │   ", EMPTY_COLOR, False)]
            + limite("Semanal", semanal, "2d 19h"))
    p.append(texto(22, arriba + 25, fila))
    p.append(texto(W - 22, arriba + 25, [(f"{token_text(tokens)} tokens", TENUE, False),
                                          ("  ·  ", EMPTY_COLOR, False), (f"${usd:.2f}", CLARO, True)], "end"))
    if aviso:
        p.append(f'<rect x="22" y="{arriba + 40}" width="{W - 44}" height="1" fill="{DIVIDER_COLOR}"/>')
        p.append(texto(22, arriba + 67, [("▲  ", WARNING_COLOR, False), (
            f"El contexto va en {token_text(contexto)}. Compactar lo resume y abarata las respuestas.",
            TENUE, False)]))
        relleno = {"normal": "#3A3937", "encima": "#4A4946", "pulsado": "#55534F"}[boton]
        p.append(f'<rect class="g" x="{W - 116}" y="{arriba + 48}" width="94" height="28" rx="6" fill="{relleno}"/>')
        p.append(texto(W - 69, arriba + 66, [("Compactar", "#C9C7BF", False)], "middle", 13))
    p.append(f'<rect class="g" x="8.5" y="{PROMPT_Y + .5}" width="{W - 17}" height="{PROMPT_H - 1}" rx="10" '
             f'fill="{CAJA}" stroke="{BORDE_CAJA}"/>')
    p.append(texto(24, PROMPT_Y + 30, [("+", CLARO, False)], tam=20))
    if escrito:
        p.append(texto(52, PROMPT_Y + 28, [(escrito, CLARO, False), ("|", TENUE, False)], tam=14.5))
    else:
        p.append(texto(52, PROMPT_Y + 28, [("Enter para enviar, Ctrl+Enter para poner en cola para después",
                                            PLACEHOLDER, False)], tam=14.5))
    return p


cuadros = []


def pon(ms, **estado):
    cuadros.append({"ms": ms, "partes": cuadro(**estado)})


antes = "Listo: el carrito ya muestra el total con impuestos."
base = dict(cinco=36, semanal=88, tokens=48_900_000, usd=15.12, chat=antes)
pon(1400, **base)

# Escribes el mensaje
mensaje = "Agrega pruebas al carrito de compras"
for i in range(1, len(mensaje) + 1, 2):
    pon(55, **base, escrito=mensaje[:i])
pon(700, **base, escrito=mensaje)

# Claude responde: suben tokens, costo y uso
pasos = 14
for i in range(1, pasos + 1):
    f = i / pasos
    pon(110, cinco=36 + 4 * f, semanal=88 + 10 * f, tokens=48_900_000 + int(1_300_000 * f),
        usd=15.12 + 0.63 * f, chat="Agregando pruebas al carrito" + "." * (i // 2 % 4))
fin = dict(cinco=40, semanal=98, tokens=50_200_000, usd=15.75)
despues = "Listo: agregué 12 pruebas al carrito y todas pasan."
pon(1100, **fin, chat=despues)

# Aparece el aviso del contexto y pulsas Compactar
pon(2600, **fin, contexto=360_500)
pon(500, **fin, contexto=360_500, boton="encima")
pon(180, **fin, contexto=360_500, boton="pulsado")
pon(3200, **fin, chat="Conversación compactada: el resumen sigue el hilo.")

escena = {"ancho": W, "alto": H, "quieto": len(cuadros) - 4, "cuadros": cuadros}
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as t:
    json.dump(escena, t, ensure_ascii=False)
subprocess.run([sys.executable, str(RAIZ / "tools" / "armar_svg.py"), str(RAIZ / "docs" / "demo.svg"), t.name,
                "--pausa", "600"], check=True)
Path(t.name).unlink()
