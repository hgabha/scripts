
def get_filename_from_url(url):
    """Extract filename from URL, removing query parameters"""
    # Parse the URL and get the path
    path = urlparse(url).path
    # Get the last part of the path (filename)
    filename = os.path.basename(path)
    return filename

def download_files(urls_array, base_path, hf_token):
    """Download files from URLs array using wget if they don't already exist"""
    # Get number of URLs
    num_urls = len(urls_array)
    print(f"Found {num_urls} URLs to download")
    #print(f"Using base path: {base_path}")

    for idx, entry in enumerate(urls_array, 1):
        url = entry["url"]
        # Combine base_path with directory from array
        directory = os.path.join(base_path, entry["directory"].lstrip('/'))
        provided_filename = entry["filename"]

        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        # Determine filename
        if provided_filename:
            filename = provided_filename
        else:
            filename = get_filename_from_url(url)

        # Construct full path
        full_path = os.path.join(directory, filename)

        #print(f"\nDownloading {idx} of {num_urls}")

        # Check if file already exists
        if os.path.exists(full_path):
            print(f"File already exists: {full_path}")
            print("Skipping download...")
            continue

        print(f"Downloading: {filename}")

        try:
          if hf_token == True :
              # Use wget with simplified progress output
              subprocess.run([
                  "wget",
                  "--header", f"Authorization: Bearer {TOKEN}",
                  "-O", full_path,    # Output file
                  url,                # URL to download
                  "--quiet",          # Suppress wget's output
                  "--show-progress",  # Show progress bar
                  "--progress=bar:force:noscroll"  # Simple progress bar format
              ], check=True)
              print(f"Successfully downloaded: {filename}")

          else:
              # Use wget with simplified progress output
              subprocess.run([
                  "wget",
                  "-O", full_path,    # Output file
                  url,                # URL to download
                  "--quiet",          # Suppress wget's output
                  "--show-progress",  # Show progress bar
                  "--progress=bar:force:noscroll"  # Simple progress bar format
              ], check=True)
              print(f"Successfully downloaded: {filename}")

        except subprocess.CalledProcessError as e:
            print(f"Error downloading {url}: {e}")
        except Exception as e:
            print(f"Unexpected error with {url}: {e}")

def delete_files(urls_array, base_path):
    # Get number of array entries
    num_urls = len(urls_array)
    print(f"Found {num_urls} files to delete")
    #print(f"Using base path: {base_path}")

    for idx, entry in enumerate(urls_array, 1):
        url = entry["url"]
        # Construct full directory path from base_path and folder name
        directory = os.path.join(base_path, entry["directory"])
        provided_filename = entry["filename"]


        # Determine filename
        if provided_filename:
            filename = provided_filename
        else:
            filename = get_filename_from_url(url)

        # Construct full path
        full_path = os.path.join(directory, filename)

        print(f"\nAttempting to delete file {idx} of {num_urls}")

        # Check if file already exists
        if os.path.exists(full_path):
            print(f"Found file {full_path}...deleted!")
            os.remove(full_path)
        else:
            print("Skipping file {full_path}...not found!")
            continue
