"""This testing module runs all the code snippets in the
docs/rst/snippets directory."""

import unittest
import doctest

# noinspection PyUnresolvedReferences
from constants import CASE_MAP, SNIPPET_FILES, CANDIDATE_LINES

########################################################################
# DOC TESTS
########################################################################
# The "load_tests" and "get_snippet_suites" methods below take care of
# everything needed to run all the snippets.


# To enable unittest discovery:
# https://docs.python.org/3.8/library/doctest.html#unittest-api
# noinspection PyUnusedLocal
def load_tests(loader, tests, ignore):
    suites = get_snippet_suites()
    for s in suites:
        tests.addTests(s)
    return tests


def get_snippet_suites():
    """Return list of DocFileSuites"""
    out = []
    # Loop over the available cases.
    for suffix, case_path in CASE_MAP.items():
        # Filter files by suffix, which corresponds to the case.
        files = [x for x in SNIPPET_FILES if x.endswith(suffix + '.rst')]

        if len(files) > 0:

            # Define global variables needed for the examples.
            g = {'CASE_PATH': case_path}
            if '2000' in suffix:
                # One example adds lines and depends on a .csv file.
                g['CANDIDATE_LINES'] = CANDIDATE_LINES

            # Create a DocFileSuite.
            out.append(doctest.DocFileSuite(
                *files, module_relative=False,
                globs=g))

    return out


if __name__ == '__main__':
    unittest.main()
