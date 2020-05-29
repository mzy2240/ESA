cases
=====

Use this directory to store PowerWorld cases for testing. Make sure the
cases are public - don't share any private cases! Ideally, you'll
include the case saved in a variety of Simulator formats (e.g. 16, 17,
18, 19, 20, 21) so that users who do not have the same Simulator version
as you can still leverage them. Please note the naming conventions:
cases end with ``_pws_version_<VERSION GOES HERE>.pwb``.

dummy_case.PWB
--------------
This is a case that literally has a single bus and nothing else. This is
intentional - it's only used so that during testing a ``SAW`` instance
can be quickly loaded up to determine the Simulator version.

ieee_14
-------

IEEE 14-bus test case downloaded from `here <https://electricgrids.engr.tamu.edu/electric-grid-test-cases/ieee-14-bus-system/>`__
on 2019-09-25.

tx2000
------

This directory contains a variant of the Texas 2000 bus synthetic 
grid. You can find a version of this model (though possibly not
identical) on Texas A&M's `website <https://electricgrids.engr.tamu.edu/electric-grid-test-cases/>`__.
This particular case was provided by `Adam Birchfield <http://adambirchfield.com/>`__.
on 2019-11-21.

tx2000_mod
----------

This directory contains a variant of the Texas 2000 bus synthetic grid
modified for voltage control experiments. This case was provided by
Diana Wallison (diwalli@tamu.edu).

wscc_9
------

This directory contains an approximation of the Western System
Coordinating Council (WSCC) system. This model is commonly used for
dynamics simulations. It was `downloaded from Texas A&M
<https://electricgrids.engr.tamu.edu/electric-grid-test-cases/wscc-9-bus-system/>`__
on 2020-04-01.
