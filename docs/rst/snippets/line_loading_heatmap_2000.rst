This examples shows how to make various of plots using Matplotlib. Matplotlib is a comprehensive library for creating static, animated, and interactive visualizations in Python. You'll first need to install Matplotlib into your virtual environment (which should be activated!), which is most easily done by.
  
.. code:: bat

    python -m pip install -U matplotlib
 
Before following along with the example, define the CASE_PATH constant like so, adapting the path to your system.

.. code:: python

  CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base.PWB"
  
Now let's get started!

Perform imports, initialize a ``SAW`` instance.

.. code:: python

    >>> from esa import SAW
    >>> import pandas as pd
    >>> import matplotlib.pyplot as plt
