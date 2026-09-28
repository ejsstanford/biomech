import numpy as np, csv, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
D="/sessions/brave-lucid-thompson/mnt/Workspace/Research_Projects/AI_Model/AI_Model_CL/"
def rd(f):
    rows=list(csv.DictReader(open(D+f)))
    return {k:np.array([float(r[k]) for r in rows]) for k in rows[0]}
pre=rd("curve, three channels against thumb abduction 2026-09-26_run2.csv")
post=rd("curve, three channels on the REPAIRED model 2026-09-28.csv")
d=pre['deg']; sp=pre['span_mm']
plt.rcParams.update({'font.family':'serif','font.size':10,'axes.titlesize':11.5,'axes.labelsize':10,
 'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#555','axes.linewidth':0.7,
 'xtick.color':'#555','ytick.color':'#555','xtick.labelsize':9,'ytick.labelsize':9,
 'legend.fontsize':9,'legend.frameon':False,'figure.facecolor':'white','axes.facecolor':'white',
 'grid.color':'#e8e8e8','grid.linewidth':0.6})
INK='#1a1a1a'; RED='#a03020'; BLUE='#2b5578'; GREY='#9a9a9a'; SOFT='#666'

fig=plt.figure(figsize=(14.2,6.6))
gs=fig.add_gridspec(1,3,wspace=0.30,top=0.615,bottom=0.215,left=0.055,right=0.985)
ax=[fig.add_subplot(gs[0,i]) for i in range(3)]

def span_axis(a):
    t=a.twiny(); t.set_xlim(a.get_xlim()); t.spines['right'].set_visible(False)
    ticks=[-28.65,-10.31,8.02,26.36,44.69]
    t.set_xticks(ticks); t.set_xticklabels(['%.0f'%np.interp(x,d,sp) for x in ticks])
    t.tick_params(colors=SOFT,labelsize=8.5)

panels=[('effMass_g','Force transfer','how much of the hand the key feels\nthrough the thumb, in grams','grams'),
        ('strength_N_mu0.5','Strength','the most downward force the thumb\ncan put into one key, in newtons','newtons'),
        ('agility_mps2','Agility','how fast the fingertip can be\naccelerated, in m/s squared','m/s squared')]
for i,(k,title,sub,unit) in enumerate(panels):
    a=ax[i]
    a.plot(d,pre[k],color=GREY,lw=5.0 if k=='effMass_g' else 2.0,ls='-' if k=='effMass_g' else (0,(4,2)),alpha=1.0,label='before the muscle repair')
    a.plot(d,post[k],color=[BLUE,RED,'#3d6b4a'][i],lw=2.4,label='after the muscle repair')
    a.axvline(0,color='#dddddd',lw=0.8,zorder=0)
    a.set_title('%d.  %s'%(i+1,title),loc='left',color=INK,fontweight='bold',pad=58)
    a.text(0,1.082,sub,transform=a.transAxes,fontsize=8.8,color=SOFT,va='bottom',linespacing=1.4)
    a.set_xlabel('carpometacarpal abduction, degrees')
    a.set_ylabel(unit); a.grid(axis='y',alpha=.6); a.set_xlim(d[0]-2,d[-1]+2)
    pk=int(np.argmax(post[k]))
    if k!='effMass_g':
        a.plot([d[pk]],[post[k][pk]],'o',color=[BLUE,RED,'#3d6b4a'][i],ms=5)
        a.annotate('peak %.1f\nat %+.0f deg'%(post[k][pk],d[pk]),(d[pk],post[k][pk]),
                   textcoords='offset points',xytext=(6,-30),fontsize=8.6,color=[BLUE,RED,'#3d6b4a'][i])
    span_axis(a)
ax[0].set_ylim(230,420); ax[1].set_ylim(0,36); ax[2].set_ylim(80,410)
ax[0].legend(loc='lower left',handlelength=2.6)
ax[0].text(0.97,0.88,'-35.8 % across the sweep.\nThe grey line is underneath:\nthe repair does not move this\ncurve by one digit, which is\nthe control on panels 2 and 3',transform=ax[0].transAxes,ha='right',va='top',fontsize=8.8,color=BLUE)
ax[1].text(0.97,0.90,'-79.0 % before the repair\n-46.4 % after, from its peak',transform=ax[1].transAxes,ha='right',fontsize=8.8,color=RED)
ax[2].text(0.97,0.14,'-42.2 % before the repair\n-39.3 % after, from its peak',transform=ax[2].transAxes,ha='right',fontsize=8.8,color='#3d6b4a')

fig.suptitle('Force transfer, strength and agility across the angles of thumb abduction',x=0.055,ha='left',fontsize=15,color=INK,fontweight='bold',y=0.965)
fig.text(0.055,0.905,'The goals document, question 2.2: "Can we graph force transfer efficiency across different angles of abduction?" This is that graph, with strength and agility beside it.',fontsize=9.8,color=SOFT)
fig.text(0.055,0.867,'One right hand, 174 mm wrist to middle fingertip, near the 80th percentile of female pianists. Fingers flat, thumb swept across its full declared range of -28.6 to +44.7 degrees.',fontsize=9.8,color=SOFT)
fig.text(0.055,0.829,'Negative angles are the thumb tucked toward the palm, zero is neutral, positive is opening out. The small numbers along the top of each panel are the hand span, in mm, at that angle.',fontsize=9.8,color=SOFT)
fig.text(0.055,0.105,'FORCE TRANSFER is effective mass at the thumb tip, the quantity the goals document asks for: the inertia the key actually feels through that finger. It carries no muscle parameters,',fontsize=8.6,color=SOFT)
fig.text(0.055,0.077,'which is why the repair leaves it untouched to the digit, and that is the control on the other two panels.  STRENGTH and AGILITY are this project\'s own recorded columns. Their formulas',fontsize=8.6,color=SOFT)
fig.text(0.055,0.049,'were never written down and have not been recovered, so the shapes and the within-curve ratios are the result and the absolute values are the less certain part.',fontsize=8.6,color=SOFT)
fig.text(0.055,0.014,'Measured on the shipped model and on the tree carrying the September 10 muscle repair, at the flat default posture. Data in AI_Model_CL/, the two CSVs named "three channels".',fontsize=7.8,color='#999')
fig.savefig(D+"FIGURE, force transfer and agility against abduction angle 2026-09-28.png",dpi=190)
print("written")
