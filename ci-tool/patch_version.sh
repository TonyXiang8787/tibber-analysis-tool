#!/bin/bash
# Exit immediately on error, treat unset variables as an error, and fail if any command in a pipeline fails
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <path> <old_version> <new_version>"
    exit 1
fi

path="$1"
old_version="$2"
new_version="$3"

find "$path" -type f \( -name "*.whl" -o -name "*.tar.gz" \) | while read -r archive; do
    dir=$(dirname "$archive")
    fname=$(basename "$archive")

    # Rename archive file if necessary
    newfname="${fname//$old_version/$new_version}"
    if [[ "$fname" != "$newfname" ]]; then
        mv "$archive" "$dir/$newfname"
        archive="$dir/$newfname"
        fname="$newfname"
    fi

    tmpdir=$(mktemp -d)

    # Unpack archive
    if [[ "$archive" == *.whl ]]; then
        unzip -q "$archive" -d "$tmpdir"
    elif [[ "$archive" == *.tar.gz" ]]; then
        tar -xzf "$archive" -C "$tmpdir"
    fi

    # Edit files inside
    find "$tmpdir" -type f | while read -r f; do
        fdir=$(dirname "$f")
        fbase=$(basename "$f")
        # Rename files with old_version in name
        newfbase="${fbase//$old_version/$new_version}"
        if [[ "$fbase" != "$newfbase" ]]; then
            mv "$f" "$fdir/$newfbase"
            f="$fdir/$newfbase"
        fi
        # Substitute contents if text
        if file "$f" | grep -qE 'text|ASCII|Unicode'; then
            sed -i "s/$old_version/$new_version/g" "$f"
        fi
    done

    # Prepare to re-pack archive at its original location
    parent_dir=$(dirname "$archive")
    mkdir -p "$parent_dir"
    rm -f "$archive"

    if [[ "$archive" == *.whl ]]; then
        (cd "$tmpdir" && zip -r "$archive" .)
    elif [[ "$archive" == *.tar.gz" ]]; then
        (cd "$tmpdir" && tar -czf "$archive" .)
    fi

    rm -rf "$tmpdir"
done