"""DEAD END 15 APPLIED TO THIS MEASUREMENT.
The findings metric covered the 23 hinges and excluded the free-joint root. That is the exact
shape of dead end 15. This asks whether the excluded channel carries posture information or
whether it carries the keyboard's own rescaling. biomechanical model t8, September 9, 2026."""
import sys, os, itertools, numpy as np
sys.path.insert(0,"/tmp/bm_t8_posture_20260909/t8_work")
from ik import Hand
PN=['A0','A#0','B0']+[f"{b}{o}" for o in range(1,8) for b in ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']]+['C8']
P={n:i for i,n in enumerate(PN)}
for n in list(P):
    if '#' in n:
        for f,s in {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}.items():
            if n.startswith(s): P[f+n[len(s):]]=P[n]
notes=[]
for ln in open("/tmp/bm_t8_posture_20260909/017-1_fingering.txt"):
    ln=ln.strip()
    if not ln or ln.startswith("//"): continue
    f=ln.split("\t"); notes.append(dict(on=float(f[1]),off=float(f[2]),pitch=f[3],chan=int(f[6]),finger=abs(int(f[7]))))
def quat_angle(q1,q2):
    d=abs(float(np.dot(q1,q2))); d=min(1.0,d); return np.degrees(2*np.arccos(d))
for handname in ("right","left"):
    hn=[n for n in notes if n["chan"]==(0 if handname=="right" else 1)]
    sample=[(a,b) for a,b in itertools.combinations(hn,2) if abs(a["on"]-b["on"])<=0.5 and a["finger"]!=b["finger"]]
    Hw,Hn=Hand(handname,"wide"),Hand(handname,"narrow")
    rootshift=[];tgtshift=[];resid=[];orient=[];sepw=[];sepn=[];hinge=[]
    for a,b in sample:
        f=[a["finger"],b["finger"]]; k=[P[a["pitch"]],P[b["pitch"]]]
        qw,ew=Hw.solve(f,k); qn,en=Hn.solve(f,k)
        if max(ew,en)>1e-4: continue
        dr=qn[:3]-qw[:3]
        dt=Hn.targets[k].mean(0)-Hw.targets[k].mean(0)     # where the two keys themselves moved
        rootshift.append(np.linalg.norm(dr)*1000)
        tgtshift.append(np.linalg.norm(dt)*1000)
        resid.append(np.linalg.norm(dr-dt)*1000)
        orient.append(quat_angle(qw[3:7],qn[3:7]))
        sepw.append(np.linalg.norm(Hw.targets[k[0]]-Hw.targets[k[1]])*1000)
        sepn.append(np.linalg.norm(Hn.targets[k[0]]-Hn.targets[k[1]])*1000)
        hinge.append(np.abs(Hw.angles_deg(qw)-Hn.angles_deg(qn)).max())
    q=lambda v,p: np.percentile(v,p)
    print(f"\n===== {handname.upper()} HAND, {len(resid)} pairs, onsets within 500 ms =====")
    print(f"  root TRANSLATION between conditions        median {np.median(rootshift):7.1f} mm   max {max(rootshift):7.1f}")
    print(f"  the two keys' own midpoint moved by        median {np.median(tgtshift):7.1f} mm   max {max(tgtshift):7.1f}")
    print(f"  RESIDUAL, root shift minus key shift       median {np.median(resid):7.1f} mm   max {max(resid):7.1f}")
    print(f"     -> fraction of root motion explained by the keyboard rescaling: "
          f"{100*(1-np.median(resid)/np.median(rootshift)):.1f}% at the median")
    print(f"  root ORIENTATION change between conditions median {np.median(orient):7.2f} deg  75th {q(orient,75):6.2f}  max {max(orient):7.2f}")
    print(f"  required fingertip separation, wide        median {np.median(sepw):7.1f} mm")
    print(f"  required fingertip separation, narrow      median {np.median(sepn):7.1f} mm")
    print(f"  separation CHANGE                          median {np.median(np.array(sepw)-np.array(sepn)):7.1f} mm")
    print(f"  hinge-only metric used in the findings     median {np.median(hinge):7.2f} deg  75th {q(hinge,75):6.2f}  max {max(hinge):7.2f}")
