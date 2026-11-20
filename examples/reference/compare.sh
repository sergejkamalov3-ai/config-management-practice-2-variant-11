#!/bin/sh
set -eu
cd "$(dirname "$0")"
for coord in junit:junit:4.13.2 org.hamcrest:hamcrest-library:1.3 org.hamcrest:hamcrest-core:1.3; do
    group=${coord%%:*}
    tail=${coord#*:}
    artifact=${tail%:*}
    release=${tail##*:}
    dest="../../build/reference/$artifact"
    mkdir -p "$dest"
    mvn -B -ntp "-Dgroup=$group" "-Dartifact=$artifact" "-Drelease=$release" \
        org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree \
        -Dscope=runtime -DoutputType=text "-DoutputFile=$dest/tree.txt"
    mvn -B -ntp "-Dgroup=$group" "-Dartifact=$artifact" "-Drelease=$release" \
        org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree \
        -Dscope=runtime -DoutputType=dot "-DoutputFile=$dest/tree.dot"
    dot -Tpng "$dest/tree.dot" -o "$dest/maven.png"
    cat "$dest/tree.txt"
done
