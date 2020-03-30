All files within this directory will be used for performing tests, using
the ``doctest`` module. As all ESA tests will require a .pwb file,
please define the full path to that .pwb file as CASE_PATH in the files.
So that the tests know which case to use for CASE_PATH, use a suffix on
the file names.

*   14 --> IEEE 14 bus case
*   2000 --> Texas 2000 bus case (not the modified version)

Also note that all ``2000`` snippets will be passed the
``CANDIDATE_LINES`` variable during testing, as that's needed for
"add_lines_2000.rst".