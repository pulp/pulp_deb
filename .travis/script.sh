#!/usr/bin/env bash
# coding=utf-8
set -veuo pipefail

# Lint code.
flake8 --config flake8.cfg

# Run migrations.
export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
export PULP_CONTENT_HOST=localhost:8080
django-admin makemigrations deb
django-admin migrate --noinput

# Run unit tests.
(cd ../pulpcore && coverage run manage.py test pulp_deb.tests.unit)

# Run functional tests.
django-admin reset-admin-password --password admin
django-admin runserver >> ~/django_runserver.log 2>&1 &
gunicorn pulpcore.content:server --bind 'localhost:8080' --worker-class 'aiohttp.GunicornWebWorker' -w 2 >> ~/content_app.log 2>&1 &
rq worker -n 'resource-manager@%h' -w 'pulpcore.tasking.worker.PulpWorker' >> ~/resource_manager.log 2>&1 &
rq worker -n 'reserved-resource-worker-1@%h' -w 'pulpcore.tasking.worker.PulpWorker' >> ~/reserved_worker-1.log 2>&1 &
sleep 8

show_logs_and_return_non_zero() {
    readonly local rc="$?"
    cat ~/django_runserver.log
    cat ~/content_app.log
    cat ~/resource_manager.log
    cat ~/'reserved_worker-1.log'
    return "${rc}"
}
pytest -v -r sx --color=yes --pyargs pulp_deb.tests.functional || show_logs_and_return_non_zero
