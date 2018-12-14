#!/usr/bin/env bash
set -veuo pipefail

if [ "$TRAVIS_PULL_REQUEST" = "false" ]
then
  PULP_PR_NUMBER=
  PULP_PLUGIN_PR_NUMBER=
else
  PR_MSG=$(http --json "https://api.github.com/repos/${TRAVIS_REPO_SLUG}/pulls/${TRAVIS_PULL_REQUEST}" "Accept:application/vnd.github.v3.text+json" | jq -r .body | tr -C "[:alnum:]-\n" =)
  echo $PR_MSG
  PULP_PR_NUMBER=$(echo $PR_MSG | sed -n 's/.*[Rr]equires.*pulp=pulp=[^0-9]*\([0-9]*\).*/\1/p')
  PULP_PLUGIN_PR_NUMBER=$(echo $PR_MSG | sed -n 's/.*[Rr]equires.*pulp=pulpcore-plugin=[^0-9]*\([0-9]*\).*/\1/p')
fi

pip install -r test_requirements.txt

pushd ..

git clone https://github.com/pulp/pulp.git
pushd pulp
if [ -n "$PULP_PR_NUMBER" ]; then
  echo "=== Using pulp PR #${PULP_PR_NUMBER} ==="
  git fetch origin +refs/pull/$PULP_PR_NUMBER/merge
  git checkout FETCH_HEAD
fi
pip install -e .
popd

git clone https://github.com/pulp/pulpcore-plugin.git
pushd pulpcore-plugin
if [ -n "$PULP_PLUGIN_PR_NUMBER" ]; then
  echo "=== Using pulpcore-plugin PR #${PULP_PLUGIN_PR_NUMBER} ==="
  git fetch origin +refs/pull/$PULP_PLUGIN_PR_NUMBER/merge
  git checkout FETCH_HEAD
fi
pip install -e .
popd

popd
pip install -e .
