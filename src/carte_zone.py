import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
import sys, json, warnings; warnings.filterwarnings('ignore')
import pandas as pd, numpy as np, geopandas as gpd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from shapely.geometry import shape
from shapely.ops import unary_union
L=sys.argv[1]; T=lambda fr,en: fr if L=='fr' else en
NAVY='#1f3b63'
plt.rcParams.update({'font.family':'DejaVu Sans','savefig.dpi':300})
geo=json.load(open(str(DATA/'districts_sante.geojson'),encoding='utf-8'))['features']
G={f['properties']['district']:shape(f['geometry']) for f in geo}
PT={d:g.representative_point() for d,g in G.items()}
NF=pd.read_csv(str(DATA/'formations_par_district.csv'),index_col=0).iloc[:,0]
NOMS={'Kousseri':'Kousséri','Kaele':'Kaélé','Mogode':'Mogodé','Pette':'Petté','Guere':'Guéré','Tokombere':'Tokombéré','Vele':'Vélé','Meri':'Méri','Kar Hay':'Kar-Hay'}
nom=lambda d: NOMS.get(d,d)
DEP={'Logone-et-Chari':['Kousseri','Goulfey','Makary','Fotokol','Mada'],
 'Diamaré':['Maroua 1','Maroua 2','Maroua 3','Bogo','Gazawa','Meri','Pette'],
 'Mayo-Danay':['Yagoua','Guere','Kar Hay','Maga','Vele'],
 'Mayo-Kani':['Kaele','Guidiguis','Mindif','Moulvoudaye','Moutourwa'],
 'Mayo-Sava':['Mora','Kolofata','Tokombere'],
 'Mayo-Tsanaga':['Mokolo','Bourha','Hina','Koza','Mogode','Mozogo','Roua']}
COL={'Logone-et-Chari':'#f6d77a','Diamaré':'#9cc3e6','Mayo-Danay':'#f5b27a','Mayo-Kani':'#c9b3e0','Mayo-Sava':'#f2a3ad','Mayo-Tsanaga':'#a8d5a2'}
D2={d:k for k,v in DEP.items() for d in v}
assert set(D2)==set(G)
POS={'Mozogo':(13.48,11.12),'Mokolo':(13.42,10.82),'Koza':(13.89,10.9),'Maroua 2':(14.27,10.87),'Gazawa':(14.03,10.40),
     'Maroua 1':(14.26,10.52),'Moulvoudaye':(14.86,10.42),'Kolofata':(14.02,11.17),'Fotokol':(14.22,12.46),'Hina':(13.79,10.40)}
fig=plt.figure(figsize=(12,8.6))
# --- centre : carte
ax=fig.add_axes([0.24,0.04,0.52,0.92])
for d,g in G.items():
    for p in ([g] if g.geom_type=='Polygon' else list(g.geoms)):
        xs,ys=p.exterior.xy; ax.fill(xs,ys,color=COL[D2[d]],ec='#666',lw=0.5)
# limites de département (contour épais)
for k,v in DEP.items():
    u=unary_union([G[d] for d in v])
    for p in ([u] if u.geom_type=='Polygon' else list(u.geoms)):
        xs,ys=p.exterior.xy; ax.plot(xs,ys,color='#333',lw=1.1)
for d in G:
    x,y=PT[d].x,PT[d].y; lx,ly=POS.get(d,(x,y))
    if np.hypot(lx-x,ly-y)>0.12: ax.plot([x,lx+0.02],[y,ly],color='#333',lw=0.5)
    ax.plot(x,y,'o',ms=2,color='#222',zorder=5)
    ax.text(lx,ly+0.045,nom(d),fontsize=6.6,ha='left',va='center',zorder=6,path_effects=[pe.withStroke(linewidth=1.8,foreground='white')])
    ax.text(lx-0.035,ly+0.045,str(NF[d]),fontsize=5.3,ha='center',va='center',color='white',fontweight='bold',zorder=7,
            bbox=dict(boxstyle='circle,pad=0.22',fc=NAVY,ec='white',lw=0.6))
ax.set_xlim(13.25,15.85); ax.set_ylim(9.82,13.15); ax.set_aspect('equal')
ax.set_xticks([13.5,14,14.5,15,15.5]); ax.set_yticks([10,10.5,11,11.5,12,12.5,13])
ax.set_xticklabels([f'{v:g}°E'.replace('.',',' if L=='fr' else '.') for v in ax.get_xticks()],fontsize=7)
ax.set_yticklabels([f'{v:g}°N'.replace('.',',' if L=='fr' else '.') for v in ax.get_yticks()],fontsize=7)
ax.grid(color='#e3e3e3',lw=0.4,zorder=0); ax.set_axisbelow(True)
ax.text(13.32,13.08,'NIGERIA',fontsize=8,color='#888',style='italic',va='top'); ax.text(15.78,11.2,T('TCHAD','CHAD'),fontsize=8,color='#888',style='italic',ha='right')
ax.text(15.25,13.0,T('Lac Tchad','Lake Chad'),fontsize=7,color='#3b7dbf',style='italic')
x0,y0=13.35,9.92; dx=50/(111.32*np.cos(np.radians(y0)))
ax.plot([x0,x0+dx],[y0,y0],color='k',lw=2.5); ax.plot([x0,x0+dx/2],[y0,y0],color='white',lw=1.4); ax.text(x0+dx/2,y0+0.05,'50 km',ha='center',fontsize=7)
ax.annotate('N',xy=(15.72,13.07),xytext=(15.72,12.82),ha='center',fontsize=10,fontweight='bold',arrowprops=dict(arrowstyle='-|>',lw=1.2,color='k'))
ax.set_title(T("Région de l'Extrême-Nord : 32 districts de santé","Far North Region: 32 health districts"),fontsize=12,fontweight='bold',color=NAVY)
# --- gauche : cartes de situation + légende
w=gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
af=w[w.continent=='Africa']; cm=w[w.name=='Cameroon']
far=gpd.GeoSeries([unary_union(list(G.values()))],crs=4326)
a1=fig.add_axes([0.01,0.66,0.2,0.3]); af.plot(ax=a1,color='#e9e9e9',ec='#999',lw=0.3); cm.plot(ax=a1,color='#f6d77a',ec='#555',lw=0.5)
a1.set_xlim(-19,53); a1.set_ylim(-36,38); a1.set_xticks([]); a1.set_yticks([]); a1.set_title(T('AFRIQUE','AFRICA'),fontsize=8,fontweight='bold',loc='left')
a1.annotate(T('Cameroun','Cameroon'),xy=(12.5,5.5),xytext=(-15,-8),fontsize=7,arrowprops=dict(arrowstyle='-|>',lw=0.8))
a2=fig.add_axes([0.01,0.33,0.2,0.31]); w.plot(ax=a2,color='#f2f2f2',ec='#aaa',lw=0.3); cm.plot(ax=a2,color='#e9e9e9',ec='#555',lw=0.6); far.plot(ax=a2,color='#d9534f',ec='#555',lw=0.5)
a2.set_xlim(8,17); a2.set_ylim(1.5,13.3); a2.set_xticks([]); a2.set_yticks([]); a2.set_title('CAMEROUN' if L=='fr' else 'CAMEROON',fontsize=8,fontweight='bold',loc='left')
a2.annotate(T('Extrême-Nord','Far North'),xy=(14.3,11.2),xytext=(9,10.7),fontsize=7,arrowprops=dict(arrowstyle='-|>',lw=0.8))
for a in (a1,a2):
    for s in a.spines.values(): s.set_color('#888')
a3=fig.add_axes([0.01,0.04,0.2,0.27]); a3.axis('off')
a3.text(0,1,T('Légende','Legend'),fontsize=9,fontweight='bold',va='top')
items=[Line2D([0],[0],marker='o',color='w',markerfacecolor='#222',markersize=4,label=T('Centre du district','District centre')),
       Line2D([0],[0],marker='o',color='w',markerfacecolor=NAVY,markersize=9,label=T('Nombre de formations\nsanitaires déclarantes','Number of reporting\nhealth facilities')),
       Line2D([0],[0],color='#333',lw=1.2,label=T('Limite de département','Department boundary')),
       Line2D([0],[0],color='#666',lw=0.6,label=T('Limite de district de santé','Health district boundary'))]
items+=[Patch(fc=COL[k],ec='#555',label=k) for k in DEP]
a3.legend(handles=items,loc='upper left',bbox_to_anchor=(0,0.93),fontsize=6.6,frameon=False,title=None,handlelength=1.6,labelspacing=0.55)
# --- droite : tableau des districts
a4=fig.add_axes([0.79,0.04,0.2,0.92]); a4.axis('off'); a4.set_xlim(0,1); a4.set_ylim(0,1)
rows=sum(len(v)+1 for v in DEP.values())+1; h=1/rows; y=1
a4.add_patch(Rectangle((0,y-h),1,h,fc=NAVY)); a4.text(0.06,y-h/2,T('District de santé','Health district'),color='white',fontsize=7,fontweight='bold',va='center')
a4.text(0.94,y-h/2,T('Formations','Facilities'),color='white',fontsize=6.5,fontweight='bold',va='center',ha='right'); y-=h
for k,v in DEP.items():
    a4.add_patch(Rectangle((0,y-h),1,h,fc=COL[k],ec='white')); a4.text(0.5,y-h/2,k,fontsize=7,fontweight='bold',va='center',ha='center'); y-=h
    for d in sorted(v,key=lambda z:nom(z)):
        a4.add_patch(Rectangle((0,y-h),1,h,fc='white',ec='#ddd',lw=0.5))
        a4.text(0.06,y-h/2,nom(d),fontsize=6.8,va='center'); a4.text(0.9,y-h/2,str(NF[d]),fontsize=6.8,va='center',ha='right'); y-=h
fig.text(0.24,0.012,T("Sources : limites des districts et formations sanitaires : DHIS-Minsante-CM ; limites des pays : Natural Earth.",
 "Sources: district boundaries and health facilities: DHIS-Minsante-CM; country boundaries: Natural Earth."),fontsize=6,color='#555')
fig.savefig(str(FIG/f'{L}_zone_etude.png'),dpi=300,bbox_inches='tight'); print('ok')
