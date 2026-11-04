"""Ingen prøve hoppes over uten at grunnen står i prøven (økt 3c, punkt 1e).

En prøve som hoppes over, er grønn i rapporten og prøver ingenting. Det er
greit når grunnen er ekte og står der den som leser prøven, ser den: et
verktøy som bare finnes på én maskin, et bygg som må lages først. Det er
ikke greit når den er stum: `importorskip` uten `reason` sier bare
«could not import», og det ser likt ut om modulen mangler med vilje eller
ved en feil.

Prøven leser hver testfil som Python (ast) og krever en grunn i hvert
`pytest.skip`, `pytest.importorskip`, `pytest.mark.skip` og
`pytest.mark.skipif`.

MÅLT 04.11.2026: 156 prøver hoppes over lokalt og 158 i Actions, alle med
grunn. 156 trenger et bygget nettsted (HAVBRUK_NETTSTED) og kjøres i dag
verken i Actions eller i porten; mot porten sitt bygg samme dag var 3 av
515 røde. De to som bare hoppes over i Actions, trenger sandbox-exec
(macOS).
"""
import ast
from pathlib import Path

TESTER = Path(__file__).resolve().parent


def _navn(node: ast.AST) -> str:
    return ast.unparse(node.func) if isinstance(node, ast.Call) else ast.unparse(node)


def _grunn(kall: ast.Call, posisjon: int) -> bool:
    return (any(k.arg == "reason" for k in kall.keywords)
            or len(kall.args) > posisjon)


def stumme(kilde: str, fil: str) -> list[str]:
    ut = []
    for node in ast.walk(ast.parse(kilde)):
        if isinstance(node, ast.Call):
            n = _navn(node)
            if n == "pytest.skip" and not _grunn(node, 0):
                ut.append(f"{fil}:{node.lineno} pytest.skip uten grunn")
            elif n == "pytest.importorskip" and not any(k.arg == "reason" for k in node.keywords):
                ut.append(f"{fil}:{node.lineno} importorskip uten reason=")
            elif n in ("pytest.mark.skipif", "pytest.mark.skip") and not any(
                    k.arg == "reason" for k in node.keywords) and not (
                    n == "pytest.mark.skip" and node.args):
                ut.append(f"{fil}:{node.lineno} {n} uten reason=")
        # Som dekoratør uten kall: `@pytest.mark.skip`.
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            for d in node.decorator_list:
                if not isinstance(d, ast.Call) and ast.unparse(d) in (
                        "pytest.mark.skip", "pytest.mark.skipif"):
                    ut.append(f"{fil}:{d.lineno} {ast.unparse(d)} uten grunn")
    return ut


def test_ingen_proeve_hoppes_over_uten_grunn():
    funn = []
    for p in sorted(TESTER.glob("test_*.py")):
        funn += stumme(p.read_text(encoding="utf-8"), p.name)
    assert not funn, "Hopper over uten å si hvorfor:\n  " + "\n  ".join(funn)


def test_kontrollen_ser_det_den_skal():
    assert stumme('import pytest\npytest.importorskip("x")\n', "a")
    assert stumme("import pytest\npytest.skip()\n", "a")
    assert stumme("import pytest\n@pytest.mark.skip\ndef test_x(): pass\n", "a")
    assert stumme("import pytest\n@pytest.mark.skipif(True)\ndef test_x(): pass\n", "a")
    assert not stumme('import pytest\npytest.importorskip("x", reason="y")\n'
                      'pytest.skip("z")\n'
                      '@pytest.mark.skipif(True, reason="w")\ndef test_x(): pass\n', "a")
