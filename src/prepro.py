import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf
from statsmodels.tsa.seasonal import STL
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.arima.model import ARIMA
import sys; pass
from pipeline_typhoide import charger_donnees, imputer
R={}
brut=charger_donnees(str(DATA/'df_2019_2025.xlsx')); Y=imputer(brut); y=Y.sum(axis=1)
R['n_weeks'],R['n_dist']=brut.shape
# descriptive
desc=pd.DataFrame({'moy':brut.mean(),'med':brut.median(),'et':brut.std(),'min':brut.min(),'max':brut.max(),'manq':brut.isna().mean()*100,'total':brut.sum()})
desc.to_csv(str(RES/'exploration')+'/desc_districts.csv')
R['reg']=dict(mean=y.mean(),med=y.median(),sd=y.std(),cv=y.std()/y.mean(),min=y.min(),max=y.max(),skew=y.skew(),kurt=y.kurt())
# stationarity
def tests(s,name):
    s=s.dropna(); a=adfuller(s,autolag='AIC'); k=kpss(s,regression='c',nlags='auto')
    return dict(serie=name,adf=a[0],adf_p=a[1],adf_lags=a[2],kpss=k[0],kpss_p=k[1])
rows=[tests(y,'Niveau'),tests(np.log(y),'Logarithme'),tests(y.diff(),'Différence première'),tests(y.diff(52),'Différence saisonnière (52)')]
st=pd.DataFrame(rows); st.to_csv(str(RES/'exploration')+'/stationnarite.csv',index=False); print(st.round(3))
# districts stationarity counts
cnt=dict(adf_stat=0,kpss_stat=0,both=0)
for d in Y:
    s=np.log1p(Y[d]); a=adfuller(s)[1]; k=kpss(s,nlags='auto')[1]
    cnt['adf_stat']+=a<.05; cnt['kpss_stat']+=k>.05; cnt['both']+=(a<.05 and k>.05)
R['dist_stat']=cnt; print(cnt)
# STL
stl=STL(y,period=52,robust=True).fit()
var=np.var(stl.resid); R['stl_FT']=max(0,1-var/np.var(stl.trend+stl.resid)); R['stl_FS']=max(0,1-var/np.var(stl.seasonal+stl.resid))
pd.DataFrame({'obs':y,'trend':stl.trend,'seas':stl.seasonal,'resid':stl.resid}).to_csv(str(RES/'exploration')+'/stl.csv')
print('force tendance %.2f saison %.2f'%(R['stl_FT'],R['stl_FS']))
# monthly seasonal index (ratio to centered MA), like Shashvat
ratio=y/y.rolling(52,center=True,min_periods=26).mean()
si=ratio.groupby(ratio.index.month).mean(); si=si/si.mean()
c=pd.read_csv(str(DATA/'climat_hebdo_2018_2025.csv'),parse_dates=['date']); p=c.groupby('date').pluie_mm.mean()
pm=(p.groupby(p.index.month).sum()/p.sum()*100)
pd.DataFrame({'indice':si,'pluie_pct':pm}).to_csv(str(RES/'exploration')+'/indices_mensuels.csv'); print(si.round(2).to_dict())
# ACF / PACF
pd.DataFrame({'acf':acf(y,nlags=60),'acf_d1':acf(y.diff().dropna(),nlags=60)}).to_csv(str(RES/'exploration')+'/acf.csv')
pd.DataFrame({'pacf':pacf(y,nlags=30),'pacf_d1':pacf(y.diff().dropna(),nlags=30)}).to_csv(str(RES/'exploration')+'/pacf.csv')
lb=acorr_ljungbox(y,lags=[4,13,52]); R['lb_raw']=lb.lb_pvalue.tolist()
# ARIMA residual diagnostics on training (2019-2022)
tr=y.iloc[:len(y)-156]; m=ARIMA(tr.values,order=(2,1,1)).fit()
lbr=acorr_ljungbox(m.resid[1:],lags=[4,13,26]); R['lb_arima']=lbr.lb_pvalue.round(3).tolist(); R['arima_aic']=m.aic
R['arima_params']=dict(zip(m.param_names,np.round(m.params,3)))
# outliers Hampel (fenêtre centrée de 9 semaines, médiane et MAD de la fenêtre)
out=0; tot=0
for d in brut:
    v=brut[d].values
    for i in range(len(v)):
        if np.isnan(v[i]): continue
        w=v[max(0,i-4):i+5]; w=w[~np.isnan(w)]
        if len(w)<5: continue
        m=np.median(w); dd=1.4826*np.median(np.abs(w-m)); tot+=1
        out+= (dd>0 and abs(v[i]-m)>3*dd)
R['outliers']=int(out); R['outliers_pct']=out/brut.notna().sum().sum()*100; print('aberrantes',out)
# mean-variance (Taylor) across districts: log var = a + b log mean
mv=pd.DataFrame({'m':brut.mean(),'v':brut.var()}); b=np.polyfit(np.log(mv.m),np.log(mv.v),1); R['taylor_b']=b[0]; print('Taylor b',b[0])
# missing structure
miss=brut.isna(); R['miss_weeks_any']=int(miss.any(axis=1).sum()); R['miss_by_year']=miss.groupby(miss.index.year).mean().mean(axis=1).mul(100).round(1).to_dict()
miss.to_csv(str(RES/'exploration')+'/manquants.csv')
json.dump({k:(v if not isinstance(v,(np.floating,np.integer)) else float(v)) for k,v in R.items()},open(str(RES/'exploration')+'/R.json','w'),default=float,indent=1)
print(json.dumps(R,default=float,indent=0)[:1500])
