#!/bin/sh

set -euv

if [ "$TEST" = "pulp" ] || [ "$TEST" = "performance" ]
then
  # Aliases for running commands in the pulp-worker container.
  PULP_WORKER_PODS="$(sudo kubectl get pods | grep -E -o "pulp-worker-(\w+)-(\w+)")"

  for POD in $PULP_WORKER_PODS
  do
    CMD_WORKER_PREFIX="sudo kubectl exec -i $POD -- "
    $CMD_WORKER_PREFIX bash -c "cat > /root/sign_deb_release.sh" < "$TRAVIS_BUILD_DIR"/pulp_deb/tests/functional/sign_deb_release.sh
    $CMD_WORKER_PREFIX bash -c "cat > /tmp/setup_signing_service.py" < "$TRAVIS_BUILD_DIR"/pulp_deb/tests/functional/setup_signing_service.py

    curl -L https://github.com/pulp/pulp-fixtures/raw/master/common/GPG-PRIVATE-KEY-pulp-qe | $CMD_WORKER_PREFIX gpg --import
    echo "6EDF301256480B9B801EBA3D05A5E6DA269D9D98:6:" | $CMD_WORKER_PREFIX gpg --import-ownertrust
    $CMD_WORKER_PREFIX chmod a+x /tmp/setup_signing_service.py /root/sign_deb_release.sh
  done
  $CMD_WORKER_PREFIX /tmp/setup_signing_service.py /root/sign_deb_release.sh
fi
