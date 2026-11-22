import numpy as np

import sinteticos as S
from lsm import puntos as P
from lsm.rasgos import (canonizar, espejar, indices_remuestreo, mano_dominante, rasgos_mano,
                        secuencia_sena, MAX_CUADROS_SENA)
from lsm.segmentador import Segmentador, segmentar_clip, segmento_principal


def test_espejar_dos_veces_es_identidad():
    clip = S.clip_letra(1)
    doble = espejar(espejar(clip))
    for k in P.PARTES:
        np.testing.assert_allclose(doble[k], clip[k], atol=1e-6)


def test_forma_de_mano_no_depende_de_distancia_ni_posicion():
    forma = S.plantilla(3)
    cerca = S._mano(np.array([0.3, 0.2]), forma, np.random.default_rng(0), escala=0.08)
    lejos = (cerca - cerca[0]) * 0.5 + np.array([0.6, 0.4, 0.0], np.float32)
    np.testing.assert_allclose(rasgos_mano(cerca, None)[:63], rasgos_mano(lejos, None)[:63], atol=1e-4)


def test_zurdo_se_canoniza_igual_que_diestro():
    diestro, zurdo = S.clip_letra(5, semilla=1), S.clip_letra(5, semilla=1, zurdo=True)
    assert mano_dominante(diestro) == "der" and mano_dominante(zurdo) == "izq"
    canon, espejo = canonizar(zurdo)
    assert espejo
    np.testing.assert_allclose(canon["mano_der"], diestro["mano_der"], atol=1e-5)


def test_segmentador_encuentra_una_sena_con_margenes():
    clip = S.clip_sena(0)
    eventos = segmentar_clip(clip)
    assert len(eventos) == 1
    ev = eventos[0]
    dur = ev.tiempos[-1] - ev.tiempos[0]
    assert 1.2 < dur < 2.4, dur


def test_segmentador_ignora_reposo():
    clip = S.clip_desde_guion([(3.0, None, None)])
    assert segmentar_clip(clip) == []


def test_segmentador_corta_por_duracion_maxima():
    forma = S.plantilla(1)
    clip = S.clip_desde_guion([(0.3, None, None), (5.0, lambda r: S.ARRIBA_D, forma)])
    seg = Segmentador(max_duracion=2.0)
    cierres = [seg.empujar(float(t), P.cuadro(clip, i)).tipo for i, t in enumerate(clip["t"])].count("cierre")
    assert cierres >= 2


def test_secuencia_de_sena_tiene_forma_fija_y_es_igual_a_cualquier_fps():
    a = secuencia_sena(segmento_principal(S.clip_sena(2, fps=30)).clip())[0]
    b = secuencia_sena(segmento_principal(S.clip_sena(2, fps=12)).clip())[0]
    assert a.shape == b.shape == (MAX_CUADROS_SENA, a.shape[1])
    na, nb = (np.abs(a).sum(1) > 0).sum(), (np.abs(b).sum(1) > 0).sum()
    assert abs(na - nb) <= 2


def test_remuestreo_limita_cuadros():
    t = np.arange(0, 20, 1 / 30)
    assert len(indices_remuestreo(t)) == MAX_CUADROS_SENA
