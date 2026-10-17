"""TraceMark API package."""

import os

# Set before NumPy import and inherit into spawned image processors.
for _thread_setting in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_setting] = "1"

__version__ = "0.2.0"
