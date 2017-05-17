# Originally pulp_rpm.yum_plugin.util, but needed here in order to remove the
# dependency on pulp_rpm

import os
import shutil
import uuid


LISTING_FILE_NAME = 'listing'


def generate_listing_files(root_publish_dir, repo_publish_dir):
    """
    (Re) Generate listing files along the path from the repo publish dir to the
    root publish dir.

    :param root_publish_dir: root directory
    :type  root_publish_dir: str
    :param repo_publish_dir: the repository's publish directory, as a descendant of the root
    directory
    :type  repo_publish_dir: str
    """
    # normalize the paths for use with os.path.dirname by removing any trailing '/'s
    root_publish_dir = root_publish_dir.rstrip('/')
    repo_publish_dir = repo_publish_dir.rstrip('/')

    # the repo_publish_dir *must* be a descendant of the root_publish_dir
    if not repo_publish_dir.startswith(root_publish_dir):
        raise ValueError(
            'repository publish directory must be a descendant of the root publish directory')

    # this is a weird case that handles a distinct difference between actual
    # Pulp behavior and the way unit tests against publish have been written
    if root_publish_dir == repo_publish_dir:
        working_dir = repo_publish_dir
    else:
        # start at the parent of the repo publish dir and work up to the publish dir
        working_dir = os.path.dirname(repo_publish_dir)

    while True:
        listing_file_path = os.path.join(working_dir, LISTING_FILE_NAME)
        tmp_file_path = os.path.join(working_dir, '.%s' % uuid.uuid4())

        directories = [d for d in os.listdir(working_dir) if
                       os.path.isdir(os.path.join(working_dir, d))]
        directories.sort()

        # write the new listing file
        with open(tmp_file_path, 'w') as listing_handle:
            listing_handle.write('\n'.join(directories))

        # move it into place, over-writing any pre-existing listing file
        shutil.move(tmp_file_path, listing_file_path)

        if working_dir == root_publish_dir:
            break

        # work up the directory structure
        working_dir = os.path.dirname(working_dir)
