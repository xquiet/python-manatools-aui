#!/bin/bash
VER=5.3.3
BASE=https://cdn.jsdelivr.net/npm/bootstrap@${VER}/dist
VENDOR_DIR=manatools/aui/backends/web/static/vendor/bootstrap

mkdir -p "${VENDOR_DIR}"

curl -sL ${BASE}/css/bootstrap.min.css -o ${VENDOR_DIR}/bootstrap.min.css
if [ $? != 0 ]; then
    echo "Error downloading bootstrap CSS"
    exit 1
fi

curl -sL ${BASE}/js/bootstrap.bundle.min.js -o ${VENDOR_DIR}/bootstrap.bundle.min.js
if [ $? != 0 ]; then
    echo "Error downloading bootstrap JS bundle"
    exit 2
fi

echo "Bootstrap ${VER} assets downloaded to ${VENDOR_DIR}"
