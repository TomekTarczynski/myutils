import os

def print_tree_structure(directory, omit_dirs=[".venv", ".pytest_cache", "__pycache__"], prefix=""):
    """Prints the tree structure of files and directories in the specified format."""

    # Get the list of files and directories
    entries = [entry for entry in os.listdir(directory) if entry not in omit_dirs]
    entries.sort()  # Sort to print in a consistent order (directories first)
    
    # Get total count of entries
    total_entries = len(entries)
    
    # Loop through entries and print in the desired tree format
    for index, entry in enumerate(entries):
        path = os.path.join(directory, entry)
        connector = "└── " if index == total_entries - 1 else "├── "

        if os.path.isdir(path):
            print(f"{prefix}{connector}{entry}/")
            # Continue to print the contents of the subdirectory with updated prefix
            new_prefix = f"{prefix}    " if index == total_entries - 1 else f"{prefix}│   "
            print_tree_structure(path, omit_dirs, new_prefix)
        else:
            print(f"{prefix}{connector}{entry}")

def print_file_contents(directory, omit_dirs=[".venv", ".pytest_cache", "__pycache__"] , max_file_length=None):
    """Prints the content of each file, skipping files larger than max_file_length."""

    for root, dirs, files in os.walk(directory):
        # Remove any directories that should be omitted
        dirs[:] = [d for d in dirs if d not in omit_dirs]
        
        # Print files and their content relative to the main directory
        for file_name in files:
            file_path = os.path.join(root, file_name)
            print(f"File: {os.path.relpath(file_path, directory)}")
            
            # Check if file size exceeds the maximum allowed file length
            try:
                file_size = os.path.getsize(file_path)
                if max_file_length is not None and file_size > max_file_length:
                    print(f"--- Skipping content of {file_name} (file size: {file_size} bytes, exceeds {max_file_length} bytes) ---\n")
                    continue  # Skip printing file content if it's too large
                
                # Print file content if size is within the limit
                with open(file_path, 'r', encoding='utf-8') as file:
                    print(f"--- Content of {file_name} ---")
                    print(file.read())  # Print file content
                    print(f"--- End of {file_name} ---\n")
            except Exception as e:
                print(f"Could not read {file_name}: {e}")