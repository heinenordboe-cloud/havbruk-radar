"""kystvakt/utlevering.py: status og lukkede manifester, ingenting annet."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kystvakt"))
import utlevering  # noqa: E402

sys.path.pop(0)

S = "a" * 64


def test_status_tomme_og_manglende_timer_og_lukkede_dogn(tmp_path, monkeypatch):
    monkeypatch.setattr(utlevering, "SRV", tmp_path)
    monkeypatch.setattr(utlevering, "tjenester", lambda: {"x.timer": {"tilstand": "active",
                                                                      "resultat": "success"}})
    naa = datetime(2026, 10, 30, 8, 30, tzinfo=timezone.utc)
    bw = tmp_path / "ais/bw"
    for dato in ("2026-10-29", "2026-10-30"):
        (bw / dato).mkdir(parents=True)
        (bw / dato / "SHA256SUMS").write_text(f"{S}  {dato}T00Z.txt.zst\n")
    # Siste ferdig regnede time kl. 08:30 er 05Z; vinduet er 29T06Z–30T05Z.
    for h in range(6, 24):
        (bw / "2026-10-29" / f"2026-10-29T{h:02}Z.regnskap.json").write_text('{"meldinger": 5}')
    for h in range(0, 6):
        m = 0 if h == 3 else 5
        u = 2 if h == 4 else 0
        (bw / "2026-10-30" / f"2026-10-30T{h:02}Z.regnskap.json").write_text(
            f'{{"meldinger": {m}, "uten_mmsi": {u}}}')
    (bw / "2026-10-29" / "2026-10-29T10Z.regnskap.json").unlink()
    eh = tmp_path / "ais/bw/etterhentet"
    for dato in ("2026-10-14", "2026-10-16"):
        (eh / dato).mkdir(parents=True)
        (eh / dato / "SHA256SUMS").write_text(f"{S}  x.etterhentet.jsonl.zst\n")
    (tmp_path / "ais/kopi").mkdir()
    (tmp_path / "ais/kopi/SIST_OK").write_text("2026-10-30T00:41:00Z\n")

    s = utlevering.status(naa)
    r = s["regnskap"]["bw"]
    assert r["timer"] == ["2026-10-29T06Z", "2026-10-30T05Z"]
    assert r["tomme"] == ["2026-10-30T03Z"] and r["mangler"] == ["2026-10-29T10Z"]
    # Linjetallene per time, for tilsynets grense på andelen uten MMSI.
    assert len(r["per_time"]) == 23, "alle med regnskap, ikke den som mangler"
    assert r["per_time"]["2026-10-30T04Z"] == {"meldinger": 5, "uten_mmsi": 2}
    assert r["per_time"]["2026-10-29T06Z"] == {"meldinger": 5, "uten_mmsi": 0}, \
        "et regnskap uten feltet teller null"
    assert r["per_time"]["2026-10-30T03Z"]["meldinger"] == 0
    assert len(s["regnskap"]["5632"]["mangler"]) == 24
    assert s["kopi_sist_ok"] == "2026-10-30T00:41:00Z"
    # Lytterens døgn er lukket når datoen er forbi; hulljegerens etter 15.
    assert [(m["kilde"], m["dato"]) for m in s["manifester"]] == [
        ("bw", "2026-10-29"), ("bw-etterhentet", "2026-10-14")]
    assert 0 <= s["disk"]["brukt_prosent"] <= 100
    assert s["python"] == ".".join(map(str, sys.version_info[:3]))
    assert s["tjenester"] == {"x.timer": {"tilstand": "active", "resultat": "success"}}
    assert s["gjenoppretting"] is None, "ingen prøve kjørt ennå"
    (tmp_path / "ais/kopi/GJENOPPRETTING.json").write_text('{"ok": true}')
    assert utlevering.status(naa)["gjenoppretting"] == {"ok": True}
    json.dumps(s)


LYTTERE = Path(__file__).resolve().parent.parent / "kystvakt" / "lyttere.sh"


def test_tjenestene_er_de_lyttere_sh_slaar_paa():
    """TJENESTER og `systemctl enable` i lyttere.sh er to lister over det
    samme. Slår skriptet på en enhet lista ikke har, ser tilsynet den
    aldri."""
    slaatt_paa = set()
    for linje in LYTTERE.read_text().splitlines():
        linje = linje.split("#")[0]
        if "systemctl enable" not in linje:
            continue
        ord_ = linje.split("systemctl enable", 1)[1].split()
        slaatt_paa |= {o for o in ord_ if o.endswith((".service", ".timer"))}
    assert slaatt_paa == set(utlevering.TJENESTER)


def test_tjenester_leser_systemd_og_timerens_tjeneste(monkeypatch):
    kall = []

    def run(cmd, **kw):
        kall.append(cmd)
        blokker = []
        for e in cmd[4:]:
            tilstand = "active" if e in utlevering.TJENESTER else "inactive"
            resultat = "exit-code" if e == "ais-rydd.service" else "success"
            blokker.append(f"Id={e}\nActiveState={tilstand}\nResult={resultat}")
        return subprocess.CompletedProcess(cmd, 0, "\n\n".join(blokker) + "\n", "")

    monkeypatch.setattr(utlevering.subprocess, "run", run)
    t = utlevering.tjenester()
    assert kall[0][:4] == ["systemctl", "show", "-p", "Id,ActiveState,Result"]
    assert set(t) == set(utlevering.TJENESTER) | {
        "ais-klokke.service", "ais-regnskap-bw.service", "ais-regnskap-5632.service",
        "ais-kopi.service", "ais-rydd.service", "ais-hulljeger.service",
        "ais-gjenopprett.service"}
    assert t["ais-bw.service"] == {"tilstand": "active", "resultat": "success"}
    assert t["ais-rydd.service"] == {"tilstand": "inactive", "resultat": "exit-code"}


def test_tjenester_uten_systemd_sier_ukjent_for_hver_enhet(monkeypatch):
    def run(cmd, **kw):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(utlevering.subprocess, "run", run)
    t = utlevering.tjenester()
    assert set(utlevering.TJENESTER) <= set(t)
    assert {v["tilstand"] for v in t.values()} == {"ukjent"}
    assert "FileNotFoundError" in t["ais-bw.service"]["resultat"]
