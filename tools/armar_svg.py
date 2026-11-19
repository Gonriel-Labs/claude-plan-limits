"""Arma un SVG animado (como un GIF, pero vectorial) a partir de una lista de cuadros.

Uso:
    python armar_svg.py <salida.svg> <escena.json> [<escena.json> ...] [--pausa MS] [--fondo COLOR]

Las escenas se reproducen una tras otra, con una pausa vacia entre ellas, y el conjunto se repite sin fin.

Formato de cada escena (JSON):
{
  "ancho": 470, "alto": 142,          # tamano del lienzo; si falta, se usa el mas grande de las escenas
  "estilo": "...",                    # opcional: CSS extra (fuentes, clases)
  "defs": "...",                      # opcional: <defs> compartidos (degradados, simbolos)
  "quieto": 12,                       # opcional, solo en la primera escena: cuadro fijo con prefers-reduced-motion
  "cuadros": [
    {"ms": 120, "partes": ["<rect .../>", "<text ...>Hola</text>"]},
    {"ms": 80,  "svg": "<g>...</g>"},                    # o un bloque SVG entero
    {"t": 3400, "x": -320, "f": [ {figura}, ... ]}       # o figuras grabadas (ver abajo)
  ]
}

Cada cuadro dura "ms" milisegundos. Si en cambio trae "t" (marca de tiempo de una grabacion),
dura hasta el "t" del siguiente. "x" e "y" desplazan el cuadro (por ejemplo, algo que entra por el borde).

Figuras grabadas ("f"), el formato que produce un grabador de interfaz como Grabador.cs:
  {"t":"r","x","y","w","h","c","o"}                 rectangulo de color c y opacidad o
  {"t":"b","x","y","w","h","f","s","sw","rx","o"}   caja con relleno f, borde s de grosor sw y esquinas rx
  {"t":"x","x","y","c","o","fs","fw","ff","s"}      texto s en (x, y = linea base)

Como un GIF, cada cuadro es un grupo y una animacion CSS por pasos muestra uno a la vez. Las partes que
se repiten en todos los cuadros de una escena se dibujan una sola vez y se reutilizan, y los cuadros
identicos seguidos se juntan: asi el archivo pesa mucho menos.
"""
import argparse
import json
import sys
from html import escape
from pathlib import Path

HUECO_MAXIMO = 250        # ms entre cuadros grabados; mas que esto se ve como un tiron
PESO_AVISO = 1024 * 1024  # GitHub muestra SVG grandes, pero sobre 1 MB la pagina carga lento


def n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def figura(f):
    o = "" if f.get("o", 1) >= 0.999 else f' opacity="{n(f["o"])}"'
    if f["t"] == "r":
        return f'<rect x="{n(f["x"])}" y="{n(f["y"])}" width="{n(f["w"])}" height="{n(f["h"])}" fill="{f["c"]}"{o}/>'
    if f["t"] == "b":
        m = f["sw"] / 2   # el trazo SVG va centrado en el borde; el de muchas UI va por dentro
        return (f'<rect x="{n(f["x"] + m)}" y="{n(f["y"] + m)}" width="{n(f["w"] - f["sw"])}" '
                f'height="{n(f["h"] - f["sw"])}" class="g" rx="{n(max(f["rx"] - m, 0))}" fill="{f["f"]}" '
                f'stroke="{f["s"]}" stroke-width="{n(f["sw"])}"{o}/>')
    if f["t"] == "x":
        mono = any(m in f.get("ff", "") for m in ("Consolas", "Mono", "Courier"))
        familia = "Consolas,Menlo,monospace" if mono else "'Segoe UI',system-ui,-apple-system,sans-serif"
        return (f'<text x="{n(f["x"])}" y="{n(f["y"])}" fill="{f["c"]}" font-size="{n(f["fs"])}" '
                f'font-weight="{f.get("fw", 400)}" font-family="{familia}"{o}>{escape(f["s"])}</text>')
    raise ValueError(f"figura desconocida: {f.get('t')!r}")


def partes_de(c):
    if "partes" in c:
        return list(c["partes"])
    if "f" in c:
        return [figura(f) for f in c["f"]]
    if "svg" in c:
        return [c["svg"]]
    return []   # cuadro vacio: pantalla sin nada


def duraciones(nombre, cuadros):
    if all("ms" in c for c in cuadros):
        return [c["ms"] for c in cuadros]
    if not all("t" in c for c in cuadros):
        sys.exit(f"{nombre}: cada cuadro necesita 'ms', o todos necesitan 't'")
    ts = [c["t"] for c in cuadros]
    huecos = [b - a for a, b in zip(ts, ts[1:])]
    if huecos and max(huecos) > HUECO_MAXIMO:
        print(f"AVISO: {nombre} tiene un hueco de {max(huecos)} ms entre cuadros: "
              "en la animacion se vera un tiron. Conviene volver a grabarla.")
    return huecos + [60]


def main():
    ap = argparse.ArgumentParser(description="Arma un SVG animado a partir de cuadros.")
    ap.add_argument("salida")
    ap.add_argument("escenas", nargs="+")
    ap.add_argument("--pausa", type=int, default=900, help="ms vacios entre escenas y antes de repetir")
    ap.add_argument("--fondo", default=None, help="color de fondo; por defecto transparente")
    a = ap.parse_args()

    escenas = []
    for ruta in a.escenas:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
        if not datos.get("cuadros"):
            sys.exit(f"{ruta}: no tiene cuadros")
        escenas.append((Path(ruta).name, datos))

    W = max(d.get("ancho", 0) for _, d in escenas)
    H = max(d.get("alto", 0) for _, d in escenas)
    if not W or not H:
        sys.exit("Falta 'ancho' y 'alto' en al menos una escena")

    css = ["rect{shape-rendering:crispEdges}.g{shape-rendering:geometricPrecision}"]
    defs, cuerpo = [], []
    bloques = []   # (desde, hasta, html)
    quietos = []
    t = 0
    for j, (nombre, d) in enumerate(escenas):
        cuadros = d["cuadros"]
        durs = duraciones(nombre, cuadros)
        grupos = [partes_de(c) for c in cuadros]
        if d.get("estilo"):
            css.append(d["estilo"])
        if d.get("defs"):
            defs.append(d["defs"])

        # Lo que esta en todos los cuadros no vacios se dibuja una vez y se reutiliza con <use>
        llenos = [g for g in grupos if g]
        fijas = set(llenos[0]) if llenos else set()
        for g in llenos[1:]:
            fijas &= set(g)
        if fijas:
            defs.append(f'<g id="e{j}">{"".join(s for s in llenos[0] if s in fijas)}</g>')

        anterior = None
        primero_escena = len(bloques)
        for c, g, dur in zip(cuadros, grupos, durs):
            dx, dy = c.get("x", 0), c.get("y", 0)
            clave = (dx, dy, tuple(g))
            if clave == anterior:
                bloques[-1][1] += dur   # cuadro identico al anterior: alarga el anterior
            else:
                anterior = clave
                if g:
                    usa = f'<use href="#e{j}"/>' if fijas else ""
                    resto = "".join(s for s in g if s not in fijas)
                    mover = f' transform="translate({n(dx)} {n(dy)})"' if dx or dy else ""
                    html = f'<g class="c f{{k}}"{mover}>{usa}{resto}</g>'
                else:
                    html = None
                bloques.append([t, t + dur, html])
            t += dur
        if j == 0:
            q = d.get("quieto")
            if q is None:   # por defecto: el cuadro visible que mas dura en la primera escena
                visibles = [i for i in range(primero_escena, len(bloques)) if bloques[i][2]]
                q = max(visibles, key=lambda i: bloques[i][1] - bloques[i][0]) if visibles else None
            else:
                q = primero_escena + min(q, len(bloques) - 1 - primero_escena)
            quietos.append(q)
        t += a.pausa
    total = t

    def pct(ms):
        return f"{ms / total * 100:.3f}".rstrip("0").rstrip(".") + "%"

    css.insert(0, f".c{{opacity:0;animation:{total / 1000:.2f}s steps(1,end) infinite}}"
                  "@media (prefers-reduced-motion:reduce){.c{animation:none}}")
    k = 0
    indice_k = {}
    for i, (desde, hasta, html) in enumerate(bloques):
        if html is None:
            continue
        claves = ("0%{opacity:0}" if desde > 0 else "") + f"{pct(desde)}{{opacity:1}}{pct(hasta)}{{opacity:0}}"
        css.append(f"@keyframes k{k}{{{claves}}}.f{k}{{animation-name:k{k}}}")
        cuerpo.append(html.replace("{k}", str(k)))
        indice_k[i] = k
        k += 1
    fijos = [f".f{indice_k[q]}" for q in quietos if q in indice_k]
    if fijos:
        css.append("@media (prefers-reduced-motion:reduce){" + ",".join(fijos) + "{opacity:1}}")

    fondo = f'<rect width="100%" height="100%" fill="{a.fondo}"/>' if a.fondo else ""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(W)}" height="{n(H)}" viewBox="0 0 {n(W)} {n(H)}" role="img">'
           f'<style>{"".join(css)}</style><defs>{"".join(defs)}</defs>{fondo}'
           f'<g xml:space="preserve">{"".join(cuerpo)}</g></svg>')
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(svg, encoding="utf-8")
    peso = salida.stat().st_size
    print(f"{salida.name}: {len(escenas)} escena(s), {k} cuadros, {total / 1000:.1f} s, "
          f"{peso / 1024:.0f} KB, {n(W)}x{n(H)}")
    if peso > PESO_AVISO:
        print("AVISO: pesa mas de 1 MB. Junta cuadros identicos, baja los cuadros por segundo o acorta la escena.")


if __name__ == "__main__":
    main()
