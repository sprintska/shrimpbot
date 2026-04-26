#!/bin/sh
# Run once on a fresh deployment to wire up symlinks.
# Assumes the repo is cloned at /opt/shrimpbot.

set -e

REPO=/opt/shrimpbot

ln -sf "$REPO/deploy/shrimpbot.service"     /etc/systemd/system/shrimpbot.service
ln -sf "$REPO/deploy/shrimpbot-api.service" /etc/systemd/system/shrimpbot-api.service
ln -sf "$REPO/deploy/update"                /usr/sbin/update

systemctl daemon-reload
echo "Symlinks created. Run 'systemctl enable shrimpbot shrimpbot-api' if this is a fresh install."
