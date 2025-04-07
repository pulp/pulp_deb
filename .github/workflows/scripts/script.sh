#!/usr/bin/env bash
# coding=utf-8

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_deb' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

set -mveuo pipefail

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..

source .github/workflows/scripts/utils.sh

export POST_SCRIPT=$PWD/.github/workflows/scripts/post_script.sh
export FUNC_TEST_SCRIPT=$PWD/.github/workflows/scripts/func_test_script.sh

# Needed for starting the service
# Gets set in .github/settings.yml, but doesn't seem to inherited by
# this script.
export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
export PULP_SETTINGS=$PWD/.ci/ansible/settings/settings.py

export PULP_URL="https://pulp"

REPORTED_STATUS="$(pulp status)"

echo "${REPORTED_STATUS}"

echo "machine pulp
login admin
password password
" | cmd_user_stdin_prefix bash -c "cat >> ~pulp/.netrc"
# Some commands like ansible-galaxy specifically require 600
cmd_prefix bash -c "chmod 600 ~pulp/.netrc"

# Generate bindings
###################

echo "::group::Generate bindings"

touch bindings_requirements.txt
pushd ../pulp-openapi-generator
  # Use app_label to generate api.json and package to produce the proper package name.

  # Workaround: Domains are not supported by the published bindings.
  # Sadly: Different pulpcore-versions aren't either...
  # * In the 'pulp' scenario we use the published/prebuilt bindings, so we can test it.
  # * In other scenarios we generate new bindings from server spec, so we have a more
  #   reliable client.
  if [ "$TEST" = "pulp" ]
  then
    BUILT_CLIENTS=" deb "
  else
    BUILT_CLIENTS=""
  fi

  for ITEM in $(jq -r '.versions[] | tojson' <<<"${REPORTED_STATUS}")
  do
    COMPONENT="$(jq -r '.component' <<<"${ITEM}")"
    VERSION="$(jq -r '.version' <<<"${ITEM}" | python3 -c "from packaging.version import Version; print(Version(input()))")"
    # On older status endpoints, the module was not provided, but the package should be accurate
    # there, because we did not merge plugins into pulpcore back then.
    MODULE="$(jq -r '.module // (.package|gsub("-"; "_"))' <<<"${ITEM}")"
    PACKAGE="${MODULE%%.*}"
    cmd_prefix pulpcore-manager openapi --bindings --component "${COMPONENT}" > "${COMPONENT}-api.json"
    if [[ ! " ${BUILT_CLIENTS} " =~ "${COMPONENT}" ]]
    then
      rm -rf "./${PACKAGE}-client"
      ./gen-client.sh "${COMPONENT}-api.json" "${COMPONENT}" python "${PACKAGE}"
      pushd "${PACKAGE}-client"
        python setup.py sdist bdist_wheel --python-tag py3
      popd
    else
      if [ ! -f "${PACKAGE}-client/dist/${PACKAGE}_client-${VERSION}-py3-none-any.whl" ]
      then
        ls -lR "${PACKAGE}-client/"
        echo "Error: Client bindings for ${COMPONENT} not found."
        echo "File ${PACKAGE}-client/dist/${PACKAGE}_client-${VERSION}-py3-none-any.whl missing."
        exit 1
      fi
    fi
    echo "/root/pulp-openapi-generator/${PACKAGE}-client/dist/${PACKAGE}_client-${VERSION}-py3-none-any.whl" >> "../pulp_deb/bindings_requirements.txt"
  done
popd

echo "::endgroup::"

echo "::group::Debug bindings diffs"

# Bindings diff for deb
jq '(.paths[][].parameters|select(.)) |= sort_by(.name)' < "deb-api.json" > "build-api.json"
jq '(.paths[][].parameters|select(.)) |= sort_by(.name)' < "../pulp-openapi-generator/deb-api.json" > "test-api.json"
jsondiff --indent 2 build-api.json test-api.json || true
echo "::endgroup::"

# Install test requirements
###########################

# Carry on previous constraints (there might be no such file).
cat *_constraints.txt > bindings_constraints.txt || true
cat .ci/assets/ci_constraints.txt >> bindings_constraints.txt
# Add a safeguard to make sure the proper versions of the clients are installed.
echo "$REPORTED_STATUS" | jq -r '.versions[]|select(.package)|(.package|sub("_"; "-")) + "-client==" + .version' >> bindings_constraints.txt
cmd_stdin_prefix bash -c "cat > /tmp/unittest_requirements.txt" < unittest_requirements.txt
cmd_stdin_prefix bash -c "cat > /tmp/functest_requirements.txt" < functest_requirements.txt
cmd_stdin_prefix bash -c "cat > /tmp/bindings_requirements.txt" < bindings_requirements.txt
cmd_stdin_prefix bash -c "cat > /tmp/bindings_constraints.txt" < bindings_constraints.txt
cmd_prefix pip3 install -r /tmp/unittest_requirements.txt -r /tmp/functest_requirements.txt -r /tmp/bindings_requirements.txt -c /tmp/bindings_constraints.txt

CERTIFI=$(cmd_prefix python3 -c 'import certifi; print(certifi.where())')
cmd_prefix bash -c "cat /etc/pulp/certs/pulp_webserver.crt >> '$CERTIFI'"

# check for any uncommitted migrations
echo "Checking for uncommitted migrations..."
cmd_user_prefix bash -c "django-admin makemigrations deb --check --dry-run"

# Run unit tests.
cmd_user_prefix bash -c "PULP_DATABASES__default__USER=postgres pytest -v -r sx --color=yes --suppress-no-test-exit-code -p no:pulpcore --pyargs pulp_deb.tests.unit"
# Run functional tests
if [[ "$TEST" == "performance" ]]; then
  if [[ -z ${PERFORMANCE_TEST+x} ]]; then
    cmd_user_prefix bash -c "pytest -vv -r sx --color=yes --suppress-no-test-exit-code --capture=no --durations=0 --pyargs pulp_deb.tests.performance"
  else
    cmd_user_prefix bash -c "pytest -vv -r sx --color=yes --suppress-no-test-exit-code --capture=no --durations=0 --pyargs pulp_deb.tests.performance.test_${PERFORMANCE_TEST}"
  fi
  exit
fi

if [ -f "$FUNC_TEST_SCRIPT" ]; then
  source "$FUNC_TEST_SCRIPT"
else
  if [[ "$GITHUB_WORKFLOW" =~ "Nightly" ]]
  then
    cmd_user_prefix bash -c "pytest -v --timeout=300 -r sx --color=yes --suppress-no-test-exit-code --pyargs pulp_deb.tests.functional -m parallel -n 8 --nightly"
    cmd_user_prefix bash -c "pytest -v --timeout=300 -r sx --color=yes --suppress-no-test-exit-code --pyargs pulp_deb.tests.functional -m 'not parallel' --nightly"
  else
    cmd_user_prefix bash -c "pytest -v --timeout=300 -r sx --color=yes --suppress-no-test-exit-code --pyargs pulp_deb.tests.functional -m parallel -n 8"
    cmd_user_prefix bash -c "pytest -v --timeout=300 -r sx --color=yes --suppress-no-test-exit-code --pyargs pulp_deb.tests.functional -m 'not parallel'"
  fi
fi
export PULP_FIXTURES_URL="http://pulp-fixtures:8080"
pushd ../pulp-cli-deb
pip install -r test_requirements.txt
pytest -v -m "pulp_deb"
popd

if [ -f "$POST_SCRIPT" ]; then
  source "$POST_SCRIPT"
fi
