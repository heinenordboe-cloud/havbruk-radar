#!/bin/bash
# Herdingen av kystvakt-1 slik den ble kjørt 28.10.2026, samlet her så en
# ny server kan settes opp likt. Kjøres som root ÉN gang på en fersk
# Ubuntu 26.04 (Hetzner CPX). Test `ssh vakt@<ip> sudo -n true` FØR
# sshd-delen stenger root; skriptet gjør det ikke for deg.
#
#   scp herding.sh root@<ip>: && ssh root@<ip> 'bash herding.sh del1'
#   ssh -i ~/.ssh/kystvakt_ed25519 vakt@<ip> 'sudo -n true' && \
#   ssh root@<ip> 'bash herding.sh del2'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

del1() {
  hostnamectl set-hostname kystvakt-1
  # cloud-init skriver ellers /etc/hosts og vertsnavnet om ved omstart.
  printf 'preserve_hostname: true\nmanage_etc_hosts: false\n' \
    > /etc/cloud/cloud.cfg.d/99-kystvakt.cfg
  sed -i 's/^127\.0\.1\.1 .*/127.0.1.1 kystvakt-1 kystvakt-1/' /etc/hosts
  # All tid i repoene er UTC (CLAUDE.md 1b-7).
  timedatectl set-timezone Etc/UTC

  apt-get update -q
  apt-get -y -q -o Dpkg::Options::=--force-confold full-upgrade
  apt-get -y -q -o Dpkg::Options::=--force-confold install \
    ufw fail2ban unattended-upgrades chrony python3-venv python3-systemd zstd

  id vakt >/dev/null 2>&1 || adduser --disabled-password --gecos "" vakt
  usermod -aG sudo vakt
  install -d -m 700 -o vakt -g vakt /home/vakt/.ssh
  install -m 600 -o vakt -g vakt /root/.ssh/authorized_keys /home/vakt/.ssh/authorized_keys
  # Ingen passord finnes på serveren, så sudo må være uten.
  echo "vakt ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vakt
  chmod 440 /etc/sudoers.d/vakt
  visudo -cf /etc/sudoers.d/vakt
}

del2() {
  # 00- fordi sshd bruker FØRSTE verdi den leser, og cloud-init legger
  # sine egne filer i samme mappe.
  cat > /etc/ssh/sshd_config.d/00-kystvakt.conf <<C
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AllowUsers vakt
C
  sshd -t
  systemctl reload ssh

  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  ufw --force enable

  cat > /etc/fail2ban/jail.local <<C
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
C
  systemctl enable --now fail2ban
  systemctl restart fail2ban

  cat > /etc/apt/apt.conf.d/20auto-upgrades <<C
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
C
  systemctl enable --now unattended-upgrades

  if ! swapon --show | grep -q /swapfile; then
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-kystvakt.conf
  sysctl -p /etc/sysctl.d/99-kystvakt.conf

  systemctl enable --now chrony
}

"$@"
