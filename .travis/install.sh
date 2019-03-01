#!/usr/bin/env bash
set -veuo pipefail

PULPCORE_PR_NUMBER=
PULPCORE_PLUGIN_PR_NUMBER=
if [ -f DONOTMERGE.requirements ]
then
  source DONOTMERGE.requirements
fi

pip install -r test_requirements.txt

pushd ..

git clone https://github.com/pulp/pulpcore.git
pushd pulpcore
if [ -n "$PULPCORE_PR_NUMBER" ]; then
  echo "=== Using pulpcore PR #${PULPCORE_PR_NUMBER} ==="
  git fetch origin +refs/pull/$PULPCORE_PR_NUMBER/merge
  git checkout FETCH_HEAD
fi
pip install -e .
popd

git clone https://github.com/pulp/pulpcore-plugin.git
pushd pulpcore-plugin
if [ -n "$PULPCORE_PLUGIN_PR_NUMBER" ]; then
  echo "=== Using pulpcore-plugin PR #${PULPCORE_PLUGIN_PR_NUMBER} ==="
  git fetch origin +refs/pull/$PULPCORE_PLUGIN_PR_NUMBER/merge
  git checkout FETCH_HEAD
fi
pip install -e .
popd

popd
pip install -e .
