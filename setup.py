import setuptools
import os
import re

with open('VERSION', 'r') as fh:
    __version__ = fh.read()

with open("README.rst", "r") as fh:
    long_description = fh.read()

# Update the __version__ in __init__ before installing:
# Path to __init__.py:
init_path = os.path.join('esa', '__init__.py')
# Read __init__.py:
with open(init_path, 'r') as fh:
    __init__ = fh.read()

# Update the version:
__init__ = re.sub(r'__version__\s*=\s*[\'"][0-9]+\.[0-9]+\.[0-9]+[\'"]',
                  '__version__ = "{}"'.format(__version__),
                  __init__)

# Write new __init__.py:
with open(init_path, 'w') as fh:
    fh.write(__init__)

setuptools.setup(
    name='esa',
    version=__version__,
    description='Easy SimAuto (ESA): An easy-to-use Python connector to '
                'PowerWorld Simulator Automation Server (SimAuto).',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author='Zeyu Mao, Brandon Thayer, Yijing Liu',
    author_email='zeyumao2@tamu.edu, blthayer@tamu.edu, yiji21@tamu.edu',
    url='https://github.com/mzy2240/ESA',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Topic :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development",

    ],
    keywords=['Python', 'PowerWorld', 'PowerWorld Simulator', 'Simulator',
              'PowerWorld Simulation Automation Server', 'SimAuto',
              'Automation', 'Power Systems', 'Electric Power', 'Power',
              'Easy SimAuto', 'ESA', 'Smart Grid', 'Numpy', 'Pandas'],
    install_requires=['pandas >= 0.25', 'numpy >= 1.19.5, <1.22', 'scipy', 'pywin32',
                      'pypiwin32', 'networkx', 'tqdm', 'numba'],
    python_requires='>=3.7',
    # There are a couple tests that use networkx, and we use the magic
    # of sphinx for documentation. Coverage is necessary to keep the
    # coverage report up to date.
    extras_require={'test': ['networkx', 'coverage', 'matplotlib'],
                    'doc': ['sphinx', 'tabulate'],
                    'dev': ['pythran']},
    license='MIT',
    # TODO: Why aren't we zip safe?
    zip_safe=False
)
