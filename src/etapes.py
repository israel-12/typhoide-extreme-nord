import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
import sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
L=sys.argv[1]; T=lambda fr,en: fr if L=='fr' else en
plt.rcParams.update({'font.family':'DejaVu Sans'})
fig,ax=plt.subplots(figsize=(12,6.2)); ax.set_xlim(-0.05,12.05); ax.set_ylim(0,6.2); ax.axis('off')
P=[('#2b6cb0','#e6eef8',T('DONNÉES','DATA'),[
     (T('Surveillance DHIS2','DHIS2 surveillance'),T('617 481 lignes, 522 formations\nsanitaires, 2019-2025','617,481 rows, 522 health\nfacilities, 2019–2025')),
     (T('Climat NASA POWER','NASA POWER climate'),T('pluie, température,\nhumidité quotidiennes','daily rainfall,\ntemperature, humidity')),
     (T('Limites et hiérarchie','Boundaries and hierarchy'),T('32 districts de santé\n(DHIS2)','32 health districts\n(DHIS2)'))]),
   ('#2a8c82','#e3f3f1',T('PRÉTRAITEMENT','PRE-PROCESSING'),[
     (T('Agrégation','Aggregation'),T('365 semaines × 32 districts\nvalidé : écart médian 0 %','365 weeks × 32 districts\nvalidated: median gap 0%')),
     (T('Données manquantes','Missing data'),T('5,5 % imputées\n(interpolation linéaire)','5.5% imputed\n(linear interpolation)')),
     (T('Valeurs aberrantes','Outliers'),T('filtre de Hampel :\n417 signalées, conservées','Hampel filter:\n417 flagged, retained')),
     (T('Transformation','Transformation'),T('ln(1 + cas)\nloi de Taylor, b = 1,37','ln(1 + cases)\nTaylor\'s law, b = 1.37'))]),
   ('#d9822b','#fbefe2',T('ANALYSE ET\nMODÉLISATION','ANALYSIS AND\nMODELLING'),[
     (T('Analyse exploratoire','Exploratory analysis'),T('STL, ADF, KPSS, ACF :\nstationnaire après différenciation','STL, ADF, KPSS, ACF:\nstationary after differencing')),
     (T('Modèle mathématique','Mathematical model'),T('réservoir de bactéries + pluie\n→ hypothèses H1 à H4','bacterial reservoir + rain\n→ hypotheses H1–H4')),
     (T('Lien pluie-cas','Rainfall–case link'),T('décalages 0-12 semaines,\nanomalies de pluie','lags 0–12 weeks,\nrainfall anomalies')),
     (T('Variables explicatives','Feature engineering'),T('retards, moyennes mobiles,\nsaison, pluie, niveau du district','lags, rolling means,\nseason, rain, district level'))]),
   ('#7b5ea7','#efeaf6',T('PRÉVISION ET\nÉVALUATION','FORECASTING AND\nEVALUATION'),[
     (T('Méthodes comparées','Methods compared'),T('naïve, ARIMA, Prophet,\nXGBoost local / global / climat','naive, ARIMA, Prophet,\nXGBoost local / global / climate')),
     (T('Origine glissante','Rolling origin'),T('2023-2025 (156 semaines)\nhorizons 1 et 4 semaines','2023–2025 (156 weeks)\nhorizons 1 and 4 weeks')),
     (T('Tests statistiques','Statistical tests'),T('Diebold-Mariano (HLN),\npar district et global','Diebold–Mariano (HLN),\nby district and overall'))]),
   ('#b03a2e','#f8e5e3',T('RÉSULTATS ET\nDÉCISION','RESULTS AND\nDECISION'),[
     (T('Calendrier','Timing'),T('pic en octobre,\n8 semaines après la pluie','peak in October,\n8 weeks after rainfall')),
     (T('Prévision par district','District forecasting'),T('modèle global :\n−15 % d\'erreur (p < 0,001)','global model:\n−15% error (p < 0.001)')),
     (T('Recommandations','Recommendations'),T('préparation dès juillet,\ndistricts prioritaires','preparedness from July,\npriority districts'))])]
W=2.24; G=0.2; x0=0.0
for i,(c,cl,titre,cards) in enumerate(P):
    x=x0+i*(W+G)
    ax.add_patch(FancyBboxPatch((x,0.15),W,5.85,boxstyle='round,pad=0.02,rounding_size=0.12',fc=cl,ec='none'))
    ax.add_patch(FancyBboxPatch((x,5.15),W,0.85,boxstyle='round,pad=0.02,rounding_size=0.12',fc=c,ec='none'))
    ax.add_patch(Circle((x+0.3,5.575),0.2,fc='white',ec='none')); ax.text(x+0.3,5.575,str(i+1),ha='center',va='center',fontsize=11,fontweight='bold',color=c)
    ax.text(x+0.58,5.575,titre,ha='left',va='center',fontsize=8.6,fontweight='bold',color='white',linespacing=1.1)
    n=len(cards); hc=0.98; gap=(4.85-n*hc)/(n+1)
    for j,(t,s) in enumerate(cards):
        y=5.0-gap-(j+1)*hc-j*gap
        ax.add_patch(FancyBboxPatch((x+0.1,y),W-0.2,hc,boxstyle='round,pad=0.01,rounding_size=0.06',fc='white',ec=c,lw=0.9))
        ax.add_patch(Rectangle((x+0.1,y+0.01),0.07,hc-0.02,fc=c,ec='none'))
        ax.text(x+0.27,y+hc-0.2,t,fontsize=6.9,fontweight='bold',color=c,va='center')
        ax.text(x+0.27,y+0.36,s,fontsize=6.0,color='#333',va='center',linespacing=1.15)
        if j<n-1: ax.annotate('',xy=(x+W/2,y-gap+0.03),xytext=(x+W/2,y-0.02),arrowprops=dict(arrowstyle='-|>',color=c,lw=0.9))
    if i<len(P)-1:
        ax.annotate('',xy=(x+W+G-0.03,3.1),xytext=(x+W+0.03,3.1),arrowprops=dict(arrowstyle='simple,head_width=0.7,head_length=0.6,tail_width=0.35',color='#555'))
fig.savefig(str(FIG/f'{L}_etapes.png'),dpi=300,bbox_inches='tight'); print('ok')
