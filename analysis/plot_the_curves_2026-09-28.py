#!/usr/bin/env python3
"""Draw the six-panel figure of the measured curves, in plain language.

Written by Claude, September 28, 2026, after Elizabeth Schumann said the first
version of the figure was written in this project's own shorthand and did not
stand on its own. Her objections, each fixed here:
  "you have to say what size of the hand"          -> the box at the bottom right
  "the span is the amount the hand is stretched"   -> every axis now reads
        "how far the hand is opened", and the box says it is not hand size
  "I do not understand the phrase forearm roll"    -> panel 3 says in words that
        pressing with the thumb out to the side also twists the forearm
  "I do not know what you mean by the repair tree" -> the three versions of the
        model are named in plain English in panel 1 and in the box

A FIGURE WITH NO GENERATOR IS THE DEFECT THIS PROJECT JUST FOUND IN ITS OWN
CURVE CSVs, so this script is kept beside the figure it draws.

Input: /tmp/data.pkl, a pickle of {(tree, posture): [rows]} where each row is the
dict returned by Hand.measure() in build_curves_2026-09-28.py. Rebuilding it
means extracting the three trees and sweeping, which run16 of the state file
records step by step.

    python3 plot_the_curves_2026-09-28.py

Writes: FIGURES, the measured curves 2026-09-28_run2.png
"""
import pickle, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=pickle.load(open('/tmp/data.pkl','rb'))
OUT="/sessions/brave-lucid-thompson/mnt/Workspace/Research_Projects/AI_Model/AI_Model_CL"
g=lambda k,c: np.array([r[c] for r in D[k]])
plt.rcParams.update({'font.family':'serif','font.size':9.5,'axes.titlesize':11,'axes.labelsize':9.5,
 'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#555','axes.linewidth':0.7,
 'xtick.color':'#555','ytick.color':'#555','xtick.labelsize':8.5,'ytick.labelsize':8.5,
 'legend.fontsize':8.5,'legend.frameon':False,'figure.facecolor':'white','axes.facecolor':'white',
 'grid.color':'#e8e8e8','grid.linewidth':0.6})
INK='#1a1a1a'; RED='#a03020'; BLUE='#2b5578'; GREY='#8a8a8a'; GREEN='#3d6b4a'; SOFT='#666'
OCT_F=142.765; OCT_D=165.392157
rf=('repair','flat'); rp=('repair','playing'); rc=('repair','curled'); pf=('pristine','flat'); sf=('step1','flat')
s=g(rf,'span_mm')
def head(a,title,lines):
    a.set_title(title,loc='left',color=INK,fontweight='bold',pad=50)
    a.text(0,1.015,lines,transform=a.transAxes,fontsize=8.4,color=SOFT,va='bottom',ha='left',linespacing=1.4)
def octl(a):
    a.axvline(OCT_F,color=GREEN,lw=1.0,ls='--',zorder=1); a.axvline(OCT_D,color=GREY,lw=1.0,ls=':',zorder=1)

fig=plt.figure(figsize=(14.6,11.2))
gs=fig.add_gridspec(2,3,hspace=0.55,wspace=0.42,top=0.760,bottom=0.185,left=0.058,right=0.972)
A=fig.add_subplot(gs[0,0]); B=fig.add_subplot(gs[0,1]); C=fig.add_subplot(gs[0,2])
E=fig.add_subplot(gs[1,0]); F=fig.add_subplot(gs[1,1]); T=fig.add_subplot(gs[1,2]); T.axis('off')

A.axhspan(1e-3,0.15,color='#eef4ee',zorder=0)
A.plot(g(sf,'span_mm'),g(sf,'residual_Nm'),color=RED,lw=2.2,label='with the fix AND the range correction')
A.plot(g(pf,'span_mm'),g(pf,'residual_Nm'),color=GREY,lw=2.6,label='the model as it ships today')
A.plot(s,g(rf,'residual_Nm'),color=BLUE,lw=1.7,ls=(0,(4,2)),label='with the muscle fix only')
A.set_yscale('log'); A.set_ylim(1e-3,90); octl(A)
A.annotate('6.6 Nm the muscles cannot supply',(77,6.6),textcoords='offset points',xytext=(0,9),fontsize=8.2,color=RED)
A.annotate('0.003 Nm, which is nothing',(77,0.0031),textcoords='offset points',xytext=(0,-15),fontsize=8.2,color=INK)
A.text(0.97,0.10,'below the green band the\nhand stays put by itself',transform=A.transAxes,ha='right',fontsize=8,color=GREEN)
head(A,'1.  Does the hand stay put, or sag?','Let the hand go slack in this shape. How much force would it need,\nthat no muscle in the model can supply, to keep from sagging?')
A.set_xlabel('how far the hand is opened, mm'); A.set_ylabel('force the muscles cannot supply, Nm')
A.legend(loc='center left',bbox_to_anchor=(0.02,0.60)); A.grid(axis='y',alpha=.6)

st=g(rf,'strength_N_mu0p5')
B.plot(s,st,color=RED,lw=2.2); octl(B); pk=int(np.argmax(st))
B.plot([s[pk]],[st[pk]],'o',color=RED,ms=5)
B.annotate('strongest here, 30.4 N,\nhand open about a fourth',(s[pk],st[pk]),textcoords='offset points',xytext=(7,-6),fontsize=8.2,color=RED)
B.plot([OCT_F],[np.interp(OCT_F,s,st)],'o',color=INK,ms=4)
B.annotate('22.5 N at\nan octave',(OCT_F,np.interp(OCT_F,s,st)),textcoords='offset points',xytext=(-7,-24),fontsize=8.2,color=INK,ha='right')
B.set_ylim(15,34)
head(B,'2.  How hard can the thumb press?','The most downward force the thumb can put into one key,\nwith the hand opened to each width.')
B.set_xlabel('how far the hand is opened, mm'); B.set_ylabel('downward force at the thumb, newtons')
B.grid(axis='y',alpha=.6)

rl=g(rf,'roll_Nm_per_N')
C.plot(s,rl,color=GREEN,lw=2.2)
for x,lab in ((104,'a fourth'),(119,'a fifth'),(OCT_F,'an octave')):
    v=np.interp(x,s,rl); C.plot([x],[v],'o',color=INK,ms=4,zorder=5)
    C.annotate(lab,(x,v),textcoords='offset points',xytext=(-7,11),fontsize=8.2,color=INK,ha='right')
C.axvline(OCT_D,color=GREY,lw=1.0,ls=':')
head(C,'3.  How much does the press twist the arm?','With the thumb out to the side, pressing down also\ntwists the forearm. This is the twist you must hold\nagainst, for each newton you press.')
C.set_xlabel('how far the hand is opened, mm'); C.set_ylabel('twist to resist, Nm per newton pressed')
C.grid(axis='y',alpha=.6)
C.text(0.96,0.07,'a fourth to an octave:  +48 %\na fifth to an octave:  +23 %',transform=C.transAxes,ha='right',fontsize=8.4,color=GREEN)

labs=['flat','slightly curved\n(playing)','well curved']
mx=[g(rf,'span_mm').max(),g(rp,'span_mm').max(),g(rc,'span_mm').max()]
bars=E.bar(labs,mx,color=[BLUE,GREEN,RED],width=0.5)
E.axhline(OCT_F,color=GREEN,ls='--',lw=1.1); E.axhline(OCT_D,color=GREY,ls=':',lw=1.1)
E.text(2.42,OCT_D+5,'an octave among the\nblack keys needs 165.4',fontsize=8.2,color=GREY)
E.text(2.42,OCT_F-34,'an octave at the front\nof the keys needs 142.8',fontsize=8.2,color=GREEN)
for b,v in zip(bars,mx): E.text(b.get_x()+b.get_width()/2,v+6,'%.0f mm'%v,ha='center',fontsize=9.2,color=INK)
E.set_ylim(0,205); E.set_xlim(-0.6,3.7)
head(E,'4.  How wide can it open and still stay put?','Widest the hand opens with the muscle fix, staying put and with no\nfinger passing through another. Shape of the fingers along the bottom.')
E.set_ylabel('widest opening, mm'); E.grid(axis='y',alpha=.6)

em=g(rf,'effMass_g')
F.plot(s,em,color=BLUE,lw=2.2); octl(F)
F.annotate('396 g with the\nhand closed',(s[0],em[0]),textcoords='offset points',xytext=(8,-6),fontsize=8.2,color=BLUE)
F.annotate('254 g wide open',(s[-1],em[-1]),textcoords='offset points',xytext=(-7,10),fontsize=8.2,color=BLUE,ha='right')
head(F,'5.  How much of the hand is behind the key?','The weight the key feels through the thumb. Opening the hand takes\na third of it away, so the same press makes less sound.')
F.set_xlabel('how far the hand is opened, mm'); F.set_ylabel('weight felt at the key, grams')
F.grid(axis='y',alpha=.6)
F.text(0.96,0.90,'a fall of 36 %',transform=F.transAxes,ha='right',fontsize=8.6,color=BLUE)

T.text(0,1.10,'What you are looking at',fontsize=12,color=INK,fontweight='bold',va='top')
txt=("WHOSE HAND.  One hand: the model's own right hand,\n"
"174 mm from wrist to middle fingertip, which Wagner 1988\n"
"puts near the 80th percentile of female pianists. Hand and\n"
"forearm weigh 1.79 kg together. It is one hand, not a\n"
"population, so nothing here is a claim about pianists in\n"
"general.\n"
"\n"
"\u201cHOW FAR THE HAND IS OPENED\u201d is the distance from\n"
"the thumb tip to the little fingertip AT THAT MOMENT. It is\n"
"how far the hand is stretched, not how big the hand is: the\n"
"hand is the same size in every panel and only the stretch\n"
"changes.\n"
"      76 mm   thumb tucked in against the palm\n"
"    104 mm   about a fourth\n"
"    119 mm   about a fifth\n"
"    143 mm   an octave taken at the front of the keys\n"
"    160 mm   as wide as this hand goes\n"
"\n"
"THE THREE VERSIONS in panel 1:\n"
"    as it ships today:  unchanged since March\n"
"    muscle fix only:  the September 10 repair\n"
"    fix + range correction:  the September 12 muscle\n"
"          length correction applied on top of the repair")
T.text(0,1.035,txt,fontsize=8.3,color=INK,va='top',linespacing=1.44)

fig.suptitle('The biomechanical piano model: what the measurements say, September 28, 2026',x=0.058,ha='left',fontsize=15.5,color=INK,fontweight='bold',y=0.977)
fig.text(0.058,0.930,'Read the box at the bottom right first. Every panel sweeps the same thing: the hand opening from thumb-tucked to as wide as it goes.',fontsize=9.8,color=SOFT)
fig.text(0.058,0.905,'Panels 2, 3 and 5 use the model with the muscle fix only, the version recommended for shipping, with the fingers flat.',fontsize=9.8,color=SOFT)
fig.text(0.058,0.880,'Dashed green line: the stretch an octave needs at the front of the keys, 142.8 mm.     Dotted grey line: the stretch it needs among the black keys, 165.4 mm.',fontsize=9.8,color=SOFT)
fig.text(0.058,0.046,'Panels 3 and 5 reproduce this project’s earlier numbers exactly. Panel 2 uses a force definition written down in build_curves_2026-09-28.py: it agrees with the earlier figures within',fontsize=8,color=GREY)
fig.text(0.058,0.024,'0.5 to 6.7 percent and matches their shape, but the earlier definition was never recorded anywhere, so panel 2’s absolute numbers are the less certain of the two.',fontsize=8,color=GREY)
fig.text(0.058,0.118,'POSTURE IS NOT A DETAIL. Curling the finger that is pressing more than doubles what the key feels, 261.6 to 580.6 g at the index; holding the hand firm rather than letting it give',fontsize=8.6,color='#a03020')
fig.text(0.058,0.100,'is a further factor of 4.9. Panels 2, 3 and 5 are at ONE posture, the flat default, which nobody plays from. Quote them as figures at that posture, never as the figure.',fontsize=8.6,color='#a03020')
fig.text(0.058,0.074,'THE KEYBOARD is the model’s own, a 6.5 inch octave. White keys are 22.6 mm wide and 148 mm deep;',fontsize=8.6,color=SOFT)
fig.text(0.058,0.056,'black keys reach only 96 mm in, so the front 52 mm of every white key is clear of them. That is why',fontsize=8.6,color=SOFT)
fig.text(0.058,0.038,'an octave taken at the front needs 22.6 mm less stretch than one taken further in.',fontsize=8.6,color=SOFT)
fig.savefig(OUT+'/FIGURES, the measured curves 2026-09-28_run2.png',dpi=190)
print('written')
