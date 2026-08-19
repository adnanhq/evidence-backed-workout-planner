"""Build the human annotation task: one self-contained local HTML page.

Two things need a person rather than a model:

  citation support   25 (exercise, study) pairs, judged on the same rubric the
                     model used, so agreement can be measured with Cohen's kappa
  tier promotion     15 cases where reading the abstract body promoted a study's
                     evidence tier, to separate "the heuristic is wrong" from
                     "MEDLINE indexing is incomplete"

The model's verdicts are deliberately not shown: an annotator who can see them is
not an independent rater. Sampling is seeded, so the same 40 items are produced
every time.

    ./.venv/bin/python -m research.s3d_build_annotation
    open research/annotate/index.html
"""
from __future__ import annotations

import json
import random
from typing import Any

from research.common import ANNOTATE_DIR, SEED, banner, read_results, write_results

N_CITATION = 25
N_TIER = 15


def build_items() -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    alias_pairs = read_results("s3_judgment_sample")["pairs"]
    semantic_pairs = read_results("s3b_semantic_pairs")["pairs"]

    # Sample across both mechanisms so agreement can be checked on each.
    # Half the citation items from each attachment mechanism: the human labels are
    # the only judged evidence that covers both, so they must be able to compare them.
    by_group: dict[str, list[dict[str, Any]]] = {"semantic_fallback": list(semantic_pairs)}
    for pair in alias_pairs:
        by_group.setdefault("alias_%s" % pair["stratum"], []).append(pair)

    quotas = {"semantic_fallback": N_CITATION // 2}
    alias_groups = [g for g in by_group if g.startswith("alias_")]
    for index, group in enumerate(sorted(alias_groups)):
        share = N_CITATION - N_CITATION // 2
        quotas[group] = share // len(alias_groups) + (1 if index < share % len(alias_groups) else 0)

    citation_items: list[dict[str, Any]] = []
    for group in sorted(by_group):
        pool = sorted(by_group[group], key=lambda p: p["pair_id"])
        rng.shuffle(pool)
        for pair in pool[:quotas[group]]:
            citation_items.append({
                "kind": "citation",
                "id": pair["pair_id"],
                "group": group,
                "exercise_name": pair["exercise_name"],
                "muscles": ", ".join(pair["primary_muscles"]),
                "equipment": pair.get("equipment", ""),
                "matched_alias": pair.get("matched_alias", ""),
                "pmid": pair["pmid"],
                "title": pair["study_title"],
                "abstract": (pair.get("study_abstract") or "(no abstract available)")[:4000],
                "url": pair["url"],
            })
    citation_items = citation_items[:N_CITATION]

    tier_items = [
        {
            "kind": "tier",
            "id": "tier:%s" % item["pmid"],
            "promotion": item["promotion"],
            "pmid": item["pmid"],
            "title": item["title"],
            "journal": item.get("journal", ""),
            "year": item.get("publication_year"),
            "publication_types": ", ".join(item["publication_types"]),
            "abstract": (item.get("abstract") or "(no abstract available)")[:4000],
            "url": item["url"],
        }
        for item in read_results("s1_tier_audit")["disagreement_sample"][:N_TIER]
    ]
    return citation_items + tier_items


PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Grounding audit &mdash; annotation</title>
<style>
:root { --bg:#fbfaf8; --card:#fff; --ink:#1a1a1a; --muted:#6b6b6b; --line:#e5e2dc;
        --accent:#0f766e; --warn:#b45309; }
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 -apple-system,
       BlinkMacSystemFont,"Segoe UI",sans-serif; }
header { position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line);
         padding:14px 24px; display:flex; gap:18px; align-items:center; z-index:5 }
h1 { font-size:15px; margin:0; font-weight:600; letter-spacing:.01em }
.bar { flex:1; height:6px; background:var(--line); border-radius:3px; overflow:hidden }
.fill { height:100%; background:var(--accent); width:0%; transition:width .2s }
main { max-width:820px; margin:0 auto; padding:26px 24px 120px }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:22px; margin-bottom:20px }
.tag { display:inline-block; font-size:11px; text-transform:uppercase; letter-spacing:.08em;
       color:var(--muted); border:1px solid var(--line); border-radius:99px; padding:2px 9px;
       margin-right:6px }
.ex { font-size:19px; font-weight:600; margin:10px 0 2px }
.meta { color:var(--muted); font-size:13px }
.abs { margin-top:14px; padding:14px; background:#f7f5f2; border-radius:7px; font-size:13.5px;
       max-height:260px; overflow:auto; white-space:pre-wrap }
.q { margin-top:18px; padding-top:16px; border-top:1px solid var(--line) }
.q p { margin:0 0 9px; font-weight:500 }
.hint { font-weight:400; color:var(--muted); font-size:13px }
button.opt { font:inherit; padding:7px 20px; margin-right:8px; border:1px solid var(--line);
             background:#fff; border-radius:7px; cursor:pointer }
button.opt.on { background:var(--accent); color:#fff; border-color:var(--accent) }
footer { position:fixed; bottom:0; left:0; right:0; background:#fff; border-top:1px solid var(--line);
         padding:12px 24px; display:flex; gap:12px; align-items:center; justify-content:center }
button.go { font:inherit; padding:9px 22px; border-radius:8px; border:1px solid var(--accent);
            background:var(--accent); color:#fff; cursor:pointer; font-weight:500 }
button.ghost { background:#fff; color:var(--ink); border-color:var(--line) }
a { color:var(--accent) }
.done { text-align:center; padding:60px 20px }
</style>
<header>
  <h1>Grounding audit &mdash; annotation</h1>
  <div class="bar"><div class="fill" id="fill"></div></div>
  <span class="meta" id="count"></span>
</header>
<main id="main"></main>
<footer>
  <button class="go ghost" id="prev">&larr; Back</button>
  <button class="go" id="next">Next &rarr;</button>
  <button class="go ghost" id="export">Export answers</button>
  <span class="meta" id="status"></span>
</footer>
<script>
const ITEMS = __ITEMS__;
const KEY = "grounding-audit-annotations-v1";
let answers = JSON.parse(localStorage.getItem(KEY) || "{}");
let i = 0;

const CIT_Q = [
  ["movement_involved", "1. Did participants actually <b>perform this movement</b> (or a clearly equivalent variant)?",
   "Watch for names that are clinical assessment tests rather than exercises, and for passing mentions."],
  ["goal_supported", "2. Does the study report a <b>hypertrophy or strength outcome</b> bearing on this exercise?", ""],
  ["variant_exact", "3. Did the study use <b>this specific variant</b> &mdash; same equipment and body position?", ""],
];

function save() { localStorage.setItem(KEY, JSON.stringify(answers)); render(); }

function render() {
  const item = ITEMS[i];
  const a = answers[item.id] || {};
  const qs = item.kind === "citation" ? CIT_Q
    : [["promotion_justified", "Was promoting this study to <b>" + (item.promotion||"").split("->")[1].trim()
        + "</b> justified by the title and abstract?",
        "MEDLINE tags it as " + (item.publication_types || "none") +
        ". Answer yes if the paper really is that design and MEDLINE simply did not tag it; " +
        "answer no if the phrase appears only because the paper discusses or cites that kind of study."]]];

  document.getElementById("main").innerHTML = `
    <div class="card">
      <span class="tag">${item.kind === "citation" ? "citation support" : "tier promotion"}</span>
      <span class="tag">${item.kind === "citation" ? item.group : item.promotion}</span>
      ${item.kind === "citation"
        ? `<div class="ex">${item.exercise_name}</div>
           <div class="meta">${item.muscles}${item.equipment ? " &middot; " + item.equipment : ""}
           ${item.matched_alias ? ' &middot; linked by the phrase "<b>' + item.matched_alias + '</b>"' : " &middot; linked by meaning, not by name"}</div>
           <div class="q" style="border:0;padding-top:14px"><p style="font-weight:400">Cited study:</p></div>`
        : ""}
      <div class="ex" style="font-size:16px">${item.title}</div>
      <div class="meta">PMID ${item.pmid}${item.year ? " &middot; " + item.year : ""}
        ${item.journal ? " &middot; " + item.journal : ""} &middot;
        <a href="${item.url}" target="_blank">open on PubMed</a></div>
      <div class="abs">${item.abstract}</div>
      ${qs.map(([k, label, hint]) => `
        <div class="q"><p>${label}${hint ? '<br><span class="hint">' + hint + "</span>" : ""}</p>
          <button class="opt ${a[k]==="yes"?"on":""}" onclick="pick('${item.id}','${k}','yes')">Yes</button>
          <button class="opt ${a[k]==="no"?"on":""}" onclick="pick('${item.id}','${k}','no')">No</button>
        </div>`).join("")}
    </div>`;

  const done = ITEMS.filter(x => {
    const ans = answers[x.id] || {};
    const need = x.kind === "citation" ? CIT_Q.map(q=>q[0]) : ["promotion_justified"];
    return need.every(k => ans[k]);
  }).length;
  document.getElementById("fill").style.width = (100 * done / ITEMS.length) + "%";
  document.getElementById("count").textContent = `${i + 1} / ${ITEMS.length} · ${done} complete`;
}

function pick(id, key, value) {
  answers[id] = Object.assign({}, answers[id], {[key]: value});
  save();
}
document.getElementById("next").onclick = () => { i = Math.min(ITEMS.length - 1, i + 1); render(); };
document.getElementById("prev").onclick = () => { i = Math.max(0, i - 1); render(); };
document.getElementById("export").onclick = () => {
  const text = JSON.stringify(answers, null, 2);
  let note = "";
  try {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], {type: "application/json"}));
    a.download = "human_annotations.json";
    a.click();
    note = "downloaded";
  } catch (e) { note = "download blocked"; }
  try { navigator.clipboard.writeText(text); note += " · copied"; } catch (e) {}
  // Always render it too: whichever of the above failed, the text is still here.
  const box = document.createElement("div");
  box.className = "card";
  box.innerHTML = '<p style="font-weight:500;margin:0 0 8px">Your answers &mdash; save this as '
    + '<code>research/annotate/human_annotations.json</code></p>'
    + '<textarea style="width:100%;height:260px;font:12px ui-monospace,monospace;'
    + 'border:1px solid var(--line);border-radius:6px;padding:10px" readonly></textarea>';
  box.querySelector("textarea").value = text;
  const main = document.getElementById("main");
  main.insertBefore(box, main.firstChild);
  box.querySelector("textarea").select();
  document.getElementById("status").textContent = note + " · also shown above";
};
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight") document.getElementById("next").click();
  if (e.key === "ArrowLeft") document.getElementById("prev").click();
});
render();
</script>
"""


def main() -> None:
    items = build_items()
    banner("annotation task")
    print("citation-support items : %d" % sum(1 for i in items if i["kind"] == "citation"))
    print("tier-promotion items   : %d" % sum(1 for i in items if i["kind"] == "tier"))
    page = PAGE.replace("__ITEMS__", json.dumps(items))
    (ANNOTATE_DIR / "index.html").write_text(page)
    write_results("s3d_annotation_items", {"n_items": len(items), "seed": SEED, "items": items})
    print("\nopen this file in a browser and work through it:")
    print("   %s" % (ANNOTATE_DIR / "index.html"))
    print("then save the exported file to:")
    print("   %s" % (ANNOTATE_DIR / "human_annotations.json"))


if __name__ == "__main__":
    main()
