#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <source-dir> <release-root> <revision>" >&2
  exit 2
}

[[ $# -eq 3 ]] || usage

source_dir=$(readlink -f "$1")
release_root=$(readlink -m "$2")
revision="$3"

[[ -f "$source_dir/Snakefile" ]] || { echo "Missing Snakefile under $source_dir" >&2; exit 1; }
[[ "$revision" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Unsafe revision: $revision" >&2; exit 1; }

releases_dir="$release_root/releases"
release_dir="$releases_dir/$revision"
current_link="$release_root/current"

mkdir -p "$releases_dir"
if [[ -e "$release_dir" ]]; then
  echo "Release already exists: $release_dir" >&2
  exit 1
fi

staging_dir="$releases_dir/.${revision}.staging.$$"
trap 'rm -rf -- "$staging_dir"' EXIT
mkdir -p "$staging_dir"
cp -a "$source_dir/." "$staging_dir/"

(
  cd "$staging_dir"
  find . -type f ! -name SHA256SUMS -print0 \
    | sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)

mv "$staging_dir" "$release_dir"
ln -sfn "releases/$revision" "$current_link.next"
mv -Tf "$current_link.next" "$current_link"
trap - EXIT

echo "Deployed PGT-A S9 release: $release_dir"
echo "Current: $(readlink "$current_link")"
