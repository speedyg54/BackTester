
#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
"""
Created on Sun May 12 05:54:19 2019

@author: OBar
"""

import datetime
import numpy as np
import pandas as pd
import sklearn

import pandas_datareader as pdr
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.svm import LinearSVC, SVC

"""
Create a Pandas DataFrame that contains the lagged price returns for a prior number of days. 
"""
def create_lagged_series(symbol, start_date, end_date, lags=5):
    #yahoo stock info
    ts = pdr.DataReader(
                    symbol, 'yahoo', start_date-datetime.timedelta(days=365), 
                    end_date
    )
    
    #Create the new lagged dataframe
    tslag = pd.DataFrame(index=ts.index)
    tslag["Today"] = ts["Adj Close"]
    tslag["Volume"] = ts["Volume"]
    
    #Create the shifted lag series of prior trading period close values
    for i in range(0, lags):
        tslag["Lag{}".format(str(i+1))] = ts["Adj Close"].shift(i+1)
        
    #Create the returns DataFrame
    tsret = pd.DataFrame(index=tslag.index)
    tsret["Volume"] = tslag["Volume"]
    tsret["Today"] = tslag["Today"].pct_change()*100.0
    
    #If any of the values of percentage returns equal zero, set them to a small
    #number (stops issues with QDA model in SKLEARN)
    for i,x in enumerate(tsret["Today"]):
        if (abs(x) < 0.0001):
            tsret["Today"][i] = 0.0001
            
    #Create the lagged percentage returns columns
    for i in range(0, lags):
        tsret["Lag{}".format(str(i+1))] = \
        tslag["Lag{}".format(str(i+1))].pct_change() * 100.0
        
    #Create the direction column indicating an up or down day
    tsret["Direction"] = np.sign(tsret["Today"])
    tsret = tsret[tsret.index >= start_date]
    
    return tsret


"""
forecast US stock market in 05' using 2001 - 2004 data.
We will generate a training/testing split. using default parameters for the radial support
vector machines and random forest. Then iterate over the models and we then made predictions
and find the hit rate and the confusion matrix for each model.
"""
if __name__ == "__main__":
    #create the lagged series of the SP500
    snpret = create_lagged_series(
        "^GSPC", datetime.datetime(2001,1,10),
        datetime.datetime(2005,12,31), lags=5                           
    )
    
    
    #use the prior two days of returns as predictor
    #values, with direction as the response
    X = snpret[["Lag1", "Lag2"]]
    y = snpret["Direction"]
    
    #the test data is split into two parts
    start_test = datetime.datetime(2005,1,1)
    
    #Create training and test sets
    X_train = X[X.index < start_test]
    X_test = X[X.index >= start_test]
    y_train = y[y.index < start_test]
    y_test = y[y.index >= start_test]
    
    #create the parametrised models
    print("Hit Rates/Confusion Matrices:\n")
    models = [("LR", LogisticRegression()),
              ("LDA", LinearDiscriminantAnalysis()),
              ("QDA", QuadraticDiscriminantAnalysis()),
              ("LSVC", LinearSVC()),
              ("RSVM", SVC(
                      C=1000000.0, cache_size=200, class_weight=None,
                      coef0=0.0, degree=3, gamma=0.0001, kernel='rbf',
                      max_iter=-1, probability=False, random_state=None,
                      shrinking=True, tol=0.001, verbose=False)
                ),
                ("RF", RandomForestClassifier(
                        n_estimators=1000, criterion='gini',
                        max_depth=None, min_samples_split=2,
                        min_samples_leaf=1, max_features='auto',
                        bootstrap=True, oob_score=False, n_jobs=1,
                        random_state=None, verbose=0)
                 )]
    
    #iterate through the models
    for m in models:
        #Train each of the models on the training set
        m[1].fit(X_train, y_train)
        pred = m[1].predict(X_test)
        
        #output the hit rate and the confusion matrix for each model
        print("{}:\n{}".format(m[0], m[1].score(X_test, y_test)))
        print("{}\n".format(confusion_matrix(pred, y_test)))
    
    
    
    
    
    
    
    
    
    
    