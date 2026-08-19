"""Assemble the pitch page with figures embedded as data URIs."""
import base64, json, pathlib, sys
sys.path.insert(0, "/Users/adnan/cse-499")
from research.common import read_results

FIG = pathlib.Path("/Users/adnan/cse-499/research/figures")
OUT = pathlib.Path("/Users/adnan/cse-499/research/paper/page/retrieval-is-not-grounding.html")

def img(name):
    data = base64.b64encode((FIG / (name + ".png")).read_bytes()).decode()
    return "data:image/png;base64," + data

figs = {n: img(n) for n in (
    "f1_tier_grading", "f2_retrieval_quality", "f3_threshold_calibration",
    "f4_attribution_coverage", "f5_citation_specificity", "f6_confidence_calibration")}

s4 = read_results("s4_conformance")
claims = s4["claims"]

def chip(v):
    return {True: ("conforms", "ok"), False: ("diverges", "bad"), None: ("qualified", "mid")}[v]

claim_rows = "\n".join(
    '<tr><td>%s</td><td class="num">%s</td><td class="num">%s</td><td><span class="chip %s">%s</span></td></tr>'
    % (c["claim"][0].upper() + c["claim"][1:],
       str(c["published"])[:46], str(c["measured"])[:46],
       chip(c["conforms"])[1], chip(c["conforms"])[0])
    for c in claims)

html = pathlib.Path("/Users/adnan/cse-499/research/paper/page/template.html").read_text()
for key, uri in figs.items():
    html = html.replace("{{%s}}" % key, uri)
html = html.replace("{{claim_rows}}", claim_rows)
OUT.write_text(html)
print("wrote %s  (%.1f MB)" % (OUT, OUT.stat().st_size / 1048576))
