import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
import sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
L=sys.argv[1]; T=lambda fr,en: fr if L=='fr' else en
NAVY,ORA,TEAL,RED='#1f3b63','#d9822b','#2a7f7f','#b03a2e'
fig,ax=plt.subplots(figsize=(7.2,3.9)); ax.set_xlim(0,10); ax.set_ylim(0,5.4); ax.axis('off')
def box(x,y,t,sub,c,w=1.5):
    ax.add_patch(FancyBboxPatch((x-w/2,y-0.42),w,0.84,boxstyle='round,pad=0.02,rounding_size=0.12',fc=c,ec=NAVY,lw=1))
    ax.text(x,y+0.1,t,ha='center',va='center',fontsize=12,fontweight='bold',color=NAVY); ax.text(x,y-0.2,sub,ha='center',va='center',fontsize=6.6)
def arr(x1,y1,x2,y2,lab='',c=NAVY,ls='-',rad=0,lx=0,ly=0.12,fs=7):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=10,color=c,lw=1.1,ls=ls,connectionstyle=f'arc3,rad={rad}'))
    if lab: ax.text((x1+x2)/2+lx,(y1+y2)/2+ly,lab,ha='center',fontsize=fs,color=c)
box(1.4,3.6,'S',T('sensibles','susceptible'),'#e8eef6')
box(4.4,4.5,'C',T('porteurs','carriers'),'#fbeee0')
box(4.4,2.7,'I',T('malades','infected'),'#f6dcd8')
box(7.4,3.6,'R',T('guéris','recovered'),'#e4f1ee')
box(4.4,0.75,'B',T('bactéries dans l\'eau','bacteria in water'),'#dbe9f6',w=1.9)
arr(2.15,3.8,3.65,4.4,'ρλ',ly=0.15); arr(2.15,3.4,3.65,2.85,'(1−ρ)λ',ly=-0.32)
arr(4.4,4.08,4.4,3.12,'θ',lx=0.15,ly=0)
arr(5.15,4.4,6.65,3.8,'φ',ly=0.12); arr(5.15,2.85,6.65,3.4,'β',ly=-0.28)
ax.annotate('',xy=(1.4,4.02),xytext=(7.4,4.02),arrowprops=dict(arrowstyle='-|>',color=NAVY,lw=1.1,connectionstyle='arc3,rad=0.35'))
ax.text(4.4,5.25,T('δ (perte d\'immunité)','δ (loss of immunity)'),ha='center',fontsize=7,color=NAVY)
# shedding
arr(3.65,4.3,3.75,1.15,'σ₁',c=TEAL,ls='--',rad=0.45,lx=-0.62,ly=-0.85)
arr(4.4,2.28,4.4,1.17,'σ₂',c=TEAL,ls='--',lx=0.18,ly=0)
# infection from B
arr(3.45,0.75,1.4,3.18,'',c=RED,rad=-0.25)
ax.text(1.55,1.55,T('force d\'infection\nλ = νB/(K+B)','force of infection\nλ = νB/(K+B)'),fontsize=7.5,color=RED,ha='center')
# rain
ax.text(8.2,0.95,T('PLUIE  P(t)','RAINFALL  P(t)'),fontsize=9,fontweight='bold',color='#1d6fa5',ha='center')
ax.text(8.2,0.72,T('ruissellement, puits,\nlatrines qui débordent','runoff, wells,\noverflowing latrines'),fontsize=6.5,color='#1d6fa5',ha='center',va='top')
arr(7.3,0.85,5.35,0.8,'κP(t)',c='#1d6fa5',ly=0.1,fs=8)
ax.text(4.4,0.12,T('disparition $\\mu_b$','decay $\\mu_b$'),ha='center',fontsize=6.6,color=TEAL)
fig.savefig(str(FIG/f'{L}_schema_modele.png'),dpi=300,bbox_inches='tight'); print('ok')
