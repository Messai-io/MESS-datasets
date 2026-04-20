# coding: utf-8

import numpy as np
import pandas as pd
import glob
import os
from matplotlib import pyplot as plt
from sklearn.gaussian_process import kernels as sk_kern
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor

def plot_result(x_test, mean, std):
    plt.plot(x_test[:, 0], mean, color="C0", label="predict mean")
    plt.fill_between(x_test[:, 0], mean + std, mean - std, color="C0", alpha=.3,label= "1 sigma confidence")
    plt.plot(x_train, y_train, "o",label= "training data")

def acq(pred_mean, pred_std, max_y, xi):
    EI = np.zeros(len(pred_mean))
    ind = np.where(pred_std != 0)[0]
    pred_mu = pred_mean[ind]
    pred_sigma = pred_std[ind]
    Z = (-max_y + pred_mean - xi) / pred_std
    EI.flat[ind] = pred_std * Z * np.array([norm.cdf(z) for z in Z]) + pred_std * np.array([norm.pdf(z) for z in Z])
    return EI.flat[ind]

def main():
    filename = 'statistics summary.csv'

    colnames = ['Poised Voltage', 'Mediator','Concentration','Maximum Slope','Enhancement Factor','Cost Performance']
    df = pd.read_csv(filename, skiprows=5,usecols=[1,2,3,4,8,10], names=colnames)

    ap_v = [200,-100,-200,-300]
    conc = np.array([1,2.5,10,25,50,100])
    med = ['RF','FMN','HNQ','AQDS']

    x_train = np.log10(conc)

    kernel = sk_kern.RBF(1.0, (1e-1, 1e3)) + sk_kern.ConstantKernel(1.0, (1e-1, 1e3)) + sk_kern.WhiteKernel()


    clf = GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-10, 
        optimizer="fmin_l_bfgs_b", 
        n_restarts_optimizer=20,
        normalize_y=True)

    x_test = np.linspace(-1, 3., 200).reshape(-1, 1)

    nextx_s = []
    for j in range(len(ap_v)):
        nextx = []

        for i in range (len(med)):
            y_train = df.iloc[6*i+24*j:6*(i+1)+24*j,5]
            print(y_train)

            max_y = np.max(y_train)
            std_y = np.std(y_train)
            xi = std_y * 0.01

            clf.fit(x_train.reshape(-1, 1), y_train)
            clf.kernel_ 

            pred_mean, pred_std= clf.predict(x_test, return_std=True)

            plot_result(x_test, pred_mean, pred_std)
            plt.title(med[i])
            plt.xlabel('Concentration (log-scale)')
            plt.legend()
            plt.savefig(str(ap_v[j])+'_'+med[i]+"_sklern_predict.png")
            plt.show()


            plt.plot(x_test, acq(pred_mean, pred_std, max_y, xi), "--", color="red", label="Acquisition Function")
            plt.title("Expected Improvement")
            plt.xlabel('Concentration (log-scale)')
            plt.legend()
            plt.savefig(str(ap_v[j])+'_'+med[i]+"_EI.png")
            plt.show()

            nextx.append(float(10**x_test[np.argmax(acq(pred_mean, pred_std, max_y, xi))]))

        nextx_s.append(nextx)
    dfr = pd.DataFrame(nextx_s)

    xp = pd.Series(ap_v)
    dfconc = pd.concat([xp,dfr], axis=1)
    df_new = dfconc.set_axis(['Poised Voltage (mV)', 'RF','FMN','HNQ','AQDS'], axis=1)

    df_new.to_csv('next_point.csv')

if __name__ == "__main__":
    main()