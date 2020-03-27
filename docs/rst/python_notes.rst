The authors of ESA have tested with Python 3.5, 3.6, 3.7, and 3.8. Many
users may find it easiest to use Anaconda, but this is not recommended
for users familiar with using Pip and/or virtual environments directly
(or via PyCharm), as Anaconda provides an unnecessarily bloated
installation.

Important Notes for PyCharm + Python 3.8
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use PyCharm to automatically create virtual environments for you,
there's a little extra work to do to get everything working for Python
3.8. Start up a terminal *inside* PyCharm (click on the ``Terminal``
button which defaults to the lower left area). In the terminal, run:
``python -m pip install -U --force-reinstall pip``. Note you may need to
run this command twice - mine failed the first time.