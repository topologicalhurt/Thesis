#!/bin/bash
set -euo pipefail

# Function to process requirements for a specific directory
process_requirements() {
    local dir_path="$1"
    local requirements_path="$2"

    echo "Processing requirements for $dir_path"

    # Create cache file path based on directory
    local cache_file="$PWD/.github/hooks/pre_commit/.cache_$(basename "$dir_path").json"
    touch "$requirements_path" # Ensure the requirements file exists

    # Find all python files and process them
    find "$dir_path" -name "*.py" -type f | while read -r py_file; do
        # Get the list of modules to install from the python script
        local modules_to_install
        modules_to_install=$(python3 "$PWD/.github/hooks/pre_commit/get_imports.py" "$py_file" "$cache_file")

        # Parse the python list string into a bash array
        local parsed_modules
        parsed_modules=$(echo "$modules_to_install" | sed -e "s/^\[//" -e "s/\]$//" -e "s/'//g" -e "s/\"//g" | tr -d '[:space:]' | tr ',' ' ')

        if [ -z "$parsed_modules" ]; then
            continue
        fi

        # Iterate over the newly found modules
        for module in $parsed_modules; do
            # Check if the module is already in the requirements file to avoid re-processing
            if ! grep -q -E "^${module}(==|>=|>|<|<=)?" "$requirements_path"; then

                echo "Found new dependency: '${module}'. Installing..."

                # 1. Install the package into the active environment.
                pip3 install "$module"
                echo "Adding '${module}' to ${requirements_path}"

                # 2. Get the installed version from pip.
                local version
                version=$(pip3 show "$module" | grep 'Version:' | awk '{print $2}')

                # 3. Append the package and its version to the requirements file.
                if [ -n "$version" ]; then
                    echo "${module}==${version}" >> "$requirements_path"
                else
                    # Fallback if version detection fails for some reason
                    echo "${module}" >> "$requirements_path"
                fi

            fi
        done
    done

    # Sort the requirements file to keep it clean and prevent unnecessary diffs
    sort -o "$requirements_path" "$requirements_path"
    git add "$requirements_path"
}

cd ../../../
PWD=$(pwd)

# Activate the virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Process Allocator requirements
ALLOCATOR_PATH="$PWD/Src/Allocator"
ALLOCATOR_REQUIREMENTS_PATH="$ALLOCATOR_PATH/requirements.txt"
process_requirements "$ALLOCATOR_PATH" "$ALLOCATOR_REQUIREMENTS_PATH"

# Process Scripts requirements
SCRIPTS_PATH="$PWD/Src/Scripts"
SCRIPTS_REQUIREMENTS_PATH="$SCRIPTS_PATH/requirements.txt"
process_requirements "$SCRIPTS_PATH" "$SCRIPTS_REQUIREMENTS_PATH"

# Deactivate if we sourced it
if [ -d ".venv" ]; then
    deactivate
fi

echo "Requirements update complete."
