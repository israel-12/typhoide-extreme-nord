import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
import pandas as pd, numpy as np, json, sys, warnings; warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from shapely.geometry import shape
from adjustText import adjust_text
pass
from pipeline_typhoide import charger_donnees
L=sys.argv[1]; T=lambda fr,en: fr if L=='fr' else en
A=str(RES/'exploration')+'/'; D=str(DATA)+'/'; O=str(FIG)+f'/{L}_'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'savefig.dpi':300,'savefig.bbox':'tight'})
NAVY='#1f3b63'
NOMS={'Kousseri':'Kousséri','Kaele':'Kaélé','Mogode':'Mogodé','Pette':'Petté','Guere':'Guéré','Tokombere':'Tokombéré','Vele':'Vélé','Meri':'Méri','Kar Hay':'Kar-Hay'}
geo=json.load(open(D+'districts_sante.geojson',encoding='utf-8'))['features']
G={f['properties']['district']:shape(f['geometry']) for f in geo}
PT={d:g.representative_point() for d,g in G.items()}
AREA={d:g.area for d,g in G.items()}
brut=charger_donnees(D+'df_2019_2025.xlsx')
tab=pd.read_csv(str(RES)+'/districts/tableau_districts.csv',index_col=0)

def fond(ax,val=None,cmap=None,vmin=None,vmax=None,fc='#eef2f7'):
    cm=plt.get_cmap(cmap) if cmap else None; norm=plt.Normalize(vmin,vmax) if cmap else None
    for d,g in G.items():
        polys=[g] if g.geom_type=='Polygon' else list(g.geoms)
        c=cm(norm(val[d])) if cmap else fc
        for p in polys:
            xs,ys=p.exterior.xy; ax.fill(xs,ys,color=c,ec='#555',lw=0.45)
    ax.set_aspect('equal'); return cm,norm

# positions d'étiquettes ajustées à la main pour les districts serrés (lon, lat)
POS={'Mozogo':(13.45,11.12),'Mokolo':(13.40,10.80),'Koza':(13.88,10.90),'Maroua 2':(14.40,10.80),
     'Gazawa':(14.02,10.40),'Maroua 1':(14.27,10.52),'Moulvoudaye':(14.86,10.42),'Kolofata':(14.02,11.16),'Fotokol':(14.22,12.46),'Hina':(13.78,10.40)}
def etiquettes(ax,texte,fs=6):
    for d in G:
        x,y=PT[d].x,PT[d].y; lx,ly=POS.get(d,(x,y))
        if (lx,ly)!=(x,y) and np.hypot(lx-x,ly-y)>0.12:
            ax.plot([x,lx],[y,ly],color='#333',lw=0.5,zorder=4); ax.plot(x,y,'o',ms=1.6,color='#333',zorder=4)
        ax.text(lx,ly,texte(d),fontsize=fs,ha='center',va='center',linespacing=0.95,color='#111',zorder=5,
                path_effects=[pe.withStroke(linewidth=2,foreground='white')])

def habillage(ax,echelle=True):
    ax.set_xlim(13.25,15.85); ax.set_ylim(9.85,13.15)
    ax.set_xticks([13.5,14,14.5,15,15.5]); ax.set_yticks([10,10.5,11,11.5,12,12.5,13])
    ax.set_xticklabels([f'{v:g}°E'.replace('.',',' if L=='fr' else '.') for v in ax.get_xticks()],fontsize=6)
    ax.set_yticklabels([f'{v:g}°N'.replace('.',',' if L=='fr' else '.') for v in ax.get_yticks()],fontsize=6)
    ax.tick_params(length=2); ax.grid(color='#ddd',lw=0.3,zorder=0)
    for s in ax.spines.values(): s.set_color('#999'); s.set_linewidth(0.6)
    if echelle:
        x0,y0=13.35,12.75; km=50; dx=km/(111.32*np.cos(np.radians(y0)))
        ax.plot([x0,x0+dx],[y0,y0],color='k',lw=2); ax.plot([x0,x0+dx/2],[y0,y0],color='white',lw=1.2)
        ax.text(x0+dx/2,y0+0.06,'50 km',ha='center',fontsize=6)
        ax.annotate('N',xy=(15.7,13.05),xytext=(15.7,12.8),ha='center',fontsize=8,fontweight='bold',arrowprops=dict(arrowstyle='-|>',color='k',lw=1))

nom=lambda d: NOMS.get(d,d)
def fmt(v,dec):
    v=0.0 if abs(v)<0.5*10**(-dec) else v
    s=f'{v:.{dec}f}'
    return (s.replace('.',',') if L=='fr' else s).replace('-','−')

# Carte de référence : noms des districts
fig,ax=plt.subplots(figsize=(5.8,6.9))
fond(ax); etiquettes(ax,lambda d: nom(d),fs=6.6); habillage(ax)
ax.set_title(T('Région de l\'Extrême-Nord : 32 districts de santé','Far North Region: 32 health districts'),fontsize=10,fontweight='bold',color=NAVY)
ax.text(13.3,13.1,T('Nigeria (ouest)','Nigeria (west)'),fontsize=6.5,style='italic',color='#666',va='top')
ax.text(15.8,11.0,T('Tchad (est)','Chad (east)'),fontsize=6.5,style='italic',color='#666',ha='right')
fig.savefig(O+'f2a_reference.png'); plt.close()

def carte_valeurs(ax,val,cmap,vmin,vmax,titre,lab,dec,ech=True,fs=5.8):
    cm,norm=fond(ax,val,cmap,vmin,vmax)
    etiquettes(ax,lambda d: f'{nom(d)}\n{fmt(val[d],dec)}',fs=fs); habillage(ax,ech)
    ax.set_title(titre,fontsize=9,fontweight='bold',color=NAVY)
    cb=plt.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cm),ax=ax,shrink=0.45,pad=0.02,aspect=25); cb.set_label(lab,fontsize=7); cb.ax.tick_params(labelsize=6)

def une_carte(nomfic,val,cmap,vmin,vmax,titre,lab,dec):
    fig,ax=plt.subplots(figsize=(5.8,6.9))
    carte_valeurs(ax,val,cmap,vmin,vmax,titre,lab,dec,fs=5.8)
    fig.savefig(O+nomfic); plt.close()
une_carte('f2b_cas.png',brut.mean(),'YlOrRd',0,160,T('Cas hebdomadaires moyens par district, 2019-2025','Mean weekly cases by district, 2019–2025'),T('cas/semaine','cases/week'),1)
une_carte('f2c_manquants.png',brut.isna().mean()*100,'Greys',0,50,T('Semaines manquantes par district (%)','Missing weeks by district (%)'),'%',1)
une_carte('f9a_correlation.png',tab.corr_lag8,'RdBu_r',-0.6,0.6,T('Corrélation cas–pluie (décalage de 8 semaines)','Case–rain correlation (8-week lag)'),'r',2)
une_carte('f9b_erreur.png',tab.MAE_rel_xgbglobal_h4,'RdYlGn_r',0.7,1.3,T('Erreur relative du modèle global à 4 semaines','Relative error of the global model at 4 weeks'),T('MAE / MAE naïf','MAE / naive MAE'),2)
print('ok',L)

# Figure composite 2×2 : valeurs seules (les noms figurent sur la carte de référence)
def etiq_valeurs(ax,val,dec,fs=5.6):
    for d in G:
        x,y=PT[d].x,PT[d].y
        ax.text(x,y,fmt(val[d],dec),fontsize=fs,ha='center',va='center',color='#111',zorder=5,path_effects=[pe.withStroke(linewidth=1.6,foreground='white')])
fig,axs=plt.subplots(2,2,figsize=(7.2,8.6))
pan=[(brut.mean(),'YlOrRd',0,160,T('A. Cas hebdomadaires moyens','A. Mean weekly cases'),T('cas/semaine','cases/week'),0),
     (brut.isna().mean()*100,'Greys',0,50,T('B. Semaines manquantes (%)','B. Missing weeks (%)'),'%',0),
     (tab.corr_lag8,'RdBu_r',-0.6,0.6,T('C. Corrélation cas–pluie (8 sem.)','C. Case–rain correlation (8 wk)'),'r',2),
     (tab.MAE_rel_xgbglobal_h4,'RdYlGn_r',0.7,1.3,T('D. Erreur relative du modèle global','D. Relative error of global model'),T('MAE / MAE naïf','MAE / naive MAE'),2)]
for ax,(v,cmap,a,b,t,lab,dec) in zip(axs.flat,pan):
    cm,norm=fond(ax,v,cmap,a,b); etiq_valeurs(ax,v,dec)
    ax.set_xlim(13.3,15.8); ax.set_ylim(9.85,13.15); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(t,fontsize=9,fontweight='bold',color=NAVY,loc='left')
    cb=plt.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cm),ax=ax,shrink=0.55,pad=0.0,aspect=22); cb.set_label(lab,fontsize=7); cb.ax.tick_params(labelsize=6)
fig.tight_layout(h_pad=0.8,w_pad=0.2); fig.savefig(O+'cartes_composite.png'); plt.close()
print('composite ok')
