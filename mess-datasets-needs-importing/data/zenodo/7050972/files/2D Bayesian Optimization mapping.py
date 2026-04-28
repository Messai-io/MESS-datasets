# coding: utf-8

import numpy as np
import pandas as pd
import glob
import os
from matplotlib import pyplot as plt
from sklearn.gaussian_process import kernels as sk_kern
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.preprocessing import MinMaxScaler

NDP = 121

def acq(pred_mean, pred_std, max_y, xi):
    EI = np.zeros(len(pred_mean))
    ind = np.where(pred_std != 0)[0]
    pred_mu = pred_mean[ind]
    pred_sigma = pred_std[ind]
    Z = (-max_y + pred_mean - xi) / pred_std
    EI.flat[ind] = pred_std * Z * np.array([norm.cdf(z) for z in Z]) + pred_std * np.array([norm.pdf(z) for z in Z])
    return EI.flat[ind]

def csvout(mat_data, scaler1, scaler2):
    na = np.vstack([np.arange(NDP)/100-0.1,np.arange(NDP)/100-0.1])
    vtrn = scaler1.inverse_transform(na)[0]
    ctrn = 10**scaler2.inverse_transform(na)[0]
    mat_df = pd.DataFrame(mat_data, columns=ctrn)
    v_df = pd.DataFrame(vtrn)
    concat_df = pd.concat([v_df,mat_df], axis=1)
    return concat_df

def main():
    filename = 'statistics summary.csv'

    mediators = ['RF','FMN','HNQ','AQDS']

    colnames = ['Poised Voltage', 'Mediator','Concentration','Maximum Slope','Enhancement Factor','Cost Performance']
    df = pd.read_csv(filename, skiprows=5,usecols=[1,2,3,4,7,9], names=colnames)


    for i in range(NDP):
        for j in range(NDP):
            if (i,j) == (0,0):
                ar = np.array([-0.1,-0.1])
            else:
                arij = np.array([0.01*i-0.1,0.01*j-0.1])
                ar = np.append(ar,arij, axis=0)

    test_x = ar.reshape(-1,2)

    vlist_p = ((np.arange(6)*100-300)+350)//5
    vlist_v = [400,300,200,100,0,-100]
    clist = 50*(np.arange(3)+0.2)
    clist_p = clist.astype(int)
    clist_v = [1,10,100]


    header = ['Mediator', 'Maximum CP', 'Poised Voltage for Maximum CP', 'Mediator Concentration for Maximum CP', 'Maximum EI', 'Poised Voltage for Maximum EI', 'Mediator Concentration for Maximum EI']
    param_list = []

    for i in range(len(mediators)):
        dfrf = df[df['Mediator']==mediators[i]].copy()

        dfrf['Concentration'] = np.log10(dfrf['Concentration'])

        scaler_v = MinMaxScaler()
        scaler_v.fit(np.array([-300,200]).reshape(-1,1))
        dfrf['Poised Voltage'] = scaler_v.transform(dfrf['Poised Voltage'].values.reshape(-1,1))

        scaler_c = MinMaxScaler()
        scaler_c.fit(np.array([0, 2]).reshape(-1,1))
        dfrf['Concentration'] = scaler_c.transform(dfrf['Concentration'].values.reshape(-1,1))

        x_train = np.stack([dfrf['Poised Voltage'], dfrf['Concentration']], axis=1)
        y_train = dfrf['Cost Performance'].values

        max_y = np.max(y_train)
        std_y = np.std(y_train)
        xi = std_y * 0.01

        kernel = sk_kern.RBF(1, (1e-1, 1e2))

        clf = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-10, 
            optimizer="fmin_l_bfgs_b", 
            n_restarts_optimizer=20,
            normalize_y=True)

        clf.fit(x_train.reshape(-1,2), y_train)
        clf.kernel_

        pred_mean, pred_std= clf.predict(test_x, return_std=True)

        pred_mean_mat = pred_mean.reshape(-1,NDP)
        EI = acq(pred_mean, pred_std, max_y, xi).reshape(-1,NDP)

        mat = np.flipud(pred_mean_mat)
        EImat = np.flipud(EI)


        fontsize1 = 20
        fontsize2 = 15

        fig, ax = plt.subplots(figsize=(8,8))
        im = ax.imshow(mat, cmap='jet', vmin=0, vmax=2, interpolation='bilinear')
        cb = plt.colorbar(im,fraction=0.04, pad=0.04)
        plt.xlabel('Concentration (uM)', fontsize=fontsize1)
        plt.ylabel('Poised Voltage (mV)', fontsize=fontsize1)

        ax.set_xticks(clist_p)
        ax.set_xticklabels(clist_v)
        ax.set_yticks(vlist_p)
        ax.set_yticklabels(vlist_v)

        plt.xticks(fontsize = fontsize2)
        plt.yticks(fontsize = fontsize2)
        plt.title('Cost Performance ('+ mediators[i]+')', fontsize=25)

        cb.ax.tick_params(labelsize=15)

        plt.savefig(mediators[i]+"_CP_Graph_extended_SHE.png")

        fig, ax = plt.subplots(figsize=(8,8))
        im = ax.imshow(EImat, cmap='hot', vmin=0, vmax=0.16, interpolation='bilinear')
        cb = plt.colorbar(im,fraction=0.04, pad=0.04)
        plt.xlabel('Concentration (uM)', fontsize=fontsize1)
        plt.ylabel('Poised Voltage (mV)', fontsize=fontsize1)

        ax.set_xticks(clist_p)
        ax.set_xticklabels(clist_v)
        ax.set_yticks(vlist_p)
        ax.set_yticklabels(vlist_v)

        plt.xticks(fontsize = fontsize2)
        plt.yticks(fontsize = fontsize2)
        plt.title('Expected Improvement ('+ mediators[i]+')', fontsize=25)

        cb.ax.tick_params(labelsize=15)

        plt.savefig(mediators[i]+"_EI_Graph_extended_SHE.png")

        df_mat = csvout(pred_mean_mat, scaler_v, scaler_c)
        df_EI = csvout(EI, scaler_v, scaler_c)
        df_mat.to_csv(mediators[i]+'_CP_2Ddata_extended.csv',index=False)
        df_EI.to_csv(mediators[i]+'_EI_2Ddata_extended.csv',index=False)

        cp_max, cp_argmax_index = max(pred_mean), pred_mean.argmax()
        cp_argmax = test_x[cp_argmax_index]
        ei_max, ei_argmax_index = EI.max(), EI.argmax()
        ei_argmax = test_x[ei_argmax_index]

        param_list.append([mediators[i],
                           cp_max,
                           scaler_v.inverse_transform([[cp_argmax[0]],[0]])[0][0],
                           10**scaler_c.inverse_transform([[cp_argmax[1]],[0]])[0][0],
                           ei_max,
                           scaler_v.inverse_transform([[ei_argmax[0]],[0]])[0][0],
                           10**scaler_c.inverse_transform([[ei_argmax[1]],[0]])[0][0]
                          ])

    df_param = pd.DataFrame(param_list)
    df_param.to_csv('estimated parameters_extended.csv', header=header, index=False)


if __name__ == "__main__":
    main()
