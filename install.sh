#! /usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# 1. Copy the blank background file
mkdir -p $HOME/.jpframe
cp $DIR/blank.jpg $HOME/.jpframe

# 2. Generate the unit file
mkdir -p $HOME/.config/systemd/user
unit_file="$HOME/.config/systemd/user/jacob-pic-frame.service"
touch ${unit_file}

cat <<EOF >${unit_file}
[Unit]
Description=The slideshow of pictures and video clips.

[Service]
Type=simple
StandardOutput=journal
ExecStart=python3 ${DIR}/app/run.py

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload

echo "Installed. Now you can use 'systemct --user start jacob-pic-frame.service' to start it.'"
