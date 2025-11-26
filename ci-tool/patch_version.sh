#!/bin/bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <path> <old_version> <new_version>"
    exit 1
fi

path="$1"
old_version="$2"
new_version="$3"

find "$path" -type f \( -name "*.whl" -o -name "*.tar.gz" \) | while read -r archive; do
    [[ -z "${archive:-}" ]] && continue

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
    elif [[ "$archive" == *.tar.gz ]]; then
        tar -xzf "$archive" -C "$tmpdir"
    fi

    # Patch directory names (deepest first)
    find "$tmpdir" -depth -type d | while read -r d; do
        [[ -z "${d:-}" ]] && continue
        dbase=$(basename "$d")
        newdbase="${dbase//$old_version/$new_version}"
        if [[ "$dbase" != "$newdbase" ]]; then
            dparent=$(dirname "$d")
            mv "$d" "$dparent/$newdbase"
        fi
    done

    # Edit files inside
    find "$tmpdir" -type f | while read -r f; do
        [[ -z "${f:-}" ]] && continue
        fdir=$(dirname "$f")
        fbase=$(basename "$f")
        newfbase="${fbase//$old_version/$new_version}"
        if [[ "$fbase" != "$newfbase" ]]; then
            mv "$f" "$fdir/$newfbase"
            f="$fdir/$newfbase"
        fi
        if file "$f" | grep -qE 'text|ASCII|Unicode'; then
            sed -i "s/$old_version/$new_version/g" "$f"
        fi
    done

    # Ensure output archive path and directory exists
    parent_dir=$(dirname "$archive")
    mkdir -p "$parent_dir"
    rm -f "$archive"

    if [[ "$archive" == *.whl ]]; then
        zip -rq "$archive" "$tmpdir"/*
    elif [[ "$archive" == *.tar.gz ]]; then
        tar -czf "$archive" -C "$tmpdir" .
    fi

    rm -rf "$tmpdir"
done