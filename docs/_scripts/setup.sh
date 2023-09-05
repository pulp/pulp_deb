#!/usr/bin/env bash
set -e

export PULP_URL=${PULP_URL:-http://localhost:24817}

# Poll a Pulp task until it is finished.
wait_until_task_finished() {
    echo "Polling the task until it has reached a final state."
    local task_url=${1}
    while true
    do
        local response=$(http ${task_url})
        local state=$(echo ${response} | jq -r .state)
        case ${state} in
            failed|canceled)
                echo "Task in final state: ${state}"
                exit 1
                ;;
            completed)
                echo "${task_url} complete."
                break
                ;;
            *)
                echo "Still waiting..."
                sleep 1
                ;;
        esac
    done
}
