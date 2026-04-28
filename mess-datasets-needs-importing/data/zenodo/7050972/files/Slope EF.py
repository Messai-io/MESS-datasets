# coding: utf-8

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

def Error1(x,df_y,sigma_x,df_sigma_y):
    return np.sqrt(((df_y/x**2)**2)*sigma_x**2+((1/x)**2)*df_sigma_y**2)

def main():
filepath_smp = 'Data with average of four data sets for impact of mediators\\'
filename_ref = 'Poised potentials without mediators.xlsx'
filename_smp = ['+200 mV.xlsx','-100 mV.xlsx','-200 mV.xlsx','-300 mV.xlsx']

window = 60
A_el = 0.07069 #Surface area of the electrode: 0.07069 cm2

    xl = []
    dflr = []
    dfls = []
    dflsm = []

    df_ref = pd.read_excel(filepath_smp+filename_ref, header=1)
    xl.append(df_ref.iloc[:,0])
    df_ref_s = df_ref.iloc[:,1:].rolling(window).mean().diff()/A_el/1000/(1/60) #uA/(cm2ÅE•h)
    dflsm.append(df_ref_s.max())

    dflr.append(df_ref.iloc[:,1:])
    dfls.append(df_ref_s)

    for i in range(len(filename_smp)):
        df_smp = pd.read_excel(filepath_smp+filename_smp[i], header=0, sheet_name='raw data processed')
        xl.append(df_smp.iloc[:,0])
        df_smp_s = df_smp.iloc[:,1:].rolling(window).mean().diff()/A_el/1000/(1/60) #uA/(cm2ÅE•h)
        dflr.append(df_smp.iloc[:,1:])
        dfls.append(df_smp_s)
        dflsm.append(df_smp_s.max())

    datl = []

    #Calculating mean, standard deviation, and standard error of the MS for reference data
    for i in range(4):
        datl.append([dflsm[0].iloc[24*i:24*(i+1)].mean(),
                     dflsm[0].iloc[24*i:24*(i+1)].std(),
                     dflsm[0].iloc[24*i:24*(i+1)].std()/np.sqrt(dflsm[0].iloc[24*i:24*(i+1)].count())])

    #Calculating mean, standard deviation, and standard error of the MS for sample data 
    for j in range(4):
        for i in range(24):
            datl.append([dflsm[j+1].iloc[4*i:4*(i+1)].mean(),
                         dflsm[j+1].iloc[4*i:4*(i+1)].std(),
                         dflsm[j+1].iloc[4*i:4*(i+1)].std()/np.sqrt(dflsm[j+1].iloc[4*i:4*(i+1)].count())])


    vol = [200, -100, -200, -300]
    med = ['RF','FMN','HNQ','AQDS']
    conc = [1,2.5,10,25,50,100]

    cond = []

    for i in range(len(vol)):
        cond.append([vol[i], 'None', 0])

    for i in range(len(vol)*len(med)*len(conc)):
        condi = [vol[i//(len(med)*len(conc))],
                 med[(i//len(conc))%len(med)],
                 conc[i%len(conc)]]
        cond.append(condi)

    dfcond = pd.DataFrame(cond)
    dfdatl = pd.DataFrame(datl)

    for i in range(4):
        dfdatl[i+3] = np.nan

    for i in range(len(vol)):
        dfdatl[3][4+24*i:4+24*(i+1)] = (dfdatl.iloc[4+24*i:4+24*(i+1),0]-dfdatl.iloc[i,0])/dfdatl.iloc[i,0]
        dfdatl[4][4+24*i:4+24*(i+1)] = Error1(dfdatl.iloc[i,0],dfdatl.iloc[4+24*i:4+24*(i+1),0],dfdatl.iloc[i,2],dfdatl.iloc[4+24*i:4+24*(i+1),2])
        dfdatl[5][4+24*i:4+24*(i+1)] = dfdatl[3][4+24*i:4+24*(i+1)]/dfcond[2][4+24*i:4+24*(i+1)]
        dfdatl[6][4+24*i:4+24*(i+1)] = dfdatl[4][4+24*i:4+24*(i+1)]/dfcond[2][4+24*i:4+24*(i+1)]

    dfconct = pd.concat([dfcond,dfdatl],axis=1)
    dfconct.columns= ['Poised Voltage (mV)',
                      'Mediator','Mediator Concentration (uM)',
                      'Mean Maximum Slope (uA/(cm2*h))',
                      'Standard Deviation (uA/(cm2*h))',
                      'Standard Error (uA/(cm2*h))',
                      'Enhancement Factor',
                      'Standard Error',
                      'Cost Performance (1/uM)',
                      'Standard Error (1/uM)']

    dfconct.to_csv('statistics summary.csv')

if __name__ == "__main__":
    main()
