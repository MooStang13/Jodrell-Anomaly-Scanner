import numpy as np

N_BINS = 512

def resample(x, n=N_BINS):
    x=np.asarray(x,dtype=float)
    old=np.linspace(0,1,len(x),endpoint=False)
    new=np.linspace(0,1,n,endpoint=False)
    return np.interp(new,old,x)

def normalise(x):
    x=resample(x)
    cutoff=np.quantile(x,0.60)
    baseline=np.median(x[x<=cutoff]) if np.any(x<=cutoff) else np.median(x)
    y=x-baseline
    noise=np.median(np.abs(y-np.median(y)))*1.4826
    scale=np.sqrt(np.mean(y*y))
    return y/(scale+1e-12), float(noise/(scale+1e-12))

def align_to_reference(ref, x):
    a,_=normalise(ref); b,_=normalise(x)
    corr=np.fft.irfft(np.fft.rfft(a)*np.conj(np.fft.rfft(b)), n=len(a))
    shift=int(np.argmax(corr))
    return np.roll(b,shift), shift

def distance(a,b):
    aa,_=normalise(a); bb,shift=align_to_reference(a,b)
    r=np.corrcoef(aa,bb)[0,1]
    if not np.isfinite(r): r=0.0
    return float(np.clip(1-r,0,2)), bb, shift, float(r)

def frequency_distance(f1,f2):
    return abs(np.log10(max(float(f1),1e-9)/max(float(f2),1e-9)))

def percentile(values, value):
    v=np.asarray(values,float)
    if len(v)<=1: return 50.0
    return float(100*np.mean(v <= value))

def robust_z(values, value):
    v=np.asarray(values,float)
    med=np.median(v)
    mad=np.median(np.abs(v-med))
    return float((value-med)/(1.4826*mad+1e-9))
