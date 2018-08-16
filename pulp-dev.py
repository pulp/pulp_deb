#!/usr/bin/env python2

import optparse
import os
import pip
import re
import sys

from pulp.devel import environment


# It is important for longer operators to come before shorter operators when
# there is overlap
RPMCMPOPS = ["<=", "<", ">=", ">", "="]
RPMCMPSEP = re.compile("(%s)" % '|'.join(RPMCMPOPS))


# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
# Please keep alphabetized and by subproject

# Standard directories
DIR_PLUGINS = '/usr/lib/pulp/plugins'

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

DIRS = (
    '/var/lib/pulp/published/deb/web',
    '/var/lib/pulp/published/deb/http',
    '/var/lib/pulp/published/deb/https',
)

LINKS = (
    ('plugins/etc/httpd/conf.d/pulp_deb.conf', '/etc/httpd/conf.d/pulp_deb.conf'),
    ('plugins/etc/pulp/server/plugins.conf.d/deb_distributor.json',
     '/etc/pulp/server/plugins.conf.d/deb_distributor.json'),
    ('plugins/etc/pulp/server/plugins.conf.d/deb_importer.json',
     '/etc/pulp/server/plugins.conf.d/deb_importer.json'),
)

PIP_INSTALLABLE = []


def parse_cmdline():
    """
    Parse and validate the command line options.
    """
    parser = optparse.OptionParser()

    parser.add_option('-I', '--install',
                      action='store_true',
                      help='install pulp development files')
    parser.add_option('-U', '--uninstall',
                      action='store_true',
                      help='uninstall pulp development files')
    parser.add_option('-D', '--debug',
                      action='store_true',
                      help=optparse.SUPPRESS_HELP)

    parser.set_defaults(install=False,
                        uninstall=False,
                        debug=True)

    opts, args = parser.parse_args()

    if opts.install and opts.uninstall:
        parser.error('both install and uninstall specified')

    if not (opts.install or opts.uninstall):
        parser.error('neither install or uninstall specified')

    return (opts, args)


def create_dirs(opts):
    for d in DIRS:
        if os.path.exists(d) and os.path.isdir(d):
            environment.debug(opts, 'skipping %s exists' % d)
            continue
        environment.debug(opts, 'creating directory: %s' % d)
        os.makedirs(d, 0o777)
    os.system('chown -R apache:apache /var/lib/pulp/published')


def getlinks():
    links = []
    for l in LINKS:
        if isinstance(l, (list, tuple)):
            src = l[0]
            dst = l[1]
        else:
            src = l
            dst = os.path.join('/', l)
        links.append((src, dst))
    return links


def install(opts):
    # Install the packages in developer mode
    pip.main(["install", "setuptools>=19.0"])
    pip.main(["install"] + PIP_INSTALLABLE)
    environment.manage_setup_pys('install', ROOT_DIR)

    warnings = []
    create_dirs(opts)
    currdir = os.path.abspath(os.path.dirname(__file__))
    for src, dst in getlinks():
        warning_msg = create_link(opts, os.path.join(currdir, src), dst)
        if warning_msg:
            warnings.append(warning_msg)

    if warnings:
        print("\n***\nPossible problems:  Please read below\n***")
        for w in warnings:
            environment.warning(w)
    return os.EX_OK


def uninstall(opts):
    for src, dst in getlinks():
        environment.debug(opts, 'removing link: %s' % dst)
        if not os.path.islink(dst):
            environment.debug(opts, '%s does not exist, skipping' % dst)
            continue
        os.unlink(dst)

    # Uninstall the packages
    environment.manage_setup_pys('uninstall', ROOT_DIR)

    return os.EX_OK


def create_link(opts, src, dst):
    if not os.path.lexists(dst):
        return _create_link(opts, src, dst)

    if not os.path.islink(dst):
        return ("[%s] is not a symbolic link as we expected, please adjust if this is not what "
                "you intended." % (dst))

    if not os.path.exists(os.readlink(dst)):
        environment.warning(
            'BROKEN LINK: [%s] attempting to delete and fix it to point to %s.' % (dst, src))
        try:
            os.unlink(dst)
            return _create_link(opts, src, dst)
        except Exception:
            msg = ("[%s] was a broken symlink, failed to delete and relink to [%s], please fix "
                   "this manually" % (dst, src))
            return msg

    environment.debug(opts, 'verifying link: %s points to %s' % (dst, src))
    dst_stat = os.stat(dst)
    src_stat = os.stat(src)
    if dst_stat.st_ino != src_stat.st_ino:
        msg = ("[%s] is pointing to [%s] which is different than the intended target "
               "[%s]" % (dst, os.readlink(dst), src))
        return msg


def _create_link(opts, src, dst):
        environment.debug(opts, 'creating link: %s pointing to %s' % (dst, src))
        try:
            os.symlink(src, dst)
        except OSError as e:
            msg = ("Unable to create symlink for [%s] pointing to [%s], received error: "
                   "<%s>" % (dst, src, e))
            return msg


if __name__ == '__main__':
    # TODO add something to check for permissions
    opts, args = parse_cmdline()
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
