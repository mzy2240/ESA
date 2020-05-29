"""Helper script to find all .pwb files located in subdirectories and
save them into a different PowerWorld Simulator version format. Be sure
to run this script from the directory in which it resides.
"""
import argparse
import os
from esa import SAW


def main(version):
    """Recurse through the directories at this level, locate .pwb files,
    and save them into a different PWB format.
    """
    # Walk the subdirectories.
    for root, dirs, files in os.walk("."):
        # Extract subdirectory paths.
        path = root.split(os.sep)

        # Skip "this" directory.
        if len(path) == 1:
            continue

        # Get absolute path to subdirectory.
        full_dir_path = os.path.abspath(path[1])

        # List out pwb files.
        pwb_files = [p for p in os.listdir(full_dir_path)
                     if p.lower().endswith('.pwb')]

        # Loop over .pwb files, create SAW instance, save case in the
        # given format.
        for pf in pwb_files:
            # Instantiate SAW instance.
            saw = SAW(FileName=os.path.join(full_dir_path, pf))

            for version in [16, 17, 18, 19, 20, 21]:
                # Create "FileType" argument.
                file_type = 'PWB{}'.format(version)

                # Create the file name, leveraging the fact that we've
                # established the last four characters are .pwb.
                out_name = os.path.join(
                    full_dir_path,
                    pf[0:-4] + '_pws_version_{}'.format(version) + '.pwb')

                # Save the case.
                saw.SaveCase(FileName=out_name, FileType=file_type, Overwrite=True)
                print('Saved new file, {}.'.format(out_name))


if __name__ == '__main__':
    # # Create argument parser and add our only argument.
    # parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     '--pwb_version',
    #     help='PowerWorld Simulator version to convert .pwb files to. At'
    #          'the time of writing, valid values are 5-20.',
    #     type=int, default=17)
    #
    # # Parse the arguments.
    # args_in = parser.parse_args()
    #
    # # Run.
    # main(args_in.pwb_version)
    main(20)

