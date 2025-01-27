import ipywidgets as widgets
from IPython.display import display
import subprocess
from urllib.parse import urlparse
import os # Add this line to import the os module

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
          if hf_token == '' :
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
          else:
              # Use wget with simplified progress output
              subprocess.run([
                  "wget",
                  "--header", f"Authorization: Bearer {hf_token}",
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
    #print(f"Found {num_urls} files to delete")
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
            print(f"Skipping file {full_path}...not found!")
            continue

def upload_handler(folder):
    # Get the list of folder names in /usr, sorted alphabetically
    folder_names = sorted([f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))])

    # Create the dropdown widget
    dropdown = widgets.Dropdown(
        options=folder_names,
        value=folder_names[0] if folder_names else None,  # Set initial value to the first folder
        description='Folders in /usr:',
        disabled=False,
    )

    # Create the text input widget for the URL
    url_input = widgets.Text(
        value='',
        placeholder='Enter URL',
        description='URL:',
        disabled=False
    )
    # Display the widgets. Create a button to submit the form (optional)
    display(dropdown)
    display(url_input)
    submit_button = widgets.Button(description="Submit")
    submit_button.on_click(handle_submit)
    display(submit_button)

# Function to handle the button click (you can replace this with your desired action)
def handle_submit(sender):
    url = url_input.value
    
    # Check if the URL starts with "https://huggingface" and doesn't already have "?download=true"
    if url.startswith("https://huggingface") and "?download=true" not in url:  
        url += "?download=true"  # Append the suffix

    CUSTOM_URL = [
    {
        "url": url_input.value,
        "directory": dropdown.value,
        "filename": ""
    }
    ]
    print(f"Selected folder: {dropdown.value}")
    print(f"Entered URL: {url_input.value}")
    #print(f"Selected folder: {CUSTOM_URL[0][url]")
    #print(f"Entered URL: {CUSTOM_URL[0][.]directory]")
    download_files(CUSTOM_URL, BASE_PATH,'')


# List of URLS
SD_URLS = [
    {
        "url": "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned.safetensors?download=true",
        "directory": "checkpoints",
        "filename": ""
    },
    {
        "url": "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/vae/diffusion_pytorch_model.safetensors?download=true",
        "directory": "vae",
        "filename": "v1-5-vae.safetensors"
    }
]
JUGGER15 = [
    {
        "url": "https://huggingface.co/KamCastle/jugg/resolve/main/juggernaut_reborn.safetensors",
        "directory": "checkpoints",
        "filename": ""
    }
]
SDXL_URLS = [
    {
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors?download=true",
        "directory": "checkpoints", "filename": ""
    },
    {
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors?download=true",
        "directory": "checkpoints", "filename": ""
    },
    {
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/vae/diffusion_pytorch_model.safetensors?download=true",
        "directory": "vae", "filename": "sd_xl_VAE.safetensors"
    }
]
#juggernaut Rundiffusion Lightning and SDXL model
JUGGERSDXL = [
    {
        "url": "https://huggingface.co/RunDiffusion/Juggernaut-XL-Lightning/resolve/main/Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors",
        "directory": "checkpoints", "filename": ""
    },
    {
        "url": "    https://huggingface.co/RunDiffusion/Juggernaut-XL-v9/resolve/main/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
        "directory": "checkpoints", "filename": ""
    }
]

OG_SUPIR = [
    {
        "url": "https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0F.ckpt?download=true",
        "directory": "checkpoints", "filename": ""
    },
    {
        "url": "https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0Q.ckpt?download=true",
        "directory": "checkpoints", "filename": ""
    }
]
KIJAI_SUPIR = [
    {
        "url": "https://huggingface.co/Kijai/SUPIR_pruned/resolve/main/SUPIR-v0F_fp16.safetensors?download=true",
        "directory": "checkpoints", "filename": "Kijai_SUPIR-V0F_fp16.safetensors"
    },
    {
        "url": "https://huggingface.co/Kijai/SUPIR_pruned/resolve/main/SUPIR-v0Q_fp16.safetensors?download=true",
        "directory": "checkpoints", "filename": "Kijai_SUPIR-V0Q_fp16.safetensors"
    }
]
AURASR = [
    {
        "url": "https://huggingface.co/fal/AuraSR/resolve/main/model.safetensors?download=true",
        "directory": "Aura-SR", "filename": ""
    },
    {
        "url": "https://huggingface.co/fal/AuraSR/resolve/main/config.json?download=true",
        "directory": "Aura-SR", "filename": ""
    }
]
FLUX_DEV = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors?download=true",
        "directory": "checkpoints", "filename": ""
    }
]
FLUX_SCHNELL = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
]
FLUX_CLIP = [
    {
        "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors?download=true",
        "directory": "clip", "filename": ""
    },
    {
        "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors?download=true",
        "directory": "clip", "filename": ""
    },
    {
        "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors?download=true",
        "directory": "clip", "filename": ""
    }
]
FLUX_LORA = [
    {
        "url": "https://huggingface.co/comfyanonymous/flux_RealismLora_converted_comfyui/resolve/main/flux_realism_lora.safetensors?download=true",
        "directory": "loras/flux", "filename": ""
    },
]
FLUX_LORA_ARAMINTA = [
    {
        "url": "https://huggingface.co/alvdansen/flux-koda/resolve/main/araminta_k_flux_koda.safetensors?download=true",
        "directory": "loras/araminta", "filename": "flmft-style_flux_koda.safetensors"
    },
    {
        "url": "https://huggingface.co/alvdansen/frosting_lane_flux/resolve/main/flux_dev_frostinglane_araminta_k.safetensors?download=true",
        "directory": "loras/araminta", "filename": "frstingln-illustration_flux_dev_frostinglane.safetensors"
    },
    {
        "url": "https://huggingface.co/alvdansen/flux_film_foto/resolve/main/araminta_k_flux_film_foto.safetensors?download=true",
        "directory": "loras/araminta", "filename": "flmft-photo-style_flux_film_foto.safetensors"
    },
]
