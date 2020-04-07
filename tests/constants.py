"""Module to hold constants for testing."""
import os

# Handle pathing.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(THIS_DIR, 'cases')
DATA_DIR = os.path.join(THIS_DIR, 'data')
SNIPPET_DIR = os.path.join(THIS_DIR, '..', 'docs', 'rst', 'snippets')
SNIPPET_FILES = [os.path.join(SNIPPET_DIR, x) for x in
                 os.listdir(SNIPPET_DIR) if x.endswith('.rst')]

# Path to IEEE 14 bus model.
PATH_14 = os.path.join(CASE_DIR, 'ieee_14', 'IEEE 14 bus.pwb')
PATH_14_PWD = os.path.join(CASE_DIR, 'ieee_14', 'IEEE 14 bus.pwd')

# Path to the Texas 2000 bus model.
PATH_2000 = os.path.join(CASE_DIR, 'tx2000', 'tx2000_base.PWB')
PATH_2000_mod = os.path.join(
    CASE_DIR, 'tx2000_mod', 'ACTIVSg2000_AUG-09-2018_Ride_version7.PWB')

# Path to the WSCC model.
PATH_9 = os.path.join(CASE_DIR, 'wscc_9', 'WSCC 9 bus.pwb')

# Aux file for filtering transformers by LTC control.
LTC_AUX_FILE = os.path.join(THIS_DIR, 'ltc_filter.aux')

# Map cases for doc testing.
CASE_MAP = {'14': PATH_14, '2000': PATH_2000}

# Path to file containing lines for one of the examples.
CANDIDATE_LINES = os.path.join(DATA_DIR, 'CandidateLines.csv')