#!/bin/bash

BLACKLISTED=('pre_commit')

for excl in "${BLACKLISTED[@]}"; do
    dependencies=$(pip show $excl | grep "^Requires" | sed 's/^Requires: //' | tr ',' ' ')
    for dep in $dependencies; do
    BLACKLISTED+=("$dep")
    done
done

cd ../../../ || exit 1
PWD=`pwd`

REQUIREMENTS_PATH=$PWD/Src/Allocator/Interpreter/requirements.txt
source .venv/bin/activate
old_requirements=$(cat $REQUIREMENTS_PATH)
pip3 freeze | grep -v -E "^($(IFS='|'; echo "${BLACKLISTED[*]}"))" > $REQUIREMENTS_PATH
diff=$(diff <(echo "$old_requirements") $REQUIREMENTS_PATH)
git add $REQUIREMENTS_PATH
echo -e "Updated requirements:\n $(cat $REQUIREMENTS_PATH) \n producing diff $diff"
