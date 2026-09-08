import argparse, base64, html, mimetypes, os, webbrowser
from pathlib import Path
import pandas as pd

def img_data(path):
    data=base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{data}"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('csv',nargs='?',default='results/candidates_v03.csv')
    ap.add_argument('--top',type=int,default=40)
    ap.add_argument('--no-browser',action='store_true')
    args=ap.parse_args()
    csv=Path(args.csv); df=pd.read_csv(csv).head(args.top)
    cards=[]
    for _,r in df.iterrows():
        rank=int(r['rank'])
        png=Path('plots')/f"{rank:03d}_{str(r.pulsar).replace('+','p')}.png"
        image=img_data(png) if png.exists() else ''
        cls='systematic' if bool(r.get('systematic_dataset_flag',False)) else ''
        cards.append(f'''
        <section class="card {cls}">
          <div class="head"><b>#{rank} {html.escape(str(r.pulsar))}</b>
          <span>{r.frequency_mhz:.1f} MHz</span><span>Score {r.candidate_score:.1f}</span>
          <span>Confidence {r.confidence:.0f}%</span></div>
          <p><b>Why flagged:</b> {html.escape(str(r.reason))}</p>
          <p><b>Measured:</b> morphology distance {r.morphology_distance:.3f},
             robust z {r.robust_z:.2f}, peers {int(r.peer_count)},
             same-frequency peers {int(r.same_frequency_peer_count)}.
             <b>Mode:</b> {html.escape(str(r.comparison_mode))}.</p>
          <img src="{image}" alt="candidate comparison plot">
          <details><summary>More data</summary>
          <pre>{html.escape(r.to_string())}</pre></details>
        </section>''')
    body=''.join(cards)
    out=csv.parent/'review_v03.html'
    out.write_text(f'''<!doctype html><html><head><meta charset="utf-8">
<title>Jodrell Anomaly Scanner v0.3 Review</title>
<style>
body{{font-family:Arial,sans-serif;background:#f2f2f2;margin:0;color:#222}}
main{{max-width:1200px;margin:auto;padding:24px}}
h1{{margin-bottom:4px}} .intro{{color:#555}}
.card{{background:white;border-radius:10px;padding:18px;margin:18px 0;box-shadow:0 2px 8px #0001}}
.card.systematic{{border-left:6px solid #777;opacity:.75}}
.head{{display:flex;gap:18px;flex-wrap:wrap;font-size:18px}}
.head span{{font-size:15px;color:#555}}
img{{width:100%;max-width:1100px;border:1px solid #ddd;margin-top:8px}}
summary{{cursor:pointer}}
pre{{white-space:pre-wrap}}
</style></head><body><main>
<h1>Jodrell Anomaly Scanner v0.3</h1>
<p class="intro">Human-review report. High score means unusual relative to comparable observations, not a discovery.</p>
{body}
</main></body></html>''',encoding='utf-8')
    print(f'Report written: {out}')
    if not args.no_browser: webbrowser.open(out.resolve().as_uri())

if __name__=='__main__': main()
