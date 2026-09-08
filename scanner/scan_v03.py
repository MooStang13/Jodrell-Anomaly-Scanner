import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from profile_io import download_profile, parse_ascii_profile
from science import distance, frequency_distance, normalise, percentile, robust_z

SAME_FREQ_TOL = 0.015       # 1.5% frequency difference
NEAR_FREQ_LOG_GAP = 0.12

def load_profiles(df, cache_dir, timeout):
    profiles={}; failures=[]
    total=len(df)
    for n,(idx,row) in enumerate(df.iterrows(),1):
        try:
            p=download_profile(row.url, cache_dir=cache_dir, timeout=timeout)
            profiles[idx]=parse_ascii_profile(p)
        except Exception as exc:
            failures.append((idx,str(exc)))
        if n==1 or n%25==0 or n==total:
            print(f'Profiles: {n}/{total} | usable={len(profiles)} | failed={len(failures)}')
    return profiles, failures

def pair_stats(target_idx, group, profiles):
    target=group.loc[target_idx]
    others=group.drop(index=target_idx)
    same=others[others.frequency_mhz.apply(lambda f: abs(float(f)-float(target.frequency_mhz))/max(float(target.frequency_mhz),1e-9) <= SAME_FREQ_TOL)]
    same=same[same.index.isin(profiles)]
    near=others[others.index.isin(profiles)].copy()
    near['gap']=near.frequency_mhz.apply(lambda f: frequency_distance(target.frequency_mhz,f))
    near=near[near.gap<=NEAR_FREQ_LOG_GAP].sort_values('gap')
    if not same.empty:
        peers=same.copy()
        mode='same-frequency'
    else:
        peers=near.head(4).copy()
        mode='near-frequency'
    if peers.empty: return None
    ds=[]
    for pidx,prow in peers.iterrows():
        d,aligned,shift,corr=distance(profiles[target_idx],profiles[pidx])
        ds.append((d,pidx,aligned,shift,corr,float(prow.frequency_mhz),frequency_distance(target.frequency_mhz,prow.frequency_mhz)))
    # Robust median of pair distances. This avoids one bad peer dominating.
    vals=np.array([x[0] for x in ds])
    morph=float(np.median(vals))
    best=max(ds,key=lambda x:x[0])
    return {'mode':mode,'distances':ds,'morph':morph,'max_dist':float(best[0]),'best':best,
            'same_count':len(same),'near_count':len(near)}

def dataset_effect_flags(df, pair_rows):
    tmp=pd.DataFrame(pair_rows)
    if tmp.empty: return {}
    # Cohorts are citation + rounded frequency. A cohort is systematic if its
    # candidates have unusually high mismatch against their own pulsar peers.
    tmp['freq_bucket']=tmp.frequency_mhz.round(0)
    cohort=tmp.groupby(['citation','freq_bucket']).morphology_distance.agg(['count','median'])
    global_med=tmp.morphology_distance.median()
    global_mad=np.median(np.abs(tmp.morphology_distance-global_med))+1e-9
    flags={}
    for key,row in cohort.iterrows():
        flags[key]=bool(row['count']>=8 and row['median'] > global_med + 2.5*global_mad)
    return flags

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--min-observations',type=int,default=3)
    ap.add_argument('--top',type=int,default=40)
    ap.add_argument('--cache-dir',default='data/cache')
    ap.add_argument('--timeout',type=int,default=30)
    args=ap.parse_args()

    df=pd.read_csv(args.csv)
    required={'pulsar','frequency_mhz','url'}
    missing=required-set(df.columns)
    if missing: raise SystemExit(f'Missing columns: {sorted(missing)}')
    df=df.dropna(subset=list(required)).copy()
    counts=df.groupby('pulsar')['pulsar'].transform('size')
    df=df[counts>=args.min_observations].copy()
    print(f'Eligible rows: {len(df)} from {df.pulsar.nunique()} pulsars')

    profiles,failed=load_profiles(df,args.cache_dir,args.timeout)
    df=df.loc[df.index.intersection(profiles)].copy()
    print(f'Usable profiles: {len(df)} | failed: {len(failed)}')

    rows=[]; comparison_map={}
    for pulsar,group in df.groupby('pulsar'):
        for idx,row in group.iterrows():
            s=pair_stats(idx,group,profiles)
            if not s: continue
            ds=s['distances']
            peer_d=np.array([x[0] for x in ds])
            z=robust_z(peer_d,s['morph'])
            peer_count=len(ds)
            near_count=sum(x[6]<=NEAR_FREQ_LOG_GAP for x in ds)
            freq_gap=min(x[6] for x in ds)
            confidence=30 + 15*min(peer_count,4)
            if s['mode']=='same-frequency': confidence+=30
            else: confidence-=25
            if freq_gap>0.05: confidence-=10
            confidence=float(np.clip(confidence,10,100))

            reason=[]
            if s['mode']=='same-frequency': reason.append(f'{peer_count} same-frequency peer(s)')
            else: reason.append(f'{peer_count} near-frequency peer(s); no same-frequency peer')
            if s['morph']>=0.55: reason.append('strong profile-shape departure')
            elif s['morph']>=0.30: reason.append('moderate profile-shape departure')
            elif s['morph']>=0.15: reason.append('subtle profile-shape departure')
            if len(ds)>=3: reason.append('robust median across multiple peers')
            if z>=3: reason.append('outlier within its peer group')

            best=s['best']
            comparison_map[idx]=s
            rows.append({
                'source_index':idx,'pulsar':pulsar,'frequency_mhz':float(row.frequency_mhz),
                'citation':row.get('citation',''),'stokes':row.get('stokes',''),'url':row.url,
                'comparison_mode':s['mode'],'morphology_distance':s['morph'],
                'max_peer_distance':s['max_dist'],'robust_z':z,
                'peer_count':peer_count,'same_frequency_peer_count':s['same_count'],
                'near_frequency_peer_count':near_count,'nearest_frequency_log_gap':freq_gap,
                'confidence':confidence,'reason':'; '.join(reason)
            })
    out=pd.DataFrame(rows)
    if out.empty: raise SystemExit('No comparable profiles found.')

    flags=dataset_effect_flags(df,out.to_dict('records'))
    out['systematic_dataset_flag']=[
        flags.get((r.citation,round(r.frequency_mhz,0)),False) for _,r in out.iterrows()
    ]
    # Score is deliberately conservative: same-frequency, robust outliers win.
    base=100*np.clip(out['robust_z']/6,0,1)
    shape=100*np.clip(out['morphology_distance']/0.65,0,1)
    out['candidate_score']=np.clip(0.65*base+0.35*shape,0,100)
    out.loc[out['comparison_mode']=='near-frequency','candidate_score']*=0.55
    out.loc[out['systematic_dataset_flag'],'candidate_score']*=0.35
    out=out.sort_values(['candidate_score','confidence'],ascending=False).reset_index(drop=True)
    out.insert(0,'rank',np.arange(1,len(out)+1))

    Path('results').mkdir(exist_ok=True); Path('plots').mkdir(exist_ok=True)
    out.to_csv('results/candidates_v03.csv',index=False)
    if failed:
        pd.DataFrame(failed,columns=['source_index','error']).to_csv('results/download_failures.csv',index=False)

    # Detailed visual evidence for top candidates.
    for _,r in out.head(args.top).iterrows():
        idx=int(r.source_index); s=comparison_map[idx]
        target,_=normalise(profiles[idx])
        peers=s['distances']
        aligned=[x[2] for x in peers]
        template=np.median(np.vstack(aligned),axis=0)
        residual=target-template
        fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True)
        axs[0].plot(target,label='candidate')
        for j,x in enumerate(aligned): axs[0].plot(x,alpha=.25,label='peer' if j==0 else None)
        axs[0].plot(template,linewidth=2,label='peer median')
        axs[0].set_ylabel('Normalised intensity'); axs[0].legend()
        axs[1].plot(residual)
        axs[1].axhline(0,linewidth=1)
        axs[1].set_ylabel('Candidate − median')
        axs[2].plot(np.abs(residual))
        axs[2].set_ylabel('|residual|'); axs[2].set_xlabel('Pulse phase bin')
        title=(f"Rank {int(r['rank'])} | {r.pulsar} | {r.frequency_mhz:.1f} MHz | "
               f"score {r.candidate_score:.1f} | confidence {r.confidence:.0f}%")
        fig.suptitle(title)
        fig.tight_layout(rect=[0,0,1,.96])
        fig.savefig(f"plots/{int(r['rank']):03d}_{r.pulsar.replace('+','p')}.png",dpi=150)
        plt.close(fig)

    print('\nSCAN COMPLETE')
    print(f'Candidates ranked: {len(out)}')
    print('results/candidates_v03.csv')
    print('Run: python review_v03.py results/candidates_v03.csv')
    print('\nTop 10:')
    for _,r in out.head(10).iterrows():
        print(f"{int(r['rank']):2d}. {r.pulsar:14s} {r.frequency_mhz:9.2f} MHz score={r.candidate_score:5.1f} conf={r.confidence:3.0f}% [{r.comparison_mode}] {r.reason}")

if __name__=='__main__': main()
