from pathlib import Path
from urllib.parse import urlparse
import hashlib, re, requests
import numpy as np

def cache_name(url):
    parsed=urlparse(str(url))
    tail=Path(parsed.path).name or 'profile.txt'
    digest=hashlib.sha1(str(url).encode('utf-8')).hexdigest()[:12]
    return f"{digest}_{tail}"

def download_profile(url, cache_dir='data/cache', timeout=30):
    cache=Path(cache_dir); cache.mkdir(parents=True,exist_ok=True)
    target=cache/cache_name(url)
    if target.exists() and target.stat().st_size>0: return target
    urls=[str(url)]
    if str(url).startswith('http://'): urls.insert(0,'https://'+str(url)[7:])
    last=None
    for u in urls:
        try:
            r=requests.get(u,timeout=timeout,headers={'User-Agent':'Jodrell-Anomaly-Scanner/0.3'})
            r.raise_for_status(); target.write_bytes(r.content); return target
        except Exception as exc: last=exc
    raise RuntimeError(f'Could not download {url}: {last}')

def parse_ascii_profile(path):
    rows=[]
    for line in Path(path).read_text(encoding='utf-8',errors='ignore').splitlines():
        line=line.strip()
        if not line or line.startswith(('#','!','%',';')): continue
        vals=[]
        for token in re.split(r'[\s,]+',line):
            try: vals.append(float(token))
            except ValueError: pass
        if vals: rows.append(vals)
    if len(rows)<16: raise ValueError(f'Only {len(rows)} numeric rows found')
    width=max(map(len,rows)); cols=[]
    for j in range(width):
        c=np.array([r[j] for r in rows if len(r)>j and np.isfinite(r[j])],float)
        if len(c)>=16: cols.append((j,c))
    viable=[]
    for j,c in cols:
        if np.std(c)<=1e-15: continue
        dif=np.diff(c)
        monotonic=(np.mean(dif>=0)>0.98 or np.mean(dif<=0)>0.98)
        score=np.std(c)/(abs(np.median(c))+np.std(c)+1e-12)
        if monotonic: score*=0.05
        viable.append((score,j,c))
    if not viable: raise ValueError('No varying intensity-like column')
    viable.sort(key=lambda x:x[0],reverse=True)
    return viable[0][2]
