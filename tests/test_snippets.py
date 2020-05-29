"""This testing module runs all the code snippets in the
docs/rst/snippets directory."""

import unittest
import doctest
import logging

from esa import SAW
# noinspection PyUnresolvedReferences
from tests.constants import CASE_MAP, SNIPPET_FILES, CANDIDATE_LINES, PATH_14

# Set up log.
LOG = logging.getLogger()

# The broken snipped is:
BROKEN = 'weighted_graph_14.rst'
# Version threshold:
BROKEN_THRESHOLD = 21

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
    # We need to get the Simulator version so we can skip tests that are
    # broken for certain versions.
    saw_14 = SAW(PATH_14)
    version = saw_14.get_simulator_version(delete_when_done=True)
    saw_14.exit()
    del saw_14

    out = []
    # Loop over the available cases.
    for suffix, case_path in CASE_MAP.items():
        # Filter files by suffix, which corresponds to the case.
        files = [x for x in SNIPPET_FILES if x.endswith(suffix + '.rst')]

        if len(files) > 0:
            # Recreate a list that excludes the broken file. For now,
            # we'll skip if the version is less than 21.
            if version < BROKEN_THRESHOLD:
                not_broken_files = [x for x in files if BROKEN not in x]
                if len(not_broken_files) != len(files):
                    LOG.warning(
                        'The snippet {} is being skipped because the '
                        'Simulator version is < {}'.format(BROKEN,
                                                           BROKEN_THRESHOLD))
            else:
                not_broken_files = files

            # Define global variables needed for the examples.
            g = {'CASE_PATH': case_path}
            if '2000' in suffix:
                # One example adds lines and depends on a .csv file.
                g['CANDIDATE_LINES'] = CANDIDATE_LINES

            # Create a DocFileSuite.
            out.append(doctest.DocFileSuite(
                *not_broken_files, module_relative=False,
                globs=g))

    return out


if __name__ == '__main__':
    unittest.main()
