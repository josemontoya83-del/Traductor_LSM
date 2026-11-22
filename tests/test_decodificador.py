import numpy as np

from lsm.decodificador import DecodificadorLetras, buscar_en_lexico
from lsm.vocabulario import NADA, cargar

CLASES = ["a", "b", "c", "d", "e", "k", "r", "x", "ll", "1", NADA]


def _uno(c, p=0.9):
    v = np.full(len(CLASES), (1 - p) / (len(CLASES) - 1), np.float32)
    v[CLASES.index(c)] = p
    return v


def _secuencia(letras, n=6, transicion=2):
    out = []
    for l in letras:
        out += [_uno(l)] * n + [_uno(NADA, 0.6)] * transicion
    return out


def test_decodifica_palabra():
    d = DecodificadorLetras(CLASES)
    for p in _secuencia(["k", "a", "r", "d", "e", "x"]):
        d.empujar(p)
    assert d.terminar() == "KARDEX"


def test_letra_doble_solo_con_pausa():
    d = DecodificadorLetras(CLASES)
    for p in [_uno("c")] * 15:      # sostener mucho una letra NO la repite
        d.empujar(p)
    assert d.texto == "C"
    for p in [_uno(NADA, 0.7)] * 4 + [_uno("c")] * 6:   # después de una pausa sí
        d.empujar(p)
    assert d.texto == "CC"


def test_permitir_solo_numeros():
    d = DecodificadorLetras(CLASES, permitidas={"1"})
    v = np.full(len(CLASES), 0.01, np.float32)
    v[CLASES.index("ll")], v[CLASES.index("1")] = 0.6, 0.3   # gana "ll", pero solo se permiten números
    for _ in range(6):
        d.empujar(v)
    assert d.texto == "1"


def test_ruido_no_escribe():
    d = DecodificadorLetras(CLASES)
    rng = np.random.default_rng(0)
    for _ in range(50):
        d.empujar(rng.dirichlet(np.ones(len(CLASES))))
    assert d.texto == ""


def test_lexico_corrige_errores():
    lex = cargar().lexico(["escolar"])
    assert buscar_en_lexico("KARDES", lex)[0][0] == "Kárdex"
    assert buscar_en_lexico("INSCRIPSION", lex)[0][0] == "Inscripción"
    assert buscar_en_lexico("ENSENADA", lex)[0] == ("Ensenada", 1.0)
