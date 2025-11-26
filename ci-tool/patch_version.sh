#!/bin/bash

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <path> <old_version> <new_version>"
    exit 1
fi

path="$1"
old_version="$2"
new_version="$3"

find "$path" -type f \( -name "*.whl" -o -name "*.tar.gz" \) | while read archive; do
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

    if [[ "$archive" == *.whl ]]; then
        unzip -q "$archive" -d "$tmpdir"
    elif [[ "$archive" == *.tar.gz ]]; then
        tar -xzf "$archive" -C "$tmpdir"
    fi

    # Edit files inside
    find "$tmpdir" -type f | while read f; do
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

    # Repack
    outarchive="$dir/$fname"
    if [[ "$archive" == *.whl ]]; then
        # Remove old archive since we'll overwrite it
        rm -f "$archive"
        (cd "$tmpdir" && zip -r "$outarchive" .)
    elif [[ "$archive" == *.tar.gz ]]; then
        rm -f "$archive"
        (cd "$tmpdir" && tar -czf "$outarchive" .)
    fi

    rm -rf "$tmpdir"
done
