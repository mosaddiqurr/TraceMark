#!/bin/sh
set -eu

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
for bucket in originals protected temporary thumbnails benchmarks reports; do
  mc mb --ignore-existing "local/$bucket"
  mc anonymous set none "local/$bucket"
done
