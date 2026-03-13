#!/bin/bash

echo "Installing Environmental Monitoring System..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv nginx

# Create virtual environment
python3 -m venv ~/env
source ~/env/bin/activate

# Install Python packages
pip install flask flask-session python-dotenv pytz
pip install numpy scipy scikit-learn
pip install pyserial adafruit-blinka adafruit-circuitpython-ads1x15

# Create project directory
mkdir -p ~/environmental_monitor/templates
mkdir -p ~/environmental_monitor/static

# Copy files (assumes you've uploaded them)
cp app.py ~/environmental_monitor/
cp main.py ~/environmental_monitor/
cp templates/* ~/environmental_monitor/templates/

# Set up systemd services
sudo cp environmental-monitor.service /etc/systemd/system/
sudo cp environmental-web.service /etc/systemd/system/

# Set up nginx
sudo cp environmental /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/environmental /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable environmental-monitor
sudo systemctl enable environmental-web
sudo systemctl start environmental-monitor
sudo systemctl start environmental-web
sudo systemctl restart nginx

echo "Installation complete!"
echo "Access the web interface at http://$(hostname -I | awk '{print $1}')"