Easy SimAuto (ESA)
==================

Easy SimAuto (ESA) is an easy-to-use Python package that simplifies
interfacing with PowerWorld's Simulator Automation Server (SimAuto). ESA
wraps all PowerWorld SimAuto functions, and also provides helper
functions to further simplify working with SimAuto. Wherever possible,
data is returned as Pandas DataFrames, making analysis a breeze. ESA is
well tested and fully `documented`_.

`Documentation`_
----------------
For quick-start directions, installation instructions, API reference,
examples, and more, please check out ESA's `documentation`_.

If you have your own copy of the ESA repository, you can also view the
documentation locally by navigating to the directory ``docs/html`` and
opening ``index.html`` with your web browser.

Citation
--------

If you use ESA in any of your work, please use the following citation:

.. code:: latex

   @misc{ESA,
     author = {Zeyu Mao and Brandon Thayer and Yijing Liu},
     title = {Easy SimAuto (ESA)},
     year = {2020},
     publisher = {GitHub},
     journal = {GitHub repository},
     howpublished = {\url{https://github.com/mzy2240/ESA}},
     commit = {<copy + paste the specific commit you used here>}
   }

Installation
------------
Please refer to ESA's `documentation`_ for full, detailed installation
directions. In many cases, ESA can simply be installed by:

.. code:: bat

    python -m pip install --only-binary pywin32,pypiwin32 pywin32 pypiwin32 esa

License
-------

`MIT <https://choosealicense.com/licenses/mit/>`__

Contributing
------------

We welcome contributions! Please read ``contributing.md``.

.. _documentation: https://github.com/mzy2240/ESA
.. _documented: https://github.com/mzy2240/ESA

