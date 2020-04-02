"""Run this with any version of Python >= 3.5 to test ESA on all
installed versions of Python. Ensure you run this from the 'tests'
directory.

Prior to running this script, you should install all supported Python
versions to your system (>= 3.5).

For help, simply run this script like:
python _test_python_versions.py -h
"""
import argparse
import os
import subprocess
import shutil

# Current directory and top-level repository directory.
THIS_DIR = os.getcwd()
TOP_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))


def main(python_install_dir, local, fresh):
    # Get Python directories.
    # https://stackoverflow.com/a/973492/11052174
    dirs = [os.path.join(python_install_dir, o) for o in
            os.listdir(python_install_dir)
            if os.path.isdir(os.path.join(python_install_dir, o))]

    # Initialize listing of output files.
    out_files = []

    # Loop.
    for d in dirs:
        # Get last two characters of d.
        code = d[-2:]
        assert code in ('35', '36', '37', '38'), 'Only Python >= 3.5!'

        print('*' * 80)
        print('Doing work for Python {}'.format(code))

        # Name of virtual environment to create.
        venv_name = os.path.join(THIS_DIR, 'test-venv-{}'.format(code))

        # Create a virtual environment if necessary.
        if os.path.isdir(venv_name) and (not fresh):
            print('No need to create {}'.format(venv_name))
        else:
            print('Creating {}...'.format(venv_name))
            if fresh:
                print('Removing existing virtual environment since the '
                      '"fresh" argument was supplied.')

                shutil.rmtree(venv_name, ignore_errors=True)

            subprocess.run((os.path.join(d, 'python.exe'),
                            '-m', 'venv', venv_name))
            print('Done.')

        # Get full path to executable Python file.
        exe = os.path.join(venv_name, 'Scripts', 'python.exe')

        # Check things are working:
        # subprocess.run((exe, '-c', 'import sys; print(sys.version);'))

        # Upgrade pip and setuptools.
        subprocess.run((exe, '-m', 'pip', 'install', '--upgrade',
                        '--no-cache-dir', 'pip', 'setuptools'))

        # Define command for installing ESA.
        cmd_tuple = \
            (exe, '-m', 'pip', 'install', '--upgrade', '--no-cache-dir')

        # Add --force-reinstall if desired.
        if fresh:
            cmd_tuple += ('--force-reinstall',)

        # Install ESA, including the test dependencies.
        if not local:
            subprocess.run(cmd_tuple + ('esa[test]',))
        else:
            subprocess.run(cmd_tuple + ('.[test]',), cwd=TOP_DIR)

        # Define output file for testing results.
        out_file = os.path.join(THIS_DIR, 'test_results_{}'.format(code))
        out_files.append(out_file)

        # Run the tests.
        with open(out_file, 'w') as f:
            subprocess.run(
                (exe, '-m', 'unittest', 'discover', 'tests'), cwd=TOP_DIR,
                stderr=subprocess.STDOUT, stdout=f)

    print('*' * 80)
    print('ALL DONE!')
    print('View results in the following files:')
    print(out_files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'python_install_dir',
        help='Full path to directory where all Python installations exist.',
        type=str)
    parser.add_argument(
        '--local', action='store_true', help='Set this flag to install ESA '
        'locally from source. If this flag is not set, ESA will be installed '
        'from PyPi.')
    parser.add_argument(
        '--fresh', action='store_true', help='Set this flag to force fresh '
        'virtual environments and packages. Existing virtual environments '
        'from a previous run of this script will be removed, and packages '
        'will be installed with the --force-upgrade flag.'
    )
    args_in = parser.parse_args()
    main(python_install_dir=args_in.python_install_dir, local=args_in.local,
         fresh=args_in.fresh)

