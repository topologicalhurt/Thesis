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

# Function to process requirements for a specific directory
process_requirements() {
    local dir_path="$1"
    local requirements_path="$2"

    echo "Processing requirements for $dir_path"

    # Create cache file path based on directory
    local cache_file="$PWD/.github/hooks/pre_commit/.cache_$(basename "$dir_path").json"

    # Track if any new packages were installed
    local new_packages_installed=false

    # Track if any new packages were installed
    local new_packages_installed=false

    # Create a temporary virtual environment
    temp_venv=$(mktemp -d)
    python3 -m venv "$temp_venv"
    source "$temp_venv/bin/activate"

    # Install only dependencies from Python files in the specific directory
    for py_file in $(find "$dir_path" -name "*.py" -type f); do
        # Extract imports and install them if they're not built-in modules
        # get_imports.py exits with code 1 if new packages were installed, 0 if all cached
        if python3 "$PWD/.github/hooks/pre_commit/get_imports.py" "$py_file" "$cache_file"; then
            # Exit code 0 means all packages were cached (no new installations)
            continue
        else
            # Exit code 1 means new packages were installed
            new_packages_installed=true
        fi
    done

    # Only update requirements file if new packages were installed
    if [ "$new_packages_installed" = true ]; then
        echo "New packages detected, updating requirements file..."

        # Generate requirements file with only external packages
        old_requirements=""
        if [ -f "$requirements_path" ]; then
            old_requirements=$(cat "$requirements_path")
        fi

        pip3 freeze | grep -v -E "^($(IFS='|'; echo "${BLACKLISTED[*]}"))" > "$requirements_path"

        diff=$(diff <(echo "$old_requirements") "$requirements_path")
        git add "$requirements_path"
        echo -e "Updated requirements for $dir_path:\n$(cat "$requirements_path")\nProducing diff: $diff\n"
    else
        echo "No new packages installed for $dir_path, requirements file unchanged."
    fi

    # Clean up temporary virtual environment
    deactivate
    rm -rf "$temp_venv"
}

# Process Allocator requirements
ALLOCATOR_PATH=$PWD/Src/Allocator
ALLOCATOR_REQUIREMENTS_PATH=$PWD/Src/Allocator/requirements.txt
process_requirements "$ALLOCATOR_PATH" "$ALLOCATOR_REQUIREMENTS_PATH"

# Process Scripts requirements
SCRIPTS_PATH=$PWD/Src/RTL/Scripts
SCRIPTS_REQUIREMENTS_PATH=$PWD/Src/RTL/Scripts/requirements.txt
process_requirements "$SCRIPTS_PATH" "$SCRIPTS_REQUIREMENTS_PATH"
