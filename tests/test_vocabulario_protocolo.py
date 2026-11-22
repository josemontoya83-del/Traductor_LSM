from collections import Counter

from lsm.protocolo import cargar_protocolo, tomas
from lsm.vocabulario import cargar, normalizar


def test_vocabulario_sin_ids_repetidos():
    v = cargar()
    ids = [s["id"] for s in v.senas()]
    assert len(ids) == len(set(ids)), [i for i, n in Counter(ids).items() if n > 1]
    assert len(v.letras) == 30 and len(v.numeros) == 10
    assert v.dominios_activos(["escolar"]) == ["general", "escolar"]
    assert v.dominios_activos(["no_existe"]) == ["general"]


def test_lexico_y_normalizar():
    v = cargar()
    lex = v.lexico(["escolar"])
    assert lex["kardex"] == "Kárdex"
    assert normalizar("¿Niño?") == "niño"
    assert normalizar("Inscripción") == "inscripcion"


def test_cantidad_de_tomas_por_sesion():
    s1, s2 = tomas("P01", "1"), tomas("P01", "2")
    assert len(s1) == 30 * 2 + 10 * 2 + 55 * 3 + 12 + 6 == 263
    assert len(s2) == 30 * 2 + 10 + 55 * 3 + 12 + 6 == 253
    assert len(tomas("P01", "2", bloques=["G"])) == 12        # opcional, solo si se pide
    for lista in (s1, s2):
        nombres = [t.nombre for t in lista]
        assert len(nombres) == len(set(nombres))


def test_repeticiones_continuan_entre_sesiones():
    r1 = {t.repeticion for t in tomas("P01", "1") if t.etiqueta == "kardex" and t.tipo == "sena"}
    r2 = {t.repeticion for t in tomas("P01", "2") if t.etiqueta == "kardex" and t.tipo == "sena"}
    assert r1 == {1, 2, 3} and r2 == {4, 5, 6}


def test_orden_barajado_pero_reproducible():
    a = [t.nombre for t in tomas("P01", "1")]
    assert a == [t.nombre for t in tomas("P01", "1")]
    assert a != [t.nombre for t in tomas("P02", "1")]


def test_deletreo_cubre_todo_el_alfabeto():
    prot, v = cargar_protocolo(), cargar()
    palabras = " ".join(prot["deletreo"]["1"] + prot["deletreo"]["2"]).lower()
    for letra in v.letras:
        assert letra["id"] in palabras, letra["id"]
