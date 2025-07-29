import subprocess
from urllib.parse import urlparse
import os # Add this line to import the os module
from IPython.display import display, Javascript

import json
import struct
from pathlib import Path
from typing import Optional, Dict, Any

#declaration of all the libraries above here

def extract_comfyui_workflows(directory_path: str) -> str:
    """
    Extract ComfyUI workflow data from all PNG files in a directory and subdirectories.
    
    Args:
        directory_path (str): Path to directory to search for PNG files
        
    Returns:
        str: Summary message with extraction results
    """
    try:
        directory = Path(directory_path)
        
        if not directory.exists():
            return f"Directory not found: {directory}"
        
        if not directory.is_dir():
            return f"Path is not a directory: {directory}"
        
        # Find all PNG files recursively
        png_files = list(directory.rglob("*.png"))
        
        if not png_files:
            return f"No PNG files found in {directory} and its subdirectories"
        
        success_count = 0
        total_files = len(png_files)
        
        for png_file in png_files:
            try:
                # Read the PNG file
                with open(png_file, 'rb') as f:
                    png_data = f.read()
                
                # Extract workflow metadata
                workflow_data = _extract_png_metadata(png_data)
                
                if workflow_data:
                    # Save workflow data in the same directory as the PNG
                    base_name = png_file.stem
                    workflow_path = png_file.parent / f"{base_name}_workflow.json"
                    
                    with open(workflow_path, 'w', encoding='utf-8') as f:
                        json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                    
                    success_count += 1
                    
            except Exception as e:
                # Continue processing other files even if one fails
                print(f"Warning: Failed to process {png_file.name}: {str(e)}")
                continue
        
        return f"Successfully extracted {success_count} workflow JSON files from {total_files} PNG files"
        
    except Exception as e:
        return f"Error processing directory: {str(e)}"


def _extract_png_metadata(png_data: bytes) -> Optional[Dict[Any, Any]]:
    """
    Extract workflow metadata from PNG file data.
    
    Args:
        png_data (bytes): Raw PNG file data
        
    Returns:
        Optional[Dict]: workflow_data if found, None otherwise
    """
    workflow_data = None
    
    # Check PNG signature
    if len(png_data) < 8 or png_data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("Not a valid PNG file")
    
    offset = 8  # Skip PNG signature
    
    while offset < len(png_data):
        # Need at least 8 bytes for chunk header
        if offset + 8 > len(png_data):
            break
            
        # Read chunk length (4 bytes, big-endian)
        length = struct.unpack('>I', png_data[offset:offset+4])[0]
        
        # Read chunk type (4 bytes)
        chunk_type = png_data[offset+4:offset+8].decode('ascii', errors='ignore')
        
        # Check for text chunks that might contain ComfyUI data
        if chunk_type in ['tEXt', 'iTXt']:
            # Extract chunk data
            chunk_data = png_data[offset+8:offset+8+length]
            
            try:
                # Decode as UTF-8 text
                text = chunk_data.decode('utf-8', errors='ignore')
                
                # Look for workflow data
                if 'workflow' in text:
                    null_index = text.find('\x00')
                    if null_index != -1:
                        key = text[:null_index]
                        value = text[null_index+1:]
                        
                        if key == 'workflow':
                            try:
                                workflow_data = json.loads(value)
                                break  # Found workflow, no need to continue
                            except json.JSONDecodeError:
                                pass  # Continue searching other chunks
                                
            except UnicodeDecodeError:
                # Skip chunks that can't be decoded as text
                pass
        
        # Move to next chunk (8 bytes header + length + 4 bytes CRC)
        offset += 8 + length + 4
        
        # Break on IEND chunk
        if chunk_type == 'IEND':
            break
    
    return workflow_data


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

def create_alert(message):
  display(Javascript(f'alert("{message}");'))
    
def refresh_pod(COMFYUI_REQ,NODES_BASE_PATH):
    # Script to find and install requirements.txt files from subfolders
  
    #%cd /{dest_folder}/ComfyUI
    #COMFYUI_REQ = f"/{dest_folder}/ComfyUI/requirements.txt"
    
    print(f"Installing ComfyUI requirements...")
    core_result = subprocess.run(
                        ['pip', 'install', 'torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124'], 
                        check=True,
                        capture_output=True,
                        text=True
                    )
    
    #!pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124
    req_result = subprocess.run(
                        ['pip', 'install', '-r', COMFYUI_REQ], 
                        check=True,
                        capture_output=True,
                        text=True
                    )
    #!pip install -r /{dest_folder}/ComfyUI/requirements.txt
    print(f"Finished Installing ComfyUI requirements...next we will refresh the nodes")
    # Define the path to search in
    #NODES_BASE_PATH = f"/{dest_folder}/ComfyUI/custom_nodes/"
    
    # Ensure the base path exists
    if not os.path.exists(NODES_BASE_PATH):
        print(f"Error: Path '{NODES_BASE_PATH}' does not exist.")
    else:
        # Initialize counters
        found_count = 0
        installed_count = 0
        
        print(f"Searching for requirements.txt files in subfolders of '{NODES_BASE_PATH}'...")
        
        # Get all immediate subfolders
        subfolders = [f.path for f in os.scandir(NODES_BASE_PATH) if f.is_dir()]
        
        for subfolder in subfolders:
            req_file_path = os.path.join(subfolder, 'requirements.txt')
            
            # Check if requirements.txt exists in the subfolder
            if os.path.isfile(req_file_path):
                found_count += 1
                folder_name = os.path.basename(subfolder)
                print(f"Found requirements.txt in '{folder_name}'")
                
                try:
                    # Run pip install command
                    print(f"Installing requirements from '{req_file_path}'...")
                    result = subprocess.run(
                        ['pip', 'install', '-r', req_file_path], 
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    installed_count += 1
                    print(f"Successfully installed requirements for '{folder_name}'")
                except subprocess.CalledProcessError as e:
                    print(f"Error installing requirements for '{folder_name}': {e.stderr}")
        
        # Summary
        print(f"\nSummary: Found {found_count} requirements.txt files, successfully installed {installed_count}")
        
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
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    }
]
FLUX_SCHNELL = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
FLUX_KONTEXT = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/resolve/main/flux1-kontext-dev.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
FLUX_KONTEXT_FP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI/resolve/main/split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
FLUX_VAE = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
]
FLUX_TOOLS = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev/resolve/main/flux1-fill-dev.safetensors?download=true",
        "directory": "checkpoints", "filename": ""
    },
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev/resolve/main/flux1-redux-dev.safetensors?download=true",
        "directory": "style_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors?download=true",
        "directory": "clip_vision", "filename": ""
    },
]
FLUX_TOOLS_LORA = [
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-Depth-dev-lora/resolve/main/flux1-depth-dev-lora.safetensors?download=true",
        "directory": "loras/flux", "filename": ""
    },
    {
        "url": "https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev-lora/resolve/main/flux1-canny-dev-lora.safetensors?download=true",
        "directory": "loras/flux", "filename": ""
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
CHROMA = [
    {
        "url":"https://huggingface.co/lodestones/Chroma/resolve/main/chroma-unlocked-v43-detail-calibrated.safetensors?download=true",
        "directory":"diffusion_models","filename": ""
    },
    {
        "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors?download=true",
        "directory": "clip", "filename": ""
    },
    {
        "url": "https://huggingface.co/lodestones/Chroma/resolve/main/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
]
FLUX_LORA = [
    {
        "url": "https://huggingface.co/comfyanonymous/flux_RealismLora_converted_comfyui/resolve/main/flux_realism_lora.safetensors?download=true",
        "directory": "loras/flux", "filename": ""
    },
]
FLUX_CNET = [
    {
        "url": "https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro/resolve/main/diffusion_pytorch_model.safetensors?download=true",
        "directory": "controlnet", "filename": "FLUX.1-dev-ControlNet-Union-Pro.safetensors"
    },
]
FLUX_CNET2 = [
    {
        "url": "https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0/resolve/main/diffusion_pytorch_model.safetensors?download=true",
        "directory": "controlnet", "filename": "FLUX.1-dev-ControlNet-Union-Pro.2.0.safetensors"
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
ULTRA_BBOX = [
    {
        "url": "https://huggingface.co/camenduru/IICF/resolve/main/ultralytics/bbox/Eyes.pt?download=true",
        "directory": "ultralytics/bbox", "filename": "Eyes.pt"
    },
]
WAN21_T2V = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_14B_bf16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },    
]
WAN21_T2VFP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN21_I2V = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_bf16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_720p_14B_bf16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN21_I2VFP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN21_MISC = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true",
        "directory": "clip_vision", "filename": ""
    },
]
WAN22_MISC = [
        {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
]
WAN22_TI2V_FP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN22_TI2V = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN22_TI2V_5B = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN22_T2VFP8_HN = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN22_T2VFP8_LN = [
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
        "directory": "diffusion_models", "filename": ""
    },
]
WAN21_KIJAI = [
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-720P_fp8_e4m3fn.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },    
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-T2V-14B_fp8_e4m3fn.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_fp32.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/open-clip-xlm-roberta-large-vit-huge-14_visual_fp16.safetensors?download=true",
        "directory": "clip", "filename": ""
    },
    {
        "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/open-clip-xlm-roberta-large-vit-huge-14_visual_fp32.safetensors?download=true",
        "directory": "clip", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true",
        "directory": "clip_vision", "filename": ""
    },
]
HIDREAM_I1_FULL = [
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_full_fp16.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    }
]
HIDREAM_I1_FULLFP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_full_fp8.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    }
]
HIDREAM_I1_FASTFP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_fast_fp8.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    }
]
HIDREAM_I1_DEVFP8 = [
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_dev_fp8.safetensors?download=true",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    }
]
HIDREAM_E1_FULL = [
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_e1_full_bf16.safetensors",
        "directory": "diffusion_models", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
        "directory": "vae", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    },
    {
        "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
        "directory": "text_encoders", "filename": ""
    }
]
