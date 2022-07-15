#!/usr/bin/env bash

export BASE_ADDR=https://pulp:443
export CONTENT_ADDR=https://pulp:443/pulp/content

cd docs/_scripts/
source setup.sh
source structured_repo.sh
