from types import SimpleNamespace

import numpy as np

from lsm import puntos as P


def _lm(n, x=0.5, y=0.5):
    return SimpleNamespace(landmark=[SimpleNamespace(x=x + i * 1e-3, y=y, z=0.01, visibility=0.9) for i in range(n)])


def test_extraer_convierte_y_a_anchos_de_imagen():
    res = SimpleNamespace(right_hand_landmarks=_lm(21, y=0.8), left_hand_landmarks=None,
                          pose_landmarks=_lm(33, y=0.4), face_landmarks=_lm(468, y=0.2))
    c = P.extraer(res, relacion=0.75)                  # imagen 4:3
    assert c["mano_der"].shape == (21, 3) and np.allclose(c["mano_der"][:, 1], 0.6)
    assert not c["mano_izq"].any()                      # mano no detectada = ceros
    assert np.allclose(c["pose"][:, 3], 0.9) and np.isclose(c["pose"][0, 1], 0.3)
    assert c["cara"].shape == (P.N_CARA, 3)
    assert np.isclose(c["cara"][5, 0], 0.5 + P.CARA_IDX[5] * 1e-3)   # toma los índices correctos
    assert P.hay_mano(c) and P.hay_hombros(c)


def test_guardar_y_cargar(tmp_path):
    clip = P.apilar([P.vacio() for _ in range(4)], [0, 0.1, 0.2, 0.3])
    P.guardar(tmp_path / "x.npz", clip)
    otro = P.cargar(tmp_path / "x.npz")
    assert otro["version"] == P.VERSION_EXTRACTOR
    assert otro["pose"].shape == (4, 33, 4) and np.allclose(otro["t"], clip["t"])
