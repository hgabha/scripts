cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
apt-get update
python -m venv venv
source venv/bin/activate
#git pull
#pip install --upgrade pip
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124

git clone https://github.com/ltdrdata/ComfyUI-Manager custom_nodes/ComfyUI-Manager
pip install -r custom_nodes/ComfyUI-Manager/requirements.txt

git clone https://github.com/cubiq/ComfyUI_essentials custom_nodes/ComfyUI_essentials
git clone https://github.com/crystian/ComfyUI-Crystools /{dest_folder}/ComfyUI/custom_nodes/ComfyUI-Crystools
pip install -r /{dest_folder}/ComfyUI/custom_nodes/ComfyUI-Crystools/requirements.txt
