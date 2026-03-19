#!/bin/bash

echo "Installing SCOPE System..."

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
mkdir -p ~/scope_monitor/templates
mkdir -p ~/scope_monitor/static

# Copy files (assumes you've uploaded them)
cp app.py ~/scope_monitor/
cp main.py ~/scope_monitor/
cp templates/* ~/scope_monitor/templates/

# Set up systemd services
sudo cp scope-monitor.service /etc/systemd/system/
sudo cp scope-web.service /etc/systemd/system/

# Set up nginx
sudo cp scope /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/scope /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable scope-monitor
sudo systemctl enable scope-web
sudo systemctl start scope-monitor
sudo systemctl start scope-web
sudo systemctl restart nginx

echo "Installation complete!"
echo "Access the web interface at http://$(hostname -I | awk '{print $1}')"