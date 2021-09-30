set -euv

if [ "$TEST" = "pulp" ] || [ "$TEST" = "performance" ] || [ "$TEST" = "azure" ] || [ "$TEST" = "s3" ]
then
  # Add signing service script and setup script:
  cmd_stdin_prefix bash -c "cat > /root/sign_deb_release.sh" < pulp_deb/tests/functional/sign_deb_release.sh
  cmd_stdin_prefix bash -c "cat > /tmp/setup_signing_service.py" < pulp_deb/tests/functional/setup_signing_service.py
  curl -L https://github.com/pulp/pulp-fixtures/raw/master/common/GPG-KEY-pulp-qe | cmd_stdin_prefix bash -c "cat > /tmp/GPG-KEY-pulp-qe"

  # Add private pulp-qe test key and set ownertrust:
  curl -L https://github.com/pulp/pulp-fixtures/raw/master/common/GPG-PRIVATE-KEY-pulp-qe | cmd_stdin_prefix gpg --import
  echo "6EDF301256480B9B801EBA3D05A5E6DA269D9D98:6:" | cmd_stdin_prefix gpg --import-ownertrust

  # Create the signing service:
  cmd_prefix chmod a+x /tmp/setup_signing_service.py /root/sign_deb_release.sh
  cmd_prefix /tmp/setup_signing_service.py /root/sign_deb_release.sh /tmp/GPG-KEY-pulp-qe
fi
