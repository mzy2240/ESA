"""This module runs the ESA tests and evaluates testing coverage. The
top-level README.rst file will be automatically updated, and a new file
which can be included in the documentation, coverage.rst, is generated.

Please run this script from the directory it exists in.
"""
from coverage import Coverage
from unittest import TestLoader, TestResult
import os
import json
from tabulate import tabulate
from collections import OrderedDict
import subprocess
import datetime
import re

# Paths:
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TOP_LEVEL = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))
TEST_DIR = os.path.join(TOP_LEVEL, 'tests')
ESA_DIR = os.path.join(TOP_LEVEL, 'esa')
JSON_FILE = os.path.join(THIS_DIR, 'coverage.json')
README = os.path.join(TOP_LEVEL, 'README.rst')


def main():
    # Initialize coverage stuff.
    cov = Coverage(source=[ESA_DIR])
    cov.start()

    # Run tests.
    run_tests()

    # Stop collecting coverage data.
    cov.stop()

    # Create a json report so we can easily get data into a dictionary.
    cov.json_report(outfile=JSON_FILE)

    # Read the json report.
    with open(JSON_FILE, 'r') as f:
        report_dict = json.load(f)

    # Clean up after yourself:
    os.remove(JSON_FILE)

    # Initialize dictionary for creating our table.
    table_dict = OrderedDict()
    table_dict['Name'] = []
    table_dict['Num. Statements'] = []
    table_dict['Missing Lines'] = []
    table_dict['Covered Lines'] = []
    table_dict['Percent Coverage'] = []

    # Map keys from coverage to keys in the table_dict.
    key_map = {'num_statements': 'Num. Statements',
               'missing_lines': 'Missing Lines',
               'covered_lines': 'Covered Lines',
               'percent_covered': 'Percent Coverage'}

    # Loop through the files and collect information.
    for key, value in report_dict['files'].items():
        # Extract the filename and summary data.
        filename = os.path.basename(key)
        s = value['summary']

        # Add the filename.
        table_dict['Name'].append('esa/' + filename)

        # Loop over the map and append.
        for s_key, t_key in key_map.items():
            table_dict[t_key].append(s[s_key])

    # Tabulate.
    rst_table = tabulate(table_dict, tablefmt='grid', headers='keys')

    # Get today's date.
    date = str(datetime.datetime.now().date())

    # Get the short git hash:
    # https://stackoverflow.com/a/21901260/11052174
    git_hash = subprocess.check_output(['git', 'rev-parse', '--short',
                                        'HEAD']).strip().decode('utf-8')

    # Read the README
    with open(README, 'r') as f:
        readme = f.read()

    # Add four spaces to each newline.
    rst_table = re.sub('\n', '\n    ', rst_table)
    # Add four spaces to the beginning.
    rst_table = '    {}'.format(rst_table)

    # Generate section.
    new_section = (".. table:: ESA's testing coverage as of {} (Git commit: {})"
                   .format(date, git_hash)
                   + '\n    :widths: auto\n    :align: left\n\n{}\n'
                   .format(rst_table))

    # Substitute the new section in.
    readme = re.sub("\.\.\stable::\sESA's\stesting\scoverage(.*)\+\n",
                    new_section, readme, flags=re.DOTALL)

    # Write modified readme.
    with open(README, 'w') as f:
        f.write(readme)

    # Write the section to file.
    with open(os.path.join(THIS_DIR, 'coverage.rst'), 'w') as f:
        f.write(new_section)


def run_tests():
    loader = TestLoader()
    suite = loader.discover(start_dir=TEST_DIR)
    result = TestResult()
    suite.run(result)


if __name__ == '__main__':
    main()
