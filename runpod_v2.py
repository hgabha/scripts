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
import threading
import time
import requests
from tqdm import tqdm

# Your existing helper functions (keeping them as-is)
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

# Model configurations (truncated for space - use your full MODEL_CONFIGS)
MODEL_CONFIGS = {
    "Stable Diffusion 1.5": {
        "hf": True,
        "files": [
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
    },
    "FLUX Dev": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    }
    # Add your other configs here...
}

class AdvancedDownloader:
    """Advanced downloader with per-file progress tracking"""
    
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.cancel_flag = threading.Event()
        
    def download_with_progress(self, url, filepath, hf_token=None, chunk_size=8192):
        """Download file with progress tracking using requests"""
        headers = {}
        if hf_token:
            headers['Authorization'] = f'Bearer {hf_token}'
            
        try:
            # Get file size first
            response = self.session.head(url, headers=headers, allow_redirects=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # Start the actual download
            response = self.session.get(url, headers=headers, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self.cancel_flag.is_set():
                        break
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Calculate progress percentage
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            if self.progress_callback:
                                self.progress_callback(progress, downloaded, total_size)
                                
            return not self.cancel_flag.is_set()
            
        except Exception as e:
            print(f"Download error: {str(e)}")
            return False
            
    def cancel_download(self):
        """Cancel the current download"""
        self.cancel_flag.set()
        
    def reset_cancel_flag(self):
        """Reset cancel flag for new downloads"""
        self.cancel_flag.clear()

class ModelDownloaderInterface:
    def __init__(self, base_path="/content", hf_token=""):
        self.base_path = base_path
        self.hf_token = hf_token
        self.is_downloading = False
        self.current_downloader = None
        
        # Create widgets
        self.model_dropdown = widgets.Dropdown(
            options=list(MODEL_CONFIGS.keys()),
            description='Model Set:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='350px')
        )
        
        self.download_btn = widgets.Button(
            description='Download Selected',
            button_style='success',
            icon='download',
            layout=widgets.Layout(width='200px')
        )
        
        self.cancel_btn = widgets.Button(
            description='Cancel Download',
            button_style='warning',
            icon='stop',
            layout=widgets.Layout(width='200px', visibility='hidden')
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
        
        # Overall progress bar
        self.overall_progress = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description='Overall:',
            bar_style='info',
            style={'bar_color': '#2196F3', 'description_width': '80px'},
            layout=widgets.Layout(width='500px', visibility='hidden')
        )
        
        # File progress bar  
        self.file_progress = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description='File:',
            bar_style='success',
            style={'bar_color': '#4CAF50', 'description_width': '80px'},
            layout=widgets.Layout(width='500px', visibility='hidden')
        )
        
        # Progress labels
        self.overall_label = widgets.HTML(
            value="",
            layout=widgets.Layout(visibility='hidden')
        )
        
        self.file_label = widgets.HTML(
            value="",
            layout=widgets.Layout(visibility='hidden')
        )
        
        # Speed and ETA display
        self.speed_label = widgets.HTML(
            value="",
            layout=widgets.Layout(visibility='hidden')
        )
        
        # Log output area with scrolling
        self.log_output = widgets.Output(
            layout=widgets.Layout(
                height='200px',
                width='100%',
                border='1px solid #ccc',
                overflow='auto',
                visibility='hidden'
            )
        )
        
        # Show/Hide logs toggle
        self.toggle_logs_btn = widgets.Button(
            description='Show Logs',
            button_style='',
            icon='eye',
            layout=widgets.Layout(width='120px')
        )
        
        # Bind events
        self.download_btn.on_click(self._on_download)
        self.cancel_btn.on_click(self._on_cancel)
        self.delete_btn.on_click(self._on_delete)
        self.info_btn.on_click(self._on_show_info)
        self.toggle_logs_btn.on_click(self._toggle_logs)
        
        # Download state
        self.current_file_idx = 0
        self.total_files = 0
        self.current_filename = ""
        self.download_start_time = 0
        
    def _toggle_logs(self, button):
        """Toggle log output visibility"""
        if self.log_output.layout.visibility == 'hidden':
            self.log_output.layout.visibility = 'visible'
            self.toggle_logs_btn.description = 'Hide Logs'
            self.toggle_logs_btn.icon = 'eye-slash'
        else:
            self.log_output.layout.visibility = 'hidden'
            self.toggle_logs_btn.description = 'Show Logs'
            self.toggle_logs_btn.icon = 'eye'
    
    def _log(self, message):
        """Add message to log output"""
        with self.log_output:
            print(message)
    
    def _show_progress_bars(self, visible=True):
        """Show or hide all progress indicators"""
        visibility = 'visible' if visible else 'hidden'
        self.overall_progress.layout.visibility = visibility
        self.file_progress.layout.visibility = visibility
        self.overall_label.layout.visibility = visibility
        self.file_label.layout.visibility = visibility
        self.speed_label.layout.visibility = visibility
        self.cancel_btn.layout.visibility = visibility if visible else 'hidden'
    
    def _update_overall_progress(self, current_file, total_files, filename=""):
        """Update overall progress across all files"""
        self.current_file_idx = current_file
        self.total_files = total_files
        self.current_filename = filename
        
        if total_files > 0:
            percentage = int(((current_file - 1) / total_files) * 100)
            self.overall_progress.value = percentage
            self.overall_label.value = f"<b>Processing file {current_file} of {total_files}:</b> {filename}"
    
    def _file_progress_callback(self, progress_percent, downloaded_bytes, total_bytes):
        """Callback for individual file download progress"""
        self.file_progress.value = progress_percent
        
        # Calculate download speed and ETA
        if hasattr(self, 'file_start_time'):
            elapsed = time.time() - self.file_start_time
            if elapsed > 0:
                speed = downloaded_bytes / elapsed
                speed_mb = speed / (1024 * 1024)
                
                if total_bytes > downloaded_bytes and speed > 0:
                    eta_seconds = (total_bytes - downloaded_bytes) / speed
                    eta_min, eta_sec = divmod(int(eta_seconds), 60)
                    eta_str = f"{eta_min}m {eta_sec}s" if eta_min > 0 else f"{eta_sec}s"
                else:
                    eta_str = "0s"
                
                # Format file size
                total_mb = total_bytes / (1024 * 1024)
                downloaded_mb = downloaded_bytes / (1024 * 1024)
                
                self.file_label.value = f"<b>{progress_percent}%</b> - {downloaded_mb:.1f}MB / {total_mb:.1f}MB"
                self.speed_label.value = f"<b>Speed:</b> {speed_mb:.1f} MB/s | <b>ETA:</b> {eta_str}"
    
    def _reset_ui_state(self):
        """Reset UI to initial state"""
        self._show_progress_bars(False)
        self._set_buttons_disabled(False)
        self.overall_progress.value = 0
        self.file_progress.value = 0
        self.overall_label.value = ""
        self.file_label.value = ""
        self.speed_label.value = ""
        self.is_downloading = False
        self.current_downloader = None
    
    def _set_buttons_disabled(self, disabled=True):
        """Enable or disable action buttons"""
        self.download_btn.disabled = disabled
        self.delete_btn.disabled = disabled
        self.info_btn.disabled = disabled
        
        if disabled:
            self.download_btn.description = 'Downloading...'
            self.download_btn.icon = 'spinner'
        else:
            self.download_btn.description = 'Download Selected'
            self.download_btn.icon = 'download'
    
    def _on_cancel(self, button):
        """Cancel current download"""
        if self.current_downloader:
            self._log("🛑 Cancelling download...")
            self.current_downloader.cancel_download()
    
    def _on_download(self, button):
        # Early return if already downloading
        if self.is_downloading:
            self._log("⚠️  Download already in progress, ignoring click")
            return
            
        # Set downloading state immediately
        self.is_downloading = True
        selected_model = self.model_dropdown.value
        selected_config = MODEL_CONFIGS[selected_model]
        
        self._log(f"🚀 Starting download for: {selected_model}")
        self._log(f"📁 Base path: {self.base_path}")
        
        # Determine if HF token should be used
        use_hf_token = selected_config.get("hf", False)
        token_to_use = self.hf_token if use_hf_token else ""
        
        if use_hf_token:
            self._log("🔑 Using HuggingFace token for authentication")
        else:
            self._log("🌐 Using public download (no token required)")
            
        self._log("=" * 50)
        
        # Show progress bars and disable buttons
        self._show_progress_bars(True)
        self._set_buttons_disabled(True)
        
        # Start download in separate thread to prevent UI blocking
        download_thread = threading.Thread(
            target=self._download_files_threaded,
            args=(selected_config["files"], token_to_use)
        )
        download_thread.daemon = True
        download_thread.start()
    
    def _download_files_threaded(self, files_list, hf_token):
        """Download files in a separate thread"""
        try:
            total_files = len(files_list)
            
            for idx, file_config in enumerate(files_list, 1):
                # Check if download was cancelled
                if not self.is_downloading:
                    self._log("⚠️  Download was cancelled by user")
                    break
                
                filename = file_config['filename'] if file_config['filename'] else get_filename_from_url(file_config['url'])
                
                # Update overall progress
                self._update_overall_progress(idx, total_files, filename)
                
                # Reset file progress
                self.file_progress.value = 0
                self.file_start_time = time.time()
                
                # Check if file already exists
                directory = os.path.join(self.base_path, file_config["directory"].lstrip('/'))
                os.makedirs(directory, exist_ok=True)
                full_path = os.path.join(directory, filename)
                
                if os.path.exists(full_path):
                    self._log(f"File already exists: {filename}")
                    self._log("Skipping download...")
                    self.file_progress.value = 100
                    continue
                
                # Download the file
                self._log(f"📥 Downloading: {filename}")
                
                success = self._download_single_file_advanced(
                    file_config, hf_token, full_path
                )
                
                if success:
                    self._log(f"✅ Successfully downloaded: {filename}")
                    self.file_progress.value = 100
                else:
                    self._log(f"❌ Failed to download: {filename}")
                    break
            
            # Update overall progress to 100% when complete
            if self.is_downloading:  # Only if not cancelled
                self.overall_progress.value = 100
                self._log("=" * 50)
                self._log("🎉 All downloads completed successfully!")
            
        except Exception as e:
            self._log(f"❌ Error during download: {str(e)}")
        finally:
            # Always reset UI state
            self._log("🔄 Resetting UI state...")
            self._reset_ui_state()
    
    def _download_single_file_advanced(self, file_config, hf_token, full_path):
        """Download a single file with advanced progress tracking"""
        try:
            # Create advanced downloader with progress callback
            self.current_downloader = AdvancedDownloader(
                progress_callback=self._file_progress_callback
            )
            
            # Download the file
            success = self.current_downloader.download_with_progress(
                url=file_config["url"],
                filepath=full_path,
                hf_token=hf_token if hf_token else None
            )
            
            return success
            
        except Exception as e:
            self._log(f"Download error: {str(e)}")
            return False
    
    def _on_delete(self, button):
        if self.is_downloading:
            self._log("⚠️  Cannot delete while download is in progress")
            return
            
        selected_model = self.model_dropdown.value
        selected_config = MODEL_CONFIGS[selected_model]
        
        self._log(f"🗑️ Starting deletion for: {selected_model}")
        self._log(f"📁 Base path: {self.base_path}")
        self._log("=" * 50)
        
        try:
            delete_files(selected_config["files"], self.base_path)
            self._log("=" * 50)
            self._log("✅ Deletion process completed!")
        except Exception as e:
            self._log(f"❌ Error during deletion: {str(e)}")
    
    def _on_show_info(self, button):
        selected_model = self.model_dropdown.value
        selected_config = MODEL_CONFIGS[selected_model]
        
        self._log(f"📋 Details for: {selected_model}")
        self._log("=" * 50)
        self._log(f"Number of files: {len(selected_config['files'])}")
        self._log(f"Requires HF Token: {'Yes' if selected_config.get('hf', False) else 'No'}")
        self._log("")
        
        for i, item in enumerate(selected_config["files"], 1):
            filename = item['filename'] if item['filename'] else get_filename_from_url(item['url'])
            self._log(f"{i}. File: {filename}")
            self._log(f"   Directory: {item['directory']}")
            self._log(f"   URL: {item['url'][:60]}{'...' if len(item['url']) > 60 else ''}")
            self._log("")
    
    def display(self):
        """Display the enhanced interface"""
        # Header
        header = widgets.HTML("<h2>🚀 Advanced ComfyUI Model Downloader</h2>")
        
        # Model selection section
        selection_box = widgets.VBox([
            widgets.HTML("<h3>📦 Model Selection</h3>"),
            self.model_dropdown
        ])
        
        # Action buttons
        main_buttons = widgets.HBox([
            self.download_btn,
            self.delete_btn,
            self.info_btn
        ], layout=widgets.Layout(justify_content='flex-start'))
        
        # Control buttons
        control_buttons = widgets.HBox([
            self.cancel_btn,
            self.toggle_logs_btn
        ], layout=widgets.Layout(justify_content='flex-start'))
        
        # Progress section
        progress_section = widgets.VBox([
            widgets.HTML("<h4>📊 Download Progress</h4>"),
            self.overall_progress,
            self.overall_label,
            widgets.HTML("<br>"),
            self.file_progress,
            self.file_label,
            self.speed_label
        ])
        
        # Logs section
        logs_section = widgets.VBox([
            widgets.HTML("<h4>📝 Download Logs</h4>"),
            self.log_output
        ])
        
        # Main interface
        main_interface = widgets.VBox([
            header,
            selection_box,
            widgets.HTML("<h3>⚡ Actions</h3>"),
            main_buttons,
            control_buttons,
            progress_section,
            logs_section
        ])
        
        display(main_interface)

# Enhanced interface creation function
def create_advanced_model_downloader(base_path="/content", hf_token=""):
    """Create and display the advanced model downloader interface"""
    interface = ModelDownloaderInterface(base_path, hf_token)
    interface.display()
    return interface

# Usage example:
# downloader = create_advanced_model_downloader(base_path="/your/path", hf_token="your_token")

MODEL_CONFIGS = {
    "Stable Diffusion 1.5": {
        "hf": False,
        "files": [
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
    },
    "Juggernaut 1.5": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/KamCastle/jugg/resolve/main/juggernaut_reborn.safetensors",
                "directory": "checkpoints",
                "filename": ""
            }
        ]
    },
    "Stable Diffusion XL": {
        "hf": False,
        "files": [
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
        ]
    },
    "Juggernaut SDXL": {
        "hf": False,
        "files": [
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
        ]
    },
    "SUPIR Original": {
        "hf": False,
        "files": [
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
    },
    "SUPIR Kijai": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Kijai/SUPIR_pruned/resolve/main/SUPIR-v0F_fp16.safetensors?download=true",
                "directory": "checkpoints",
                "filename": "Kijai_SUPIR-V0F_fp16.safetensors"
            },
            {
                "url": "https://huggingface.co/Kijai/SUPIR_pruned/resolve/main/SUPIR-v0Q_fp16.safetensors?download=true",
                "directory": "checkpoints",
                "filename": "Kijai_SUPIR-V0Q_fp16.safetensors"
            }
        ]
    },
    "AuraSR": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/fal/AuraSR/resolve/main/model.safetensors?download=true",
                "directory": "Aura-SR",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/fal/AuraSR/resolve/main/config.json?download=true",
                "directory": "Aura-SR",
                "filename": ""
            }
        ]
    },
    "FLUX Dev": {
        "hf": True,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "FLUX Schnell": {
        "hf": True,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "FLUX Kontext": {
        "hf": True,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/resolve/main/flux1-kontext-dev.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "FLUX Kontext FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI/resolve/main/split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "FLUX VAE": {
        "hf": True,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            }
        ]
    },
    "FLUX Tools": {
        "hf": True,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev/resolve/main/flux1-fill-dev.safetensors?download=true",
                "directory": "checkpoints",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev/resolve/main/flux1-redux-dev.safetensors?download=true",
                "directory": "style_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors?download=true",
                "directory": "clip_vision",
                "filename": ""
            }
        ]
    },
    "FLUX Tools LoRA": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-Depth-dev-lora/resolve/main/flux1-depth-dev-lora.safetensors?download=true",
                "directory": "loras/flux",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev-lora/resolve/main/flux1-canny-dev-lora.safetensors?download=true",
                "directory": "loras/flux",
                "filename": ""
            }
        ]
    },
    "FLUX CLIP": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            }
        ]
    },
    "Chroma": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/lodestones/Chroma/resolve/main/chroma-unlocked-v43-detail-calibrated.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/lodestones/Chroma/resolve/main/ae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            }
        ]
    },
    "Qwen Image": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_bf16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            }
        ]
    },
    "Qwen Image FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            }
        ]
    },
    "FLUX LoRA Realism": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/comfyanonymous/flux_RealismLora_converted_comfyui/resolve/main/flux_realism_lora.safetensors?download=true",
                "directory": "loras/flux",
                "filename": ""
            }
        ]
    },
    "FLUX ControlNet Union Pro": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro/resolve/main/diffusion_pytorch_model.safetensors?download=true",
                "directory": "controlnet",
                "filename": "FLUX.1-dev-ControlNet-Union-Pro.safetensors"
            }
        ]
    },
    "FLUX ControlNet Union Pro 2.0": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0/resolve/main/diffusion_pytorch_model.safetensors?download=true",
                "directory": "controlnet",
                "filename": "FLUX.1-dev-ControlNet-Union-Pro.2.0.safetensors"
            }
        ]
    },
    "FLUX LoRA Araminta Collection": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/alvdansen/flux-koda/resolve/main/araminta_k_flux_koda.safetensors?download=true",
                "directory": "loras/araminta",
                "filename": "flmft-style_flux_koda.safetensors"
            },
            {
                "url": "https://huggingface.co/alvdansen/frosting_lane_flux/resolve/main/flux_dev_frostinglane_araminta_k.safetensors?download=true",
                "directory": "loras/araminta",
                "filename": "frstingln-illustration_flux_dev_frostinglane.safetensors"
            },
            {
                "url": "https://huggingface.co/alvdansen/flux_film_foto/resolve/main/araminta_k_flux_film_foto.safetensors?download=true",
                "directory": "loras/araminta",
                "filename": "flmft-photo-style_flux_film_foto.safetensors"
            }
        ]
    },
    "UltraLytics BBox Eyes": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/camenduru/IICF/resolve/main/ultralytics/bbox/Eyes.pt?download=true",
                "directory": "ultralytics/bbox",
                "filename": "Eyes.pt"
            }
        ]
    },
    "Wan 2.1 T2V": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_14B_bf16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.1 T2V FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.1 I2V": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_bf16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_720p_14B_bf16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.1 I2V FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.1 Misc": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true",
                "directory": "clip_vision",
                "filename": ""
            }
        ]
    },
    "Wan 2.2 Misc": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            }
        ]
    },
    "Wan 2.2 TI2V FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.2 TI2V": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.2 TI2V 5B": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.2 T2V FP8 High Noise": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.2 T2V FP8 Low Noise": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
                "directory": "diffusion_models",
                "filename": ""
            }
        ]
    },
    "Wan 2.1 Kijai Complete": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-720P_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-T2V-14B_fp8_e4m3fn.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_fp32.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/open-clip-xlm-roberta-large-vit-huge-14_visual_fp16.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/open-clip-xlm-roberta-large-vit-huge-14_visual_fp32.safetensors?download=true",
                "directory": "clip",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true",
                "directory": "clip_vision",
                "filename": ""
            }
        ]
    },
    "HiDream I1 Full": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_full_fp16.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            }
        ]
    },
    "HiDream I1 Fast FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_fast_fp8.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            }
        ]
    },
    "HiDream I1 Dev FP8": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_i1_dev_fp8.safetensors?download=true",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            }
        ]
    },
    "HiDream E1 Full": {
        "hf": False,
        "files": [
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/diffusion_models/hidream_e1_full_bf16.safetensors",
                "directory": "diffusion_models",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/vae/ae.safetensors?download=true",
                "directory": "vae",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_l_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/clip_g_hidream.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            },
            {
                "url": "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files/text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors?download=true",
                "directory": "text_encoders",
                "filename": ""
            }
        ]
    }
}
