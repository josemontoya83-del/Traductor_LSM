"""
revisar_datos.py — ¿Qué lleva grabado cada persona y qué hay que repetir?

    python herramientas/revisar_datos.py              # resumen por persona, sesión y bloque
    python herramientas/revisar_datos.py --avisos     # además lista las tomas con avisos de calidad

Las tomas con avisos se vuelven a grabar abriendo la captura con la misma persona/sesión
después de borrar su .mp4 y .json (o con R justo después de grabarlas).
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lsm.datos import listar_clips, participantes, personas_prueba  # noqa: E402
from lsm.protocolo import cargar_protocolo, tomas  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--avisos", action="store_true")
    a = ap.parse_args()

    prot = cargar_protocolo()
    clips = listar_clips()
    gente = participantes()
    prueba = personas_prueba()
    personas = sorted(set(gente) | {c.persona for c in clips})
    if not personas:
        print("Todavía no hay grabaciones.")
        return

    por_sesion = defaultdict(set)
    for c in clips:
        por_sesion[(c.persona, c.sesion)].add(c.json.stem)

    for persona in personas:
        info = gente.get(persona, {})
        marca = "  [PRUEBA FINAL]" if persona in prueba else ""
        print(f"\n{persona}  mano {info.get('mano_dominante', '?')}{marca}")
        for sesion in prot["sesiones"]:
            esperadas = tomas(persona, sesion, incluir_opcionales=True)
            hechas = por_sesion[(persona, sesion)]
            if not hechas:
                print(f"  Sesión {sesion}: sin grabar")
                continue
            por_bloque = defaultdict(lambda: [0, 0])
            for t in esperadas:
                por_bloque[(t.bloque, t.nombre_bloque)][1] += 1
                por_bloque[(t.bloque, t.nombre_bloque)][0] += t.nombre in hechas
            total_h = sum(v[0] for v in por_bloque.values())
            print(f"  Sesión {sesion}: {total_h}/{len(esperadas)} tomas")
            for (b, nombre), (h, n) in por_bloque.items():
                estado = "OK" if h == n else ("--" if h == 0 else "..")
                print(f"     {estado} {b} {nombre:52s} {h:4d}/{n}")

    sin_puntos = [c for c in clips if not c.puntos.exists()]
    con_avisos = [c for c in clips if c.meta.get("calidad", {}).get("avisos")]
    print(f"\nTomas totales: {len(clips)} | sin extraer puntos: {len(sin_puntos)} | con avisos: {len(con_avisos)}")
    if sin_puntos:
        print("  -> corre: python herramientas/extraer_puntos.py")
    if a.avisos and con_avisos:
        print("\nTomas con avisos de calidad:")
        for c in con_avisos:
            print(f"  {c.persona}/s{c.sesion}/{c.json.stem}: "
                  f"{'; '.join(c.meta['calidad']['avisos'])}")
    if not prueba:
        print("\nRecuerda: al terminar, elige 2 personas para la prueba final en protocolo/particion.json")


if __name__ == "__main__":
    main()
