The simplest way to verify that ESA installed correctly is to attempt
to import it. Most (but not all) installation issues will rear their
heads at this point. Simply execute the following in a Command Prompt
window (ensure your virtual environment is activated!):

.. code:: bat

    python -c "import esa; print('Success!')"

If an error message is emitted, ESA or its dependencies are not properly
installed. If you're unable to figure it out on your own, feel free to
file an issue on `GitHub <https://github.com/mzy2240/ESA/issues>`__. We
do not guarantee that we can help everyone.
