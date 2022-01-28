"""Run this script to automatically compile AOT functions for python 3.7, 3.8 and 3.9
"""
import argparse
import os
import subprocess
import shutil



def main():
    list_of_envs = []
    envs = subprocess.check_output('conda env list').splitlines()[2:-1]
    for string in envs:
        try:
            list_of_envs.append(string.decode("utf-8").split()[0])
        except IndexError:
            pass
    print(list_of_envs)
    # print(env_name)

    versions = ['37', '38', '39']  # pythran seems to only work in 3.7 3.8 3.9

    for ver in versions:
        # Create a virtual environment if necessary.
        if f"compile{ver}" in list_of_envs:
            print(f"No need to create Conda python {ver} env")
        else:
            subprocess.run(f'conda create -n compile{ver} python={ver[0]}.{ver[1]} -y')
            subprocess.run(f'conda activate compile{ver} && conda install -c conda-forge "numpy<1.22" pythran -y', shell=True)

        # Compile
        compile_statement = f"pythran --config compiler.blas=mkl -O3 -ffast-math -DUSE_XSIMD esa/_performance.py -o esa/performance{ver}.pyd"
        subprocess.run(f"conda activate compile{ver} && {compile_statement}", shell=True)
        print('DONE!')

    print('*' * 80)
    print('ALL DONE!')




if __name__ == '__main__':
    main()

