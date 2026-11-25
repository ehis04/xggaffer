#!/bin/sh

set -eu

BASE_URL=${1:-https://xggaffer.site}
BASE_URL=${BASE_URL%/}
CURL=${CURL:-curl}

check_json_status() {
    path=$1
    expected=$2
    response=$($CURL --fail --silent --show-error \
        --connect-timeout 10 --max-time 30 "$BASE_URL$path")
    printf '%s' "$response" | grep -Eq \
        "\"status\"[[:space:]]*:[[:space:]]*\"$expected\""
    echo "PASS $path"
}

check_http() {
    path=$1
    $CURL --fail --silent --show-error --output /dev/null \
        --connect-timeout 10 --max-time 30 "$BASE_URL$path"
    echo "PASS $path"
}

echo "Smoke testing $BASE_URL"
check_json_status /health/live/ ok
check_json_status /health/ready/ ok
check_http /

echo "All deployment smoke tests passed."
