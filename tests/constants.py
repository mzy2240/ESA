"""Module to hold constants for testing."""
import os
from esa import SAW

# Handle pathing.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(THIS_DIR, 'cases')
DUMMY_CASE = os.path.join(CASE_DIR, 'dummy_case.pwb')
DATA_DIR = os.path.join(THIS_DIR, 'data')
SNIPPET_DIR = os.path.join(THIS_DIR, '..', 'docs', 'rst', 'snippets')
SNIPPET_FILES = [os.path.join(SNIPPET_DIR, x) for x in
                 os.listdir(SNIPPET_DIR) if x.endswith('.rst')]

# Use the dummy case to get the version of Simulator.
saw = SAW(DUMMY_CASE)
VERSION = saw.get_simulator_version(delete_when_done=True)
saw.exit()
del saw

# Path to IEEE 14 bus model.
PATH_14 = os.path.join(CASE_DIR, 'ieee_14',
                       'IEEE 14 bus_pws_version_{}.pwb'.format(VERSION))
# TODO: Update all PWD files with versions when we create them.
PATH_14_PWD = os.path.join(CASE_DIR, 'ieee_14', 'IEEE 14 bus.pwd')

# Path to the Texas 2000 bus model.
PATH_2000 = os.path.join(CASE_DIR, 'tx2000',
                         'tx2000_base_pws_version_{}.pwb'.format(VERSION))
PATH_2000_mod = os.path.join(
    CASE_DIR, 'tx2000_mod',
    'ACTIVSg2000_AUG-09-2018_Ride_version7_pws_version_{}.pwb'.format(VERSION))

# Path to the WSCC model.
PATH_9 = os.path.join(CASE_DIR, 'wscc_9',
                      'WSCC 9 bus_pws_version_{}.pwb'.format(VERSION))

# Aux file for filtering transformers by LTC control.
LTC_AUX_FILE = os.path.join(THIS_DIR, 'ltc_filter.aux')

# Map cases for doc testing.
CASE_MAP = {'14': PATH_14, '2000': PATH_2000}

# Path to file containing lines for one of the examples.
CANDIDATE_LINES = os.path.join(DATA_DIR, 'CandidateLines.csv')
