"""Las pruebas usan carpetas temporales para datos y modelos (nunca tocan datos/ ni modelos/)."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="lsm_pruebas_")
os.environ["LSM_DATOS"] = os.path.join(_TMP, "datos")
os.environ["LSM_MODELOS"] = os.path.join(_TMP, "modelos")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
