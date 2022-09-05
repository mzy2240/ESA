import numpy as np


# pythran export initialize_bound(float64[], float64[], float64[], float64[], float64[][])
def initialize_bound(bpmax, bpmin, bnmax, bnmin, A):
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


# pythran export calculate_bound(float64[][], float64[][], float64[], float64[], float64[][], float64[][])
def calculate_bound(bp, bn, Amax1, Amin1, Wbuf1, Wbuf2):
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
    w = np.maximum(wb1, wb2)
    return w


def mod_sparse_test(scipy=None):
    import numpy as np
    from scipy.sparse import csr_matrix, vstack, hstack
    row = np.array([0, 0, 1, 2, 2, 2])
    col = np.array([0, 2, 2, 0, 1, 2])
    data = np.array([1, 2, 3, 4, 5, 6])
    csr = csr_matrix((data, (row, col)), shape=(3, 3))

    row = np.array([0, 0, 1, 2, 2, 2])
    col = np.array([0, 2, 2, 0, 1, 2])
    data = np.array([0, 0, 3, 4, 5, 6])
    csr = csr_matrix((data, (row, col)), shape=(3, 3))
    print("before\n", csr)

    def get_data(ary, first_zero=False):
        """This function takes in the csr matrix, extract the first row, returns zero like matrix."""
        _col = ary.getrow(0).toarray().nonzero()[1]  # get the non-zero col
        _row = np.zeros(ary[0].data.shape)  # change data to 0
        _data = _row
        if _col.size < _row.size:
            _col = np.insert(_col, 0, -1)
        elif first_zero:
            _data = np.insert(_row, 0, -1)
            _row = np.insert(_row, 0, 0)
            _col = np.insert(_col, 0, 0)
        return csr_matrix((_data, (_row, _col)), shape=ary[0].shape)  # create zero like csr matrix

    v_csr = vstack([get_data(csr), csr[1:]]).T
    csr = vstack([get_data(v_csr,True), v_csr[1:]]).T
    print("processed", csr)



if __name__ == "__main__":
    mode_sparse_test()
