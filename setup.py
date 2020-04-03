import setuptools
import os

with open('VERSION', 'r') as fh:
    __version__ = fh.read()

with open("README.rst", "r") as fh:
    long_description = fh.read()

# Append the version to __init__ before installing.
with open(os.path.join('esa', '__init__.py'), 'a') as fh:
    fh.write('__version__ = "{}"\n'.format(__version__))

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
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
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
    install_requires=['pandas >= 0.25', 'numpy >= 1.13.3', 'pywin32',
                      'pypiwin32'],
    python_requires='>=3.5',
    # There are a couple tests that use networkx, and we use the magic
    # of sphinx for documentation. Coverage is necessary to keep the
    # coverage report up to date.
    extras_require={'test': ['networkx', 'coverage'],
                    'doc': ['sphinx', 'tabulate']},
    license='MIT',
    # TODO: Why aren't we zip safe?
    zip_safe=False
)
