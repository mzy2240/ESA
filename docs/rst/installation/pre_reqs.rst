ESA has the following prerequisites:

*   Microsoft Windows Operating System (PowerWorld is Windows only. The
    authors of ESA have only ever attempted to use Windows 10.).
*   Python >=3.5. Download it `here
    <https://www.python.org/downloads/>`__.
*   `PowerWorld <https://www.powerworld.com/>`__ Simulator with
    the `Automation Server (SimAuto) add-on
    <https://www.powerworld.com/products/simulator/add-ons-2/simauto>`__
    installed.

    * **NOTE**: the authors of ESA have tested with Simulator
      versions 17 and 21. It is likely, but **not guaranteed**, that ESA
      will work with all Simulator versions 16-21. If you encounter a
      problem with a particular version, please file an `issue
      <https://github.com/mzy2240/ESA/issues>`__ and we may be able
      to help (if we can get access to that particular Simulator
      version).

*   `Git Large File Storage (LFS) <https://git-lfs.github.com/>`__
    (**OPTIONAL**: required to download case files and run tests). After
    installing Git LFS, simply change directories to the ESA repository,
    and run ``git lfs install``. You will likely need to run a
    ``git pull`` or ``git lfs pull`` after installing and setting up Git
    LFS. After initial setup, you shouldn't need to do anything else
    with Git LFS.