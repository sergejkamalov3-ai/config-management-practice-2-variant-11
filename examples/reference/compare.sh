#!/bin/sh
set -eu
cd "$(dirname "$0")"
dest_root="$(pwd)/../../build/reference"
mkdir -p "$dest_root"
cache=$(mktemp -d)
trap 'rm -rf "$cache"' EXIT
plugin=org.apache.maven.plugins:maven-dependency-plugin:3.8.1
mvn -version
for coord in junit:junit:4.13.2 org.hamcrest:hamcrest-library:1.3 org.hamcrest:hamcrest-core:1.3; do
    group=${coord%%:*}
    tail=${coord#*:}
    artifact=${tail%:*}
    release=${tail##*:}
    dest="$dest_root/$artifact"
    mkdir -p "$dest"
    run_mvn() {
        mvn -B "-Dmaven.repo.local=$cache/$artifact" \
            -Dmaven.artifact.threads=1 -Daether.connector.basic.threads=1 \
            "-Dgroup=$group" "-Dartifact=$artifact" "-Drelease=$release" "$@"
    }
    if ! run_mvn "$plugin:resolve" -DincludeScope=runtime >"$dest/resolve.log" 2>&1; then
        tail -40 "$dest/resolve.log"
        exit 1
    fi
    run_mvn -ntp "$plugin:tree" -Dscope=runtime -DoutputType=json "-DoutputFile=$dest/tree.json"
    run_mvn -ntp "$plugin:tree" -Dscope=runtime -DoutputType=dot "-DoutputFile=$dest/tree.dot"
    dot -Tpng "$dest/tree.dot" -o "$dest/maven.png"
    "${PYTHON:-python3}" verify.py "$coord" "$dest"
done
