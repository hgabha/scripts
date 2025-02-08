cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
apt-get update
python -m venv venv
source venv/bin/activate
echo "Virtual Environment created VENV & activated"
#git pull
#pip install --upgrade pip
#--extra-index-url https://download.pytorch.org/whl/cu124
echo "Installing requirements"
pip install -r requirements.txt 

echo "Installing Custom Nodes"

git clone https://github.com/ltdrdata/ComfyUI-Manager custom_nodes/ComfyUI-Manager
pip install -r custom_nodes/ComfyUI-Manager/requirements.txt

git clone https://github.com/cubiq/ComfyUI_essentials custom_nodes/ComfyUI_essentials
git clone https://github.com/crystian/ComfyUI-Crystools /workspace/ComfyUI/custom_nodes/ComfyUI-Crystools
pip install -r /workspace/ComfyUI/custom_nodes/ComfyUI-Crystools/requirements.txt
deactivate
