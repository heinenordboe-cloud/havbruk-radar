#!/bin/bash
# Installerer AIS-lytterne på kystvakt-1 slik de ble satt opp 28.10.2026.
# Kjøres som root etter herding.sh, fra en mappe med filene i kystvakt/:
#
#   scp kystvakt/{lytter.py,regnskap.py,hulljeger.py,kopi.py,rydd.py,utlevering.py,utlevering.pub,boks-ssh-config,*.service,*.timer,lyttere.sh} vakt@kystvakt:/tmp/kv/
#   ssh vakt@kystvakt 'cd /tmp/kv && sudo bash lyttere.sh'
#
# Kan kjøres flere ganger. Nøkkelfila til BarentsWatch lages IKKE her:
# den skriver Heine selv, så hemmeligheten aldri går gjennom en annen
# maskin (se MALING-AIS, tillegget 28.10.2026).
#
# Én systembruker per kilde, ingen av dem med sudo eller skall:
#   ais       BarentsWatch, eier /srv/ais og nøkkelfila
#   ais5632   Kystverkets 5632, eier /srv/ais5632
#   utlevering  GitHubs lesetilgang: én nøkkel, tvungen kommando
#             (utlevering.py), ingen filer den eier. Skallet er /bin/sh
#             fordi sshd kjører den tvungne kommandoen gjennom det.
#
# Storage Box: `ais` har en egen nøkkel (/srv/ais/.ssh/boks_ed25519) og
# vertsnøkkelen festet. Nøkkelen lages her; den legges inn på boksen av
# Heine, som skriver underkontoens passord selv (MALING-AIS, 30.10.2026).
# Råfilene er lesbare for alle (åpne data), slik at hver kildes regnskap
# kan sammenligne med den andre. Nøkkelfila er det ikke.
set -euo pipefail

for u in ais ais5632; do
  id "$u" >/dev/null 2>&1 || useradd --system --home-dir "/srv/$u" --shell /usr/sbin/nologin "$u"
done

install -d -m 755 -o ais -g ais /srv/ais /srv/ais/bw /srv/ais/klokke
install -d -m 755 -o ais5632 -g ais5632 /srv/ais5632 /srv/ais5632/raa
if [ -f /etc/kystvakt/barentswatch-ais.env ]; then
  chown ais:ais /etc/kystvakt/barentswatch-ais.env
  chmod 400 /etc/kystvakt/barentswatch-ais.env
fi

install -d -m 755 -o ais -g ais /srv/ais/kopi
install -d -m 700 -o ais -g ais /srv/ais/.ssh
[ -f /srv/ais/.ssh/boks_ed25519 ] || \
  runuser -u ais -- ssh-keygen -q -t ed25519 -N "" -C "ais@kystvakt-1 boks" -f /srv/ais/.ssh/boks_ed25519
[ -f boks-ssh-config ] && install -m 600 -o ais -g ais boks-ssh-config /srv/ais/.ssh/config
# Hentet 30.10.2026 fra kystvakt-1 og fra en maskin utenfor Hetzner; lik.
echo "[u705336.your-storagebox.de]:23 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIICf9svRenC/PLKIL9nk6K/pxQgoiFC41wTNvoIncOxs" \
  > /srv/ais/.ssh/known_hosts
chown ais:ais /srv/ais/.ssh/known_hosts

id utlevering >/dev/null 2>&1 || useradd --system --home-dir /var/lib/utlevering --shell /bin/sh utlevering
# Eid av root: brukeren kan ikke endre sin egen nøkkel eller kommando.
install -d -m 755 -o root -g root /var/lib/utlevering /var/lib/utlevering/.ssh
printf 'restrict,command="/usr/bin/python3 /opt/kystvakt/utlevering.py" %s\n' "$(cat utlevering.pub)" \
  > /var/lib/utlevering/.ssh/authorized_keys
chmod 644 /var/lib/utlevering/.ssh/authorized_keys
sed -i 's/^AllowUsers vakt$/AllowUsers vakt utlevering/' /etc/ssh/sshd_config.d/00-kystvakt.conf
sshd -t && systemctl reload ssh

# Lytterne startes bare på nytt når lytteren selv eller unit-filene deres
# er endret. En omstart koster sekunder av strømmen og deler timen i .2,
# og en ny kopi- eller ryddejobb er ingen grunn til det.
start_paa_nytt=nei
for f in lytter.py:/opt/kystvakt ais-bw.service:/etc/systemd/system ais-5632.service:/etc/systemd/system; do
  cmp -s "${f%%:*}" "${f#*:}/${f%%:*}" || start_paa_nytt=ja
done

install -d -m 755 /opt/kystvakt
install -m 644 lytter.py regnskap.py kopi.py rydd.py utlevering.py /opt/kystvakt/
[ -f hulljeger.py ] && install -m 644 hulljeger.py /opt/kystvakt/

for f in *.service *.timer; do
  [ "$f" = ais-lytter.service ] && continue  # 5631: stoppet av Heine 28.10
  install -m 644 "$f" /etc/systemd/system/
done
systemctl daemon-reload

systemctl enable --now ais-klokke.timer ais-regnskap-bw.timer ais-regnskap-5632.timer ais-kopi.timer ais-rydd.timer
[ -f /etc/systemd/system/ais-hulljeger.timer ] && systemctl enable --now ais-hulljeger.timer
systemctl enable ais-bw.service ais-5632.service
if [ "$start_paa_nytt" = ja ]; then
  systemctl restart ais-bw.service ais-5632.service
else
  echo "lytter.py og unit-filene er uendret; lytterne kjører videre"
fi
systemctl --no-pager --lines=0 status ais-bw.service ais-5632.service
