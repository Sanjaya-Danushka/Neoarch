#!/bin/bash
# NeoArch Scheduled Update Setup Script

echo "NeoArch Scheduled Update Setup"
echo "=============================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should NOT be run as root. Please run as your regular user."
   exit 1
fi

# Copy service and timer files to systemd directory
echo "Installing systemd service and timer..."

sudo cp neoarch-update.service /etc/systemd/system/
sudo cp neoarch-update.timer /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start the timer
sudo systemctl enable neoarch-update.timer
sudo systemctl start neoarch-update.timer

echo "✓ Scheduled update service installed and enabled!"
echo ""
echo "The system will now check for updates daily and prompt you if needed."
echo "You can control this through the NeoArch settings."
echo ""
echo "To check status: systemctl status neoarch-update.timer"
echo "To disable: sudo systemctl disable neoarch-update.timer"
echo "To re-enable: sudo systemctl enable neoarch-update.timer"
