#!/bin/bash
echo "Setting up Environmental Monitoring System on Raspberry Pi"

# Update system
sudo apt update && sudo apt upgrade -y

# Enable interfaces
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial 2  # Enable serial but disable console

# Install system packages
sudo apt install -y python3-pip python3-venv python3-full libatlas-base-dev

# Create virtual environment
python3 -m venv ~/env
source ~/env/bin/activate

# Install Python packages
pip install --upgrade pip
pip install adafruit-blinka
pip install adafruit-circuitpython-ads1x15
pip install numpy scipy scikit-learn
pip install pyserial

echo "Setup complete! Run 'source ~/env/bin/activate' before running your script"