#!/usr/bin/env bash

set -ev

trap "rm frigg_1.0_ppc64.deb" EXIT

# user defined values
NAME=manual-upload-frigg-ppc64
DIST=pulp
COMP=upload

RELEASE_FILE_FIELDS=(
  codename=${DIST}
  suite=${DIST}
  version=1
  origin=myorigin
  label=mylabel
  description=mydescription
)

# download a package
wget https://fixtures.pulpproject.org/debian/pool/asgard/f/frigg/frigg_1.0_ppc64.deb

# create a repo and distribution
REPO_HREF=$(http ${PULP_URL}/pulp/api/v3/repositories/deb/apt/ name=${NAME} | jq -r .pulp_href)
TASK_HREF=$(http ${PULP_URL}/pulp/api/v3/distributions/deb/apt/ name=${NAME} base_path=${NAME} repository=${REPO_HREF} | jq -r .task)
wait_until_task_finished ${PULP_URL}${TASK_HREF}

# Create a Release, ReleaseArchitecture, and ReleaseComponent content to set various release file fields and add them to the repo in a single action
TASK_HREF=$(http ${PULP_URL}/pulp/api/v3/content/deb/releases/ repository=${REPO_HREF} distribution=${DIST} ${RELEASE_FILE_FIELDS[@]} architectures:='["amd64", "ppc64"]' components:=['"'${COMP}'"'] | jq -r .task)
wait_until_task_finished ${PULP_URL}${TASK_HREF}

# upload the package to create Package and PackageReleaseComponent content and add it to the repo in a single action
# the ReleaseComponent and ReleaseArchitecture were created in the previous step but could have been created in this step
TASK_HREF=$(http --form ${PULP_URL}/pulp/api/v3/content/deb/packages/ file@frigg_1.0_ppc64.deb repository=${REPO_HREF} distribution=${DIST} component=${COMP} | jq -r .task)
wait_until_task_finished ${PULP_URL}${TASK_HREF}

# publish our repo
TASK_HREF=$(http ${PULP_URL}/pulp/api/v3/publications/deb/apt/ repository=${REPO_HREF} | jq -r .task)
wait_until_task_finished ${PULP_URL}${TASK_HREF}

# check that our repo has one of the package index folders we would expect
http --check-status ${PULP_URL}/pulp/content/${NAME}/dists/${DIST}/${COMP}/binary-ppc64/Packages
