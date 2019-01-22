#!/bin/sh

set -eux

SRCDIR=$(readlink -f $(dirname $0))
TMPDIR=$(mktemp -d)

trap "rm -rf $TMPDIR" exit

cd $TMPDIR

mkdir asgard
cd asgard

for CTL in ${SRCDIR}/asgard/*.ctl
do
  equivs-build --arch ppc64 ${CTL}
done
cd ..

mkdir jotunheimr
cd jotunheimr

for CTL in ${SRCDIR}/jotunheimr/*.ctl
do
  equivs-build --arch armeb ${CTL}
done
cd ..

cp -a ${SRCDIR}/conf .
reprepro -C asgard includedeb ragnarok asgard/*.deb
reprepro -C jotunheimr includedeb ragnarok jotunheimr/*.deb

rm dists/ragnarok/jotunheimr/binary-armeb/Packages

tar cvzf ${SRCDIR}/fixtures.tar.gz dists pool
