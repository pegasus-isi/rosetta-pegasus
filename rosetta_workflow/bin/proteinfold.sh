#!/bin/bash

set -e 

inputs="$@"

file=$1

flags=$(echo $inputs | sed 's/data-\([0-9]\{1,4\}\) //g')

tar -xf "$file.tar.gz"

rm "$file.tar.gz"

cp -r "$file"/* .

rm -r "$file"

chmod +x ./AbinitioRelax.static.linuxgccrelease

tar -xzf database.tar.gz

rm database.tar.gz

./AbinitioRelax.static.linuxgccrelease $flags
