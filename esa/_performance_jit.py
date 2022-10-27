import numpy as np

# Import numba
try:  # pragma: no cover
    import numba as nb

    use_numba = True
except ImportError:
    use_numba = False


def _initialize_bound(bpmax, bpmin, bnmax, bnmin, A):
    bp0 = A.copy()
    bp1 = A.copy()
    bn0 = A.copy()
    bn1 = A.copy()
    for i in range(len(bpmax)):
        bp0[i, :] *= bpmax[i]
        bp1[i, :] *= bpmin[i]
        bn0[i, :] *= bnmax[i]
        bn1[i, :] *= bnmin[i]
    Wbuf1 = np.maximum(bp0, bp1)
    Wbuf2 = np.maximum(bn0, bn1)
    w = np.maximum(Wbuf1 + Wbuf1.conj().T, Wbuf2 + Wbuf2.conj().T)
    return w, Wbuf1, Wbuf2


def _calculate_bound(bp, bn, Amax1, Amin1, Wbuf1, Wbuf2):
    bp0 = bp.copy()
    bp1 = bp.copy()
    bn0 = bn.copy()
    bn1 = bn.copy()
    for i in range(len(Amax1)):
        bp0[:, i] *= Amax1[i]
        bp1[:, i] *= Amin1[i]
        bn0[:, i] *= Amax1[i]
        bn1[:, i] *= Amin1[i]
    wb1 = np.maximum(bp0, bp1) + Wbuf1
    wb2 = np.maximum(bn0, bn1) + Wbuf2
    return np.maximum(wb1, wb2)


if use_numba:  # pragma: no cover
    initialize_bound = nb.njit()(_initialize_bound)
    calculate_bound = nb.njit()(_calculate_bound)
else:  # pragma: no cover
    initialize_bound = _initialize_bound
    calculate_bound = nb.njit()(_calculate_bound)
