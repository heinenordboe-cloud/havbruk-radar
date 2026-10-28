#!/bin/bash
# Installerer AIS-lytterne på kystvakt-1 slik de ble satt opp 28.10.2026.
# Kjøres som root etter herding.sh, fra en mappe med filene i kystvakt/:
#
#   scp kystvakt/{lytter.py,regnskap.py,hulljeger.py,*.service,*.timer,lyttere.sh} vakt@kystvakt:/tmp/kv/
#   ssh vakt@kystvakt 'cd /tmp/kv && sudo bash lyttere.sh'
#
# Kan kjøres flere ganger. Nøkkelfila til BarentsWatch lages IKKE her:
# den skriver Heine selv, så hemmeligheten aldri går gjennom en annen
# maskin (se MALING-AIS, tillegget 28.10.2026).
#
# Én systembruker per kilde, ingen av dem med sudo eller skall:
#   ais       BarentsWatch, eier /srv/ais og nøkkelfila
#   ais5632   Kystverkets 5632, eier /srv/ais5632
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

install -d -m 755 /opt/kystvakt
install -m 644 lytter.py regnskap.py /opt/kystvakt/
[ -f hulljeger.py ] && install -m 644 hulljeger.py /opt/kystvakt/

for f in *.service *.timer; do
  [ "$f" = ais-lytter.service ] && continue  # 5631: stoppet av Heine 28.10
  install -m 644 "$f" /etc/systemd/system/
done
systemctl daemon-reload

systemctl enable --now ais-klokke.timer ais-regnskap-bw.timer ais-regnskap-5632.timer
[ -f /etc/systemd/system/ais-hulljeger.timer ] && systemctl enable --now ais-hulljeger.timer
systemctl enable ais-bw.service ais-5632.service
systemctl restart ais-bw.service ais-5632.service
systemctl --no-pager --lines=0 status ais-bw.service ais-5632.service
