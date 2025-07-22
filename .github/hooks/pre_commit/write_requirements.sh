#!/bin/bash
set -eo pipefail

# Function to process requirements for a specific directory
process_requirements() {
    local dir_path="$1"
    local requirements_path="$2"

    echo "Processing requirements for $dir_path"

    # Create cache file path based on directory
    local cache_file="$ROOT/.github/hooks/pre_commit/.cache_$(basename "$dir_path").json"
    touch "$requirements_path" # Ensure the requirements file exists

    find "$dir_path" -name "*.py" -type f | while read -r py_file; do
        local modules_to_install
        modules_to_install=$(python3 "$ROOT/.github/hooks/pre_commit/get_imports.py" "$py_file" "$cache_file")
        local parsed_modules
        parsed_modules=$(echo "$modules_to_install" | sed -e "s/^\[//" -e "s/\]$//" -e "s/'//g" -e "s/\"//g" | tr -d '[:space:]' | tr ',' ' ')

        if [ -z "$parsed_modules" ]; then
            continue
        fi

        for module in $parsed_modules; do

            # Check if the module is already in the requirements file to avoid re-processing
            if ! grep -q -E "^${module}(==|>=|>|<|<=)?" "$requirements_path"; then

                echo "Found new dependency: '${module}'. Installing..."

                pip3 install "$module"
                echo "Adding '${module}' to ${requirements_path}"

                local version
                version=$(pip3 show "$module" | grep 'Version:' | awk '{print $2}')

                # Append the package and its version to the requirements file.
                if [ -n "$version" ]; then
                    echo "${module}==${version}" >> "$requirements_path"
                else
                    echo "${module}" >> "$requirements_path"
                fi

            fi
        done
    done

    # Sort the requirements file to keep it clean and prevent unnecessary diffs
    sort -o "$requirements_path" "$requirements_path"
    git add "$requirements_path"
}

[ "$CUR_BRANCH" == "research" ] || {
    source "$VENV_DIR/bin/activate"

    # Process Allocator requirements
    ALLOCATOR_PATH="$ROOT/Src/Allocator"
    ALLOCATOR_REQUIREMENTS_PATH="$ALLOCATOR_PATH/requirements.txt"
    process_requirements "$ALLOCATOR_PATH" "$ALLOCATOR_REQUIREMENTS_PATH"

    # Process Scripts requirements
    SCRIPTS_PATH="$ROOT/Src/Scripts"
    SCRIPTS_REQUIREMENTS_PATH="$SCRIPTS_PATH/requirements.txt"
    process_requirements "$SCRIPTS_PATH" "$SCRIPTS_REQUIREMENTS_PATH"

    deactivate
}
