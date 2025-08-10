import subprocess
from urllib.parse import urlparse
import os
from IPython.display import display, Javascript
import ipywidgets as widgets
from IPython.display import clear_output
import json
import struct
from pathlib import Path
from typing import Optional, Dict, Any

# Your existing functions (keeping them as-is)
def extract_comfyui_workflows(directory_path: str) -> str:
    """Extract ComfyUI workflow data from all PNG files in a directory and subdirectories."""
    try:
        directory = Path(directory_path)
        
        if not directory.exists():
            return f"Directory not found: {directory}"
        
        if not directory.is_dir():
            return f"Path is not a directory: {directory}"
        
        png_files = list(directory.rglob("*.png"))
        
        if not png_files:
            return f"No PNG files found in {directory} and its subdirectories"
        
        success_count = 0
        total_files = len(png_files)
        
        for png_file in png_files:
            try:
                with open(png_file, 'rb') as f:
                    png_data = f.read()
                
                workflow_data = _extract_png_metadata(png_data)
                
                if workflow_data:
                    base_name = png_file.stem
                    workflow_path = png_file.parent / f"{base_name}_workflow.json"
                    
                    with open(workflow_path, 'w', encoding='utf-8') as f:
                        json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                    
                    success_count += 1
                    
            except Exception as e:
                print(f"Warning: Failed to process {png_file.name}: {str(e)}")
                continue
        
        return f"Successfully extracted {success_count} workflow JSON files from {total_files} PNG files"
        
    except Exception as e:
        return f"Error processing directory: {str(e)}"

def _extract_png_metadata(png_data: bytes) -> Optional[Dict[Any, Any]]:
    """Extract workflow metadata from PNG file data."""
    workflow_data = None
    
    if len(png_data) < 8 or png_data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("Not a valid PNG file")
    
    offset = 8
    
    while offset < len(png_data):
        if offset + 8 > len(png_data):
            break
            
        length = struct.unpack('>I', png_data[offset:offset+4])[0]
        chunk_type = png_data[offset+4:offset+8].decode('ascii', errors='ignore')
        
        if chunk_type in ['tEXt', 'iTXt']:
            chunk_data = png_data[offset+8:offset+8+length]
            
            try:
                text = chunk_data.decode('utf-8', errors='ignore')
                
                if 'workflow' in text:
                    null_index = text.find('\x00')
                    if null_index != -1:
                        key = text[:null_index]
                        value = text[null_index+1:]
                        
                        if key == 'workflow':
                            try:
                                workflow_data = json.loads(value)
                                break
                            except json.JSONDecodeError:
                                pass
                                
            except UnicodeDecodeError:
                pass
        
        offset += 8 + length + 4
        
        if chunk_type == 'IEND':
            break
    
    return workflow_data

def get_filename_from_url(url):
    """Extract filename from URL, removing query parameters"""
    path = urlparse(url).path
    filename = os.path.basename(path)
    return filename

def download_files(urls_array, base_path, hf_token):
    """Download files from URLs array using wget if they don't already exist"""
    num_urls = len(urls_array)
    print(f"Found {num_urls} URLs to download")

    for idx, entry in enumerate(urls_array, 1):
        url = entry["url"]
        directory = os.path.join(base_path, entry["directory"].lstrip('/'))
        provided_filename = entry["filename"]

        os.makedirs(directory, exist_ok=True)

        if provided_filename:
            filename = provided_filename
        else:
            filename = get_filename_from_url(url)

        full_path = os.path.join(directory, filename)

        if os.path.exists(full_path):
            print(f"File already exists: {full_path}")
            print("Skipping download...")
            continue

        print(f"Downloading: {filename}")

        try:
            if hf_token == '':
                subprocess.run([
                    "wget",
                    "-O", full_path,
                    url,
                    "--quiet",
                    "--show-progress",
                    "--progress=bar:force:noscroll"
                ], check=True)
                print(f"Successfully downloaded: {filename}")
            else:
                subprocess.run([
                    "wget",
                    "--header", f"Authorization: Bearer {hf_token}",
                    "-O", full_path,
                    url,
                    "--quiet",
                    "--show-progress",
                    "--progress=bar:force:noscroll"
                ], check=True)
                print(f"Successfully downloaded: {filename}")

        except subprocess.CalledProcessError as e:
            print(f"Error downloading {url}: {e}")
        except Exception as e:
            print(f"Unexpected error with {url}: {e}")

def delete_files(urls_array, base_path):
    """Delete files from URLs array"""
    num_urls = len(urls_array)

    for idx, entry in enumerate(urls_array, 1):
        url = entry["url"]
        directory = os.path.join(base_path, entry["directory"])
        provided_filename = entry["filename"]

        if provided_filename:
            filename = provided_filename
        else:
            filename = get_filename_from_url(url)

        full_path = os.path.join(directory, filename)

        print(f"\nAttempting to delete file {idx} of {num_urls}")

        if os.path.exists(full_path):
            print(f"Found file {full_path}...deleted!")
            os.remove(full_path)
        else:
            print(f"Skipping file {full_path}...not found!")
            continue

def create_alert(message):
    display(Javascript(f'alert("{message}");'))
    
def refresh_pod(COMFYUI_REQ, NODES_BASE_PATH):
    """Refresh pod by installing requirements"""
    print(f"Installing ComfyUI requirements...")
    core_result = subprocess.run(
        ['pip', 'install', 'torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu124'], 
        check=True,
        capture_output=True,
        text=True
    )
    
    req_result = subprocess.run(
        ['pip', 'install', '-r', COMFYUI_REQ], 
        check=True,
        capture_output=True,
        text=True
    )
    
    print(f"Finished Installing ComfyUI requirements...next we will refresh the nodes")
    
    if not os.path.exists(NODES_BASE_PATH):
        print(f"Error: Path '{NODES_BASE_PATH}' does not exist.")
    else:
        found_count = 0
        installed_count = 0
        
        print(f"Searching for requirements.txt files in subfolders of '{NODES_BASE_PATH}'...")
        
        subfolders = [f.path for f in os.scandir(NODES_BASE_PATH) if f.is_dir()]
        
        for subfolder in subfolders:
            req_file_path = os.path.join(subfolder, 'requirements.txt')
            
            if os.path.isfile(req_file_path):
                found_count += 1
                folder_name = os.path.basename(subfolder)
                print(f"Found requirements.txt in '{folder_name}'")
                
                try:
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
        
        print(f"\nSummary: Found {found_count} requirements.txt files, successfully installed {installed_count}")

# Model configurations
MODEL_CONFIGS = {
    "Stable Diffusion 1.5": [
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
    ],
    "Juggernaut 1.5": [
        {
            "url": "https://huggingface.co/KamCastle/jugg/resolve/main/juggernaut_reborn.safetensors",
            "directory": "checkpoints",
            "filename": ""
        }
    ],
    "Stable Diffusion XL": [
        {
            "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors?download=true",
            "directory": "checkpoints", 
            "filename": ""
        },
        {
            "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors?download=true",
            "directory": "checkpoints", 
            "filename": ""
        },
        {
            "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/vae/diffusion_pytorch_model.safetensors?download=true",
            "directory": "vae", 
            "filename": "sd_xl_VAE.safetensors"
        }
    ],
    "Juggernaut SDXL": [
        {
            "url": "https://huggingface.co/RunDiffusion/Juggernaut-XL-Lightning/resolve/main/Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors",
            "directory": "checkpoints", 
            "filename": ""
        },
        {
            "url": "https://huggingface.co/RunDiffusion/Juggernaut-XL-v9/resolve/main/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
            "directory": "checkpoints", 
            "filename": ""
        }
    ],
    "SUPIR Models": [
        {
            "url": "https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0F.ckpt?download=true",
            "directory": "checkpoints", 
            "filename": ""
        },
        {
            "url": "https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0Q.ckpt?download=true",
            "directory": "checkpoints", 
            "filename": ""
        }
    ]
}

class ModelDownloaderInterface:
    def __init__(self, base_path="/content", hf_token=""):
        self.base_path = base_path
        self.hf_token = hf_token
        
        # Create widgets
        self.model_dropdown = widgets.Dropdown(
            options=list(MODEL_CONFIGS.keys()),
            description='Model Set:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='300px')
        )
        
        self.download_btn = widgets.Button(
            description='Download Selected',
            button_style='success',
            icon='download',
            layout=widgets.Layout(width='200px')
        )
        
        self.delete_btn = widgets.Button(
            description='Delete Selected',
            button_style='danger',
            icon='trash',
            layout=widgets.Layout(width='200px')
        )
        
        self.info_btn = widgets.Button(
            description='Show Details',
            button_style='info',
            icon='info',
            layout=widgets.Layout(width='200px')
        )
        
        # Bind events
        self.download_btn.on_click(self._on_download)
        self.delete_btn.on_click(self._on_delete)
        self.info_btn.on_click(self._on_show_info)
        
    def _on_download(self, button):
        selected_model = self.model_dropdown.value
        
        print(f"🚀 Starting download for: {selected_model}")
        print(f"📁 Base path: {self.base_path}")
        print("=" * 50)
        
        try:
            selected_config = MODEL_CONFIGS[selected_model]
            download_files(selected_config, self.base_path, self.hf_token)
            print("=" * 50)
            print("✅ Download process completed!")
        except Exception as e:
            print(f"❌ Error during download: {str(e)}")
    
    def _on_delete(self, button):
        selected_model = self.model_dropdown.value
        
        print(f"🗑️ Starting deletion for: {selected_model}")
        print(f"📁 Base path: {self.base_path}")
        print("=" * 50)
        
        try:
            selected_config = MODEL_CONFIGS[selected_model]
            delete_files(selected_config, self.base_path)
            print("=" * 50)
            print("✅ Deletion process completed!")
        except Exception as e:
            print(f"❌ Error during deletion: {str(e)}")
    
    def _on_show_info(self, button):
        selected_model = self.model_dropdown.value
        selected_config = MODEL_CONFIGS[selected_model]
        
        print(f"📋 Details for: {selected_model}")
        print("=" * 50)
        print(f"Number of files: {len(selected_config)}")
        print()
        
        for i, item in enumerate(selected_config, 1):
            filename = item['filename'] if item['filename'] else get_filename_from_url(item['url'])
            print(f"{i}. File: {filename}")
            print(f"   Directory: {item['directory']}")
            print(f"   URL: {item['url'][:60]}{'...' if len(item['url']) > 60 else ''}")
            print()
    
    def display(self):
        """Display the interface"""
        # Model selection section
        selection_box = widgets.VBox([
            widgets.HTML("<h3>📦 Model Selection</h3>"),
            self.model_dropdown
        ])
        
        # Action buttons
        buttons_box = widgets.HBox([
            self.download_btn,
            self.delete_btn,
            self.info_btn
        ], layout=widgets.Layout(justify_content='flex-start'))
        
        # Main interface
        main_interface = widgets.VBox([
            widgets.HTML("<h2>🤖 ComfyUI Model Downloader</h2>"),
            selection_box,
            widgets.HTML("<h3>⚡ Actions</h3>"),
            buttons_box
        ])
        
        display(main_interface)

# Create and display the interface
def create_model_downloader_interface(base_path="/content", hf_token=""):
    """Create and display the model downloader interface"""
    interface = ModelDownloaderInterface(base_path, hf_token)
    interface.display()
    return interface

# Usage example:
# downloader = create_model_downloader_interface(base_path="/your/path", hf_token="your_token")
