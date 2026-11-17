import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
import pandas as pd, numpy as np, json, sys, warnings; warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
pass
L=sys.argv[1]  # fr / en
T=lambda fr,en: fr if L=='fr' else en
A=str(RES/'exploration')+'/'; D=str(DATA)+'/'; O=str(FIG)+f'/{L}_'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
 'axes.titlesize':10,'axes.titleweight':'bold','axes.labelsize':9,'legend.fontsize':8,'legend.frameon':False,'savefig.dpi':300,'savefig.bbox':'tight'})
NAVY,ORA,GRE,RED,TEAL='#1f3b63','#d9822b','#8c8c8c','#b03a2e','#2a7f7f'
from pipeline_typhoide import charger_donnees, imputer
brut=charger_donnees(D+'df_2019_2025.xlsx'); Y=imputer(brut); y=Y.sum(axis=1)
mois=T(['J','F','M','A','M','J','J','A','S','O','N','D'],['J','F','M','A','M','J','J','A','S','O','N','D'])

# F1 pipeline
fig,ax=plt.subplots(figsize=(7.2,3.4)); ax.axis('off'); ax.set_xlim(0,10); ax.set_ylim(0.2,5)
def box(x,y,w,h,t,c):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.1',fc=c,ec=NAVY,lw=0.8)); ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=6.2,linespacing=1.3)
def arr(x1,y1,x2,y2): ax.annotate('',xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle='-|>',color=NAVY,lw=0.9))
W,H,G=2.25,1.25,0.27
L1=[T('1. Export DHIS2\nMAPE16_H_10\n617 481 lignes','1. DHIS2 export\nMAPE16_H_10\n617,481 rows'),
    T('2. Hiérarchie\n522 formations\n→ districts','2. Hierarchy\n522 facilities\n→ districts'),
    T('3. Fusion Waza → Mora\n32 districts\n2019-2025','3. Merge Waza → Mora\n32 districts\n2019–2025'),
    T('4. Contrôle qualité\nvs extraction antérieure\nécart médian 0 %','4. Quality check\nvs earlier extract\nmedian gap 0%')]
L2=[T('5. Manquants 5,5 %\nimputation linéaire\npar district','5. Missing 5.5%\nlinear imputation\nby district'),
    T('6. Climat NASA POWER\npluie, T°, humidité\n→ semaines DHIS2','6. NASA POWER climate\nrain, temp., humidity\n→ DHIS2 weeks'),
    T('7. Analyse exploratoire\nSTL, indices saisonniers\nADF, KPSS, ACF/PACF','7. Exploratory analysis\nSTL, seasonal indices\nADF, KPSS, ACF/PACF'),
    T('8. Modèles, évaluation\norigine glissante 2023-2025\nDiebold-Mariano','8. Models, evaluation\nrolling origin 2023–2025\nDiebold–Mariano')]
xs=[0.05+i*(W+G) for i in range(4)]
for x,t in zip(xs,L1): box(x,3.4,W,H,t,'#e8eef6')
for i in range(3): arr(xs[i]+W,4.02,xs[i+1],4.02)
for x,t in zip(xs[::-1],L2): box(x,1.3,W,H,t,'#fbeee0' if '8.' not in t else '#e4f1ee')
arr(xs[3]+W/2,3.4,xs[3]+W/2,2.55)
for i in range(3,0,-1): arr(xs[i],1.92,xs[i-1]+W,1.92)
ax.text(5,0.55,T('Sortie : 365 semaines × 32 districts, série régionale et covariables climatiques alignées','Output: 365 weeks × 32 districts, regional series and aligned climate covariates'),fontsize=7,style='italic',color=NAVY,ha='center')
fig.savefig(O+'f1_pipeline.png'); plt.close()

# F2 map mean weekly cases
geo=json.load(open(D+'districts_sante.geojson',encoding='utf-8'))['features']
mean=brut.mean()
def carte(ax,val,cmap,vmin,vmax,title,lab):
    norm=plt.Normalize(vmin,vmax); cm=plt.get_cmap(cmap)
    for f in geo:
        d=f['properties']['district']; g=f['geometry']
        for p in ([g['coordinates']] if g['type']=='Polygon' else g['coordinates']):
            xs,ys=zip(*p[0]); ax.fill(xs,ys,color=cm(norm(val[d])),ec='white',lw=0.5)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title,fontsize=9)
    cb=plt.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cm),ax=ax,shrink=0.55,pad=0.01); cb.set_label(lab,fontsize=7); cb.ax.tick_params(labelsize=7)
c=pd.read_csv(D+'districts_coordonnees.csv').set_index('district')
fig,axs=plt.subplots(1,2,figsize=(7.2,5))
carte(axs[0],mean,'YlOrRd',0,140,T('Cas hebdomadaires moyens','Mean weekly cases'),T('cas/semaine','cases/week'))
for d in ['Kousseri','Maroua 1','Mokolo','Mora','Yagoua','Mada','Kolofata','Kaele']:
    axs[0].text(c.at[d,'longitude'],c.at[d,'latitude'],d,fontsize=6,ha='center')
carte(axs[1],brut.isna().mean()*100,'Greys',0,50,T('Semaines manquantes','Missing weeks'),'%')
fig.savefig(O+'f2_carte.png'); plt.close()

# F3 series + facilities
import pandas as pd
fac=pd.read_csv(D+'formations_declarantes_par_semaine.csv',index_col=0,parse_dates=True).iloc[:,0]
fig,ax=plt.subplots(figsize=(7.2,3))
ax.plot(y.index,y,color=NAVY,lw=1,label=T('Cas déclarés (région)','Reported cases (region)'))
ax.axvspan(y.index[-156],y.index[-1],color=ORA,alpha=0.12,lw=0); ax.text(y.index[-150],1980,T('Période test','Test period'),fontsize=7.5,color=ORA)
ax.set_ylabel(T('Cas par semaine','Cases per week')); ax.set_ylim(0,2100)
ax2=ax.twinx(); ax2.plot(fac.index,fac,color=GRE,lw=1,ls='--',label=T('Formations déclarantes','Reporting facilities'))
ax2.set_ylabel(T('Formations déclarantes','Reporting facilities'),color=GRE); ax2.set_ylim(0,420); ax2.spines['right'].set_visible(True); ax2.tick_params(colors=GRE)
h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); ax.legend(h1+h2,l1+l2,loc='lower right')
fig.savefig(O+'f3_serie.png'); plt.close()

# F4 missing heatmap
miss=brut.isna().T; order=miss.mean(axis=1).sort_values(ascending=False).index
fig,ax=plt.subplots(figsize=(7.2,4.2))
ax.imshow(miss.loc[order].values,aspect='auto',cmap='Greys',interpolation='nearest')
ax.set_yticks(range(len(order))); ax.set_yticklabels(order,fontsize=6)
yrs=[i for i,d in enumerate(brut.index) if d.isocalendar().week==1 and i>0]+[0]
ax.set_xticks(sorted(yrs)); ax.set_xticklabels([str(brut.index[i].isocalendar().year) for i in sorted(yrs)],fontsize=7)
ax.set_xlabel(T('Semaine épidémiologique (noir : semaine manquante)','Epidemiological week (black: missing week)'))
for s in ['top','right','left','bottom']: ax.spines[s].set_visible(False)
fig.savefig(O+'f4_manquants.png'); plt.close()

# F5 STL
s=pd.read_csv(A+'stl.csv',index_col=0,parse_dates=True)
fig,axs=plt.subplots(4,1,figsize=(7.2,5.6),sharex=True)
for ax,col,lab in zip(axs,['obs','trend','seas','resid'],[T('Observé','Observed'),T('Tendance','Trend'),T('Saisonnalité','Seasonal'),T('Résidu','Remainder')]):
    if col=='resid': ax.bar(s.index,s[col],width=5,color=GRE)
    else: ax.plot(s.index,s[col],color=NAVY if col!='seas' else ORA,lw=1)
    ax.set_ylabel(lab,fontsize=8)
fig.align_ylabels(); fig.savefig(O+'f5_stl.png'); plt.close()

# F6 seasonal index vs rain
im=pd.read_csv(A+'indices_mensuels.csv',index_col=0)
fig,ax=plt.subplots(figsize=(7.2,3))
ax.bar(range(1,13),im.pluie_pct,color='#9ecae1',label=T('Pluie (% du cumul annuel)','Rainfall (% of annual total)'))
ax.set_ylabel(T('Pluie (%)','Rainfall (%)')); ax.set_xticks(range(1,13)); ax.set_xticklabels(mois)
ax2=ax.twinx(); ax2.plot(range(1,13),im.indice,color=RED,marker='o',ms=4,lw=1.5,label=T('Indice saisonnier des cas','Seasonal index of cases'))
ax2.axhline(1,color=RED,lw=0.6,ls=':'); ax2.set_ylabel(T('Indice saisonnier','Seasonal index'),color=RED); ax2.spines['right'].set_visible(True); ax2.set_ylim(0.75,1.3)
h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); ax.legend(h1+h2,l1+l2,loc='upper left')
fig.savefig(O+'f6_indices.png'); plt.close()

# F7 ACF/PACF
a=pd.read_csv(A+'acf.csv',index_col=0); p=pd.read_csv(A+'pacf.csv',index_col=0); n=len(y); ci=1.96/np.sqrt(n)
fig,axs=plt.subplots(2,2,figsize=(7.2,4.4))
for ax,ser,t in [(axs[0,0],a.acf,T('ACF – niveau','ACF – level')),(axs[0,1],p.pacf,T('PACF – niveau','PACF – level')),(axs[1,0],a.acf_d1,T('ACF – différence première','ACF – first difference')),(axs[1,1],p.pacf_d1,T('PACF – différence première','PACF – first difference'))]:
    ax.vlines(ser.index,0,ser.values,color=NAVY,lw=1); ax.axhline(0,color='k',lw=0.5); ax.fill_between(ser.index,-ci,ci,color=GRE,alpha=0.25,lw=0); ax.set_title(t,fontsize=8.5); ax.set_xlabel(T('Décalage (semaines)','Lag (weeks)'),fontsize=7.5)
fig.tight_layout(); fig.savefig(O+'f7_acf.png'); plt.close()

# F8 correlation rain lags
from analyse_districts import correlations_district
cc=pd.read_csv(D+'climat_hebdo_2018_2025.csv',parse_dates=['date']); pr=cc.groupby('date').pluie_mm.mean()
tend=y.rolling(52,center=True,min_periods=26).mean(); yd=y/tend; p4=pr.rolling(4).sum(); w=p4.index.isocalendar().week.values; an=p4-p4.groupby(w).transform('mean')
lags=range(13); r1=[yd.corr(p4.shift(k).reindex(y.index)) for k in lags]; r2=[yd.corr(an.shift(k).reindex(y.index)) for k in lags]
fig,ax=plt.subplots(figsize=(7.2,2.9)); wdt=0.38
ax.bar(np.array(lags)-wdt/2,r1,wdt,color=NAVY,label=T('Cumul de pluie (4 sem.)','4-week rainfall'))
ax.bar(np.array(lags)+wdt/2,r2,wdt,color=ORA,label=T('Anomalie de pluie','Rainfall anomaly'))
ax.axhline(0,color='k',lw=0.5); ci=1.96/np.sqrt(len(y)); ax.axhspan(-ci,ci,color=GRE,alpha=0.2,lw=0)
ax.set_xlabel(T('Décalage (semaines)','Lag (weeks)')); ax.set_ylabel(T('Corrélation (cas sans tendance)','Correlation (detrended cases)')); ax.set_xticks(list(lags)); ax.legend(loc='upper left')
fig.savefig(O+'f8_correlation.png'); plt.close()

# F9 maps 3 panels
tab=pd.read_csv(str(RES)+'/districts/tableau_districts.csv',index_col=0)
fig,axs=plt.subplots(1,3,figsize=(7.4,4))
carte(axs[0],tab.corr_lag8,'RdBu_r',-0.6,0.6,T('A. Corrélation cas–pluie\n(décalage 8 sem.)','A. Case–rain correlation\n(8-week lag)'),'r')
carte(axs[1],tab.MAE_rel_xgbglobal_h4,'RdYlGn_r',0.7,1.3,T('B. Erreur relative du modèle\nglobal (h = 4)','B. Relative error of the\nglobal model (h = 4)'),T('MAE / MAE naïf','MAE / naive MAE'))
carte(axs[2],tab.pct_manquant,'Greys',0,50,T('C. Semaines\nmanquantes','C. Missing\nweeks'),'%')
fig.savefig(O+'f9_cartes.png'); plt.close()

# F10 regional forecasts h4
P=pd.read_csv(str(RES)+'/regional_climat/previsions_test.csv',parse_dates=['date_cible']); P=P[P.horizon==4]
fig,ax=plt.subplots(figsize=(7.2,3))
r=P.drop_duplicates('date_cible').set_index('date_cible').reel; ax.plot(r.index,r,color='k',lw=1.6,label=T('Observé','Observed'))
for mname,col,ls in [('Naïf',GRE,':'),('ARIMA',TEAL,'-'),('Prophet','#7b5ea7','-'),('XGBoost',RED,'-')]:
    s=P[P.modele==mname].set_index('date_cible').prevu; ax.plot(s.index,s,color=col,lw=0.9,ls=ls,label=T(mname,'Naive' if mname=='Naïf' else mname))
ax.set_ylabel(T('Cas par semaine','Cases per week')); ax.legend(ncol=5,loc='upper left')
fig.savefig(O+'f10_previsions.png'); plt.close()

# F11 relative MAE per district dot plot h4
Q=pd.read_csv(str(RES)+'/districts/previsions_districts.csv'); Q=Q[Q.observe&(Q.horizon==4)]; Q['ae']=(Q.reel-Q.prevu).abs()
M=Q.groupby(['district','modele']).ae.mean().unstack(); Rr=M.div(M['Naïf'],axis=0)[['XGBoost global','ARIMA','XGBoost local']].sort_values('XGBoost global')
fig,ax=plt.subplots(figsize=(7.2,5.2))
for col,cl,mk,lab in [('XGBoost local',GRE,'s',T('XGBoost local','Local XGBoost')),('ARIMA',TEAL,'^','ARIMA'),('XGBoost global',RED,'o',T('XGBoost global','Global XGBoost'))]:
    ax.scatter(Rr[col],range(len(Rr)),color=cl,marker=mk,s=18,label=lab,zorder=3)
ax.axvline(1,color='k',lw=0.7,ls='--'); ax.set_yticks(range(len(Rr))); ax.set_yticklabels(Rr.index,fontsize=6.5)
ax.set_xlabel(T('MAE relative au modèle naïf (h = 4 semaines) — inférieure à 1 : meilleur','MAE relative to naive model (h = 4 weeks) — below 1: better'))
ax.grid(axis='y',color='#eee',lw=0.5); ax.legend(loc='lower right')
fig.savefig(O+'f11_districts.png'); plt.close()

# F12 importance
imp=pd.read_csv(A+'importance.csv',index_col=0).iloc[:,0]
names={'lag_0':T('Cas semaine t','Cases week t'),'moy_13':T('Moyenne 13 sem.','13-week mean'),'lag_1':T('Cas t−1','Cases t−1'),'niveau_district':T('Niveau du district','District level'),
 'lag_3':T('Cas t−3','Cases t−3'),'lag_2':T('Cas t−2','Cases t−2'),'moy_4':T('Moyenne 4 sem.','4-week mean'),'meme_sem_an_passe':T('Même semaine an passé','Same week last year'),'sin_sem':T('Semaine (sinus)','Week (sine)'),'cos_sem':T('Semaine (cosinus)','Week (cosine)')}
imp=imp.sort_values()
fig,ax=plt.subplots(figsize=(7.2,2.9)); ax.barh([names[i] for i in imp.index],imp.values,color=NAVY)
for i,v in enumerate(imp.values): ax.text(v+0.3,i,f'{v:.1f}'.replace('.',',' if L=='fr' else '.'),va='center',fontsize=7)
ax.set_xlabel(T('Importance relative (gain, %)','Relative importance (gain, %)'))
fig.savefig(O+'f12_importance.png'); plt.close()
print('ok',L)
