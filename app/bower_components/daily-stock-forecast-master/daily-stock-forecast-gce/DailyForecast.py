#!/usr/bin/env python
#
# Copyright 2014 DMT SOURCE, LLC.
#
#     DMTSOURCE.COM | CONTACT: DEREK M TISLER lstrdean@gmail.com
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

import sys

from GetSymbols import *
from GetHistoricalFromYahoo import *
#from MeasureVolatility import *
#from Cluster import *
#from GaussianProcess import *
from SupportVectorRegression import *
from GaussianProcess import *

import pandas as pd
from pandas.tseries.offsets import BDay

from scipy import stats

from pytz import timezone

from datetime import datetime, time
import calendar
import time as tt

import platform
if platform.system() != 'Windows':
    import googledatastore as datastore

import logging

#import threading
#import multiprocessing

#Force error if warning needs to be traced
#import warnings
#warnings.simplefilter("error")

def percentDiff(x1,x2):
    return np.abs(x1-x2)/((x1+x2)/2.0)*100.0

def AddIntToDS(entity, name, item, indx=False):
    prop = entity.property.add()
    prop.name = name
    prop.value.indexed = indx
    prop.value.integer_value = int(item)

def AddFloatToDS(entity, name, item, indx=False):
    prop = entity.property.add()
    prop.name = name
    prop.value.indexed = indx
    prop.value.double_value = float("{0:.2f}".format(item))

def AddDoubleListToDS(entity, name, items):
    prop = entity.property.add()
    prop.name = name
    for item in items:
        prop.value.list_value.add().double_value = float("{0:.2f}".format(item))

def AddStrListToDS(entity, name, items):
    prop = entity.property.add()
    prop.name = name
    for item in items:
        prop.value.list_value.add().string_value = item        

def AddStringToDS(entity, name, item, indx=False):
    prop = entity.property.add()
    prop.name = name
    prop.value.indexed = indx
    prop.value.string_value = item

if __name__ == "__main__":

    #launch example python DailyForecast.py

    #Track time of the simulation
    startTime = tt.time()

    #First day of trading
    nowTime = datetime.now(tz=timezone('US/Eastern')).time()
    if nowTime >= time(19,00):
        dayToPredict = datetime.now(tz=timezone('US/Eastern')) + BDay(1)
    else:
        dayToPredict = datetime.now(tz=timezone('US/Eastern')) + BDay(0)
            
    print "\nPredicting %s\n"%dayToPredict.date()
    logging.info("Predicting %s\n"%dayToPredict.date())
    
    NPredPast             = 10
    history_len           = 100 #days
    saftey_days           = 10

    startOfPredictSim     = dayToPredict - BDay(NPredPast)

    endOfHistoricalDate   = dayToPredict - BDay(1)
    startOfHistoricalDate = startOfPredictSim - BDay(history_len+saftey_days)
    
    #Perform a guess for each prediction day
    predDays = pd.bdate_range(startOfPredictSim, dayToPredict)

    #Download symbols
    fullSymbols, fullNames, fullExchange, fullSector, fullIndustry  = GetAllSymbols()
    """fullSymbols, fullNames, fullExchange, fullSector, fullIndustry  = (['HEES','NFLX','AAPL'],
                                                         ['Google Inc.','Netflix, Inc.','Apple Inc.'],
                                                         ['NASDAQ','NASDAQ','NASDAQ'],
                                                         ['Technology','Consumer Services ','Technology'],
                                                         ['Software','Entertainment','Software'])"""
    """fullSymbols, fullNames, fullExchange, fullSector, fullIndustry  = (['SPY'],
                                                                       ['SPY Index'],
                                                                       ['NYSE'],
                                                                       ['Technology'],
                                                                       ['Software'])"""

    #Download historical data
    symbols, names, exchanges, sector, industry, dates, high, low, openPrice, closePrice, volume = \
                    GetHistoricalFromYahoo(fullSymbols,
                                           fullNames,
                                           fullExchange,
                                           fullSector,
                                           fullIndustry,
                                           (startOfHistoricalDate.month,
                                            startOfHistoricalDate.day,
                                            startOfHistoricalDate.year),
                                           (endOfHistoricalDate.month,
                                            endOfHistoricalDate.day,
                                            endOfHistoricalDate.year),
                                           priceFilterLow=5.0,
                                           priceFilterHigh=1e6,
                                           minVolume=1000.0,
                                           useThreading=True,
                                           requiredDomain=history_len+1,
                                           verbose=True)

    #We need to fetch extra days so we have the right # to handle the fixed dx indexing
    if len(dates[0]) != history_len+1:
        print "Insufficient domain, increase saftey_days."
        print len(dates[0])
        exit()
    
    #If no stocks in universe, exit
    if(len(symbols) == 0):
        exit()
    
    #Cross validate pred against history at end of simulation
    savedPrediction = {}

    #Check that each stock has the right domain(dates), if we cant get historical, then drop that prediction's day
    #loop trough past pred days, remove any that are not in history, dont include final day
    dropList = []
    #We have to check each symbol, but then we must ensure all others are also adjusted
    #for i in np.arange(len(symbols)):
    #Check each date in the predDays
    for j in np.arange(len(predDays)-1):
        if predDays[j].date() not in dates[0]:
            #Track the items to be dropped from the predDays list
            dropList.append(j)
            #Check if this bad date IS contained in other symbols
                
    predDays = predDays.delete(dropList)
    NPredPast = len(predDays)
    #print len(predDays)
    #

    #Make sure the first past prediction day is in the history
    if predDays[0].date() not in dates[0]:
        logging.error("FIRST PREDICTION DAY MISSING FROM HISTORY")
        print("FIRST PREDICTION DAY MISSING FROM HISTORY")
        exit()

    dropList = []
    for i in np.arange(len(predDays)-1):
        for j in np.arange(len(symbols)):
            hWI = i
            hWF = i+np.where(dates[0]==predDays[0].date())[0][0]#98
            #ensure the right day is being forecasted, holes could be in data
            if predDays[i].date() != dates[j][hWF]:
                logging.debug("Dates DONOT Match: %s vs %s"%(predDays[i].date(),dates[j][hWF]))
                print "Dates DONOT Match: %s vs %s"%(predDays[i].date(),dates[j][hWF])
                dropList.append(dropList)
    predDays = predDays.delete(dropList)
    #print len(predDays)
    #

    #Confirm that the day before the prediction is our last history day
    if endOfHistoricalDate.day !=  dates[0][-1].day:
        print "---- WARNING WARNING WARNING ----"
        print str(endOfHistoricalDate.date()) + ' : Expected end of historical'
        print str(dates[0][-1]) + ' : Recieved end of historical'
        print 'We do not have previous day''s values, reject unless holiday\n'
    
    cycleTime = tt.time() #track time of each percent sim progress
    for i in np.arange(len(predDays)):
        #set up moving window on historical data
        hWI = i
        #hWI = 0
        hWF = i+np.where(dates[0]==predDays[0].date())[0][0]#98 for ex cause 1 missing day and -1 for indexing on len 100

        #print status
        print "Simulation progress: %.0f%%, took %0.0f seconds"%(float(i+1)/float(len(predDays))*100.0, tt.time()-cycleTime)
        cycleTime = tt.time() #track time of each percent sim progress
        
        #SVD
        messageId = 0
        for j in np.arange(len(symbols)):
            #print "PRE %s"%symbols[j]
            #Test date sync, should be n-1 on left, w. all 3 matching on both sides
            #print dates[j][hWF-1:hWF][0], predDays[i].date()
            
            pHighBest, pLowBest, pOpenBest, pCloseBest, pVolumeBest = SupportVectorRegression(symbols[j],
                                                                             [high[j][hWI:hWF],
                                                                              low[j][hWI:hWF],
                                                                              openPrice[j][hWI:hWF],
                                                                              closePrice[j][hWI:hWF],
                                                                              volume[j][hWI:hWF]],
                                                                             genPlot = False,
                                                                             c = 100.0, #100 is cool w 170 sec cycle
                                                                             Gamma = 0.007,
                                                                             Epsilon = 0.1)
            """pHighBest, pLowBest, pOpenBest, pCloseBest, pVolumeBest = GaussianProcessRegressions(symbols[j],
                                                                             [high[j][hWI:hWF],
                                                                              low[j][hWI:hWF],
                                                                              openPrice[j][hWI:hWF],
                                                                              closePrice[j][hWI:hWF],
                                                                              np.log(volume[j][hWI:hWF])],
                                                                             genPlot = False)"""
            #pVolumeBest = np.exp(pVolumeBest)
            #Save items to pred array, final item just gets passed through as no real value exists to compare with
            if not symbols[j] in savedPrediction:
                savedPrediction[symbols[j]] = []
            savedPrediction[symbols[j]].append([pHighBest, pLowBest, pOpenBest, pCloseBest, pVolumeBest])
            #print "POST %s"%symbols[j]
        
    #Check the simulation result, need to save best

    #test ability to change dates to days
    dayOfWeekAsInt = pd.DatetimeIndex( predDays ).weekday
    dayOfWeekAsStr = []
    for dayInt in dayOfWeekAsInt:
        dayOfWeekAsStr.append(
            {
              0: 'M',
              1: 'Tu',
              2: 'W',
              3: 'Th',
              4: 'F'
            }[dayInt])
        
    #Easy names for index of prediction array
    OPEN   = 2
    CLOSE  = 3
    HIGH   = 0
    LOW    = 1
    VOLUME = 4

    #Get the rank of each stock, measure the price diff between open & close and rank
    rankItems = []
    rankScore = []
    rankIndexOriginal = []
    for i in np.arange(len(symbols)):
        rankItems.append(abs((np.array(savedPrediction[symbols[i]])[:,CLOSE][-1] - closePrice[i][-1])/abs(closePrice[i][-1])*100.0))
        R2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1], closePrice[i][-NPredPast+1:])[0][1]
        slope, intercept, r_value, p_value, std_err = stats.linregress(closePrice[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1])
        if np.mean([1.0-R2,abs(1.0-slope)]) <= 0.05:
            rankScore.append(1)
        elif np.mean([1.0-R2,abs(1.0-slope)]) < 0.1 and np.mean([1.0-R2,abs(1.0-slope)]) > 0.05:
            rankScore.append(2)
        else:
            rankScore.append(3)
        rankIndexOriginal.append(i)
    #rankIndex = np.array(rankItems).argsort()[::-1]
    rankItems = np.array(rankItems)
    rankScore = np.array(rankScore)


    #Get the index of each accuracy group
    indexRank1 = np.where(rankScore == 1)
    indexRank2 = np.where(rankScore == 2)
    indexRank3 = np.where(rankScore == 3)
    
    #Sort each accuracy group from high to low close price change
    sortedIndexRank1 = rankItems[indexRank1].argsort()[::-1]
    sortedIndexRank2 = rankItems[indexRank2].argsort()[::-1]
    sortedIndexRank3 = rankItems[indexRank3].argsort()[::-1]

    #Now we can sort the original index list by sliceing with the above groups to save symbol indicies in order of 1,2,3 accuracy
    sortedRankIndexOriginal = np.zeros(len(rankIndexOriginal))
    if len(sortedIndexRank1) > 0:
        sortedRankIndexOriginal[0:len(sortedIndexRank1)] = np.array(rankIndexOriginal)[indexRank1][sortedIndexRank1]
    if len(sortedIndexRank2) > 0:
        sortedRankIndexOriginal[len(sortedIndexRank1):len(sortedIndexRank1)+len(sortedIndexRank2)] = np.array(rankIndexOriginal)[indexRank2][sortedIndexRank2]
    if len(sortedIndexRank3) > 0:
        sortedRankIndexOriginal[len(sortedIndexRank1)+len(sortedIndexRank2):len(sortedIndexRank1)+len(sortedIndexRank2)+len(sortedIndexRank3)] = np.array(rankIndexOriginal)[indexRank3][sortedIndexRank3]

    #loop through the now sorted index list, and use that to fetch each symbol and apply a rank(ascending).
    rank = {}
    counter = 1
    for i in sortedRankIndexOriginal:
        rank[symbols[i]] = counter
        counter += 1
    
    if platform.system() != 'Windows':
        # Set the dataset from the command line parameters.
        datastore.set_options(dataset="daily-stock-forecast")

        #Save each symbol into the datastore
        for i in np.arange(len(symbols)):
            if rank[symbols[i]] <= 100000:
                try:
                    req = datastore.CommitRequest()
                    req.mode = datastore.CommitRequest.NON_TRANSACTIONAL
                    entity = req.mutation.insert_auto_id.add()

                    # Create a new entity key.
                    key = datastore.Key()
                    
                    # Set the entity key with only one `path_element`: no parent.
                    path = key.path_element.add()
                    path.kind = 'Forecast'

                    # Copy the entity key.
                    entity.key.CopyFrom(key)
                    
                    # - a dateTimeValue 64bit integer: `date`
                    prop = entity.property.add()
                    prop.name = 'date'
                    prop.value.timestamp_microseconds_value = long(tt.mktime(dayToPredict.timetuple()) * 1e6)
                    #prop.value.timestamp_microseconds_value = long(tt.time() * 1e6)

                    AddIntToDS(entity, 'rank', rank[symbols[i]], True)
                    AddStringToDS(entity, 'symbol', symbols[i], True)
                    AddStringToDS(entity, 'company', names[i], True)
                    AddStringToDS(entity, 'exchange', exchanges[i], True)
                    AddStringToDS(entity, 'sector', sector[i], True)
                    AddStringToDS(entity, 'industry', industry[i], True)

                    #predictions
                    AddDoubleListToDS(entity, 'openPredPrice', np.array(savedPrediction[symbols[i]])[:,OPEN])
                    AddDoubleListToDS(entity, 'closePredPrice', np.array(savedPrediction[symbols[i]])[:,CLOSE])
                    AddDoubleListToDS(entity, 'highPredPrice', np.array(savedPrediction[symbols[i]])[:,HIGH])
                    AddDoubleListToDS(entity, 'lowPredPrice', np.array(savedPrediction[symbols[i]])[:,LOW])
                    AddDoubleListToDS(entity, 'volumePred', np.array(savedPrediction[symbols[i]])[:,VOLUME])
                    AddStrListToDS(entity, 'dayOfPred', dayOfWeekAsStr)

                    #History lists
                    #print type(volume[i][0]), type(low[i][0]), float("{0:.2f}".format(volume[i][0]))
                    AddDoubleListToDS(entity, 'openPriceHistory', openPrice[i][-NPredPast+1:])
                    AddDoubleListToDS(entity, 'closePriceHistory', closePrice[i][-NPredPast+1:])
                    AddDoubleListToDS(entity, 'highPriceHistory', high[i][-NPredPast+1:])
                    AddDoubleListToDS(entity, 'lowPriceHistory', low[i][-NPredPast+1:])
                    AddDoubleListToDS(entity, 'volumeHistory', volume[i][-NPredPast+1:])
    #                AddStrListToDS(entity, 'dayOfWeekHistory', dayOfWeekAsStr[:-1])

                    #prediction correlation value, R2
                    #print len(np.array(savedPrediction[symbols[i]])[:,OPEN][:-1]), len(openPrice[i][-NPredPast+1:])
                    openR2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,OPEN][:-1], openPrice[i][-NPredPast+1:])[0][1]
                    AddFloatToDS(entity, 'openPredR2', openR2)
                    closeR2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1], closePrice[i][-NPredPast+1:])[0][1]
                    AddFloatToDS(entity, 'closePredR2', closeR2)
                    highR2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,HIGH][:-1], high[i][-NPredPast+1:])[0][1]
                    AddFloatToDS(entity, 'highPredR2', highR2)
                    lowR2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,LOW][:-1], low[i][-NPredPast+1:])[0][1]
                    AddFloatToDS(entity, 'lowPredR2', lowR2)
                    volR2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,VOLUME][:-1], volume[i][-NPredPast+1:])[0][1]
                    AddFloatToDS(entity, 'volumePredR2', volR2)

                    #prediction correlation slope
                    #print len(openPrice[i][-NPredPast+1:]), len( np.array(savedPrediction[symbols[i]])[:,OPEN][:-1])
                    slope, intercept, r_value, p_value, std_err = stats.linregress(openPrice[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,OPEN][:-1])
                    AddFloatToDS(entity, 'openPredSlope', slope)
                    if np.mean([1.0-openR2,abs(1.0-slope)]) <= 0.05:
                        AddIntToDS(entity, 'openModelAccuracy', 1)
                    elif np.mean([1.0-openR2,abs(1.0-slope)]) < 0.1 and np.mean([1.0-openR2,abs(1.0-slope)]) > 0.05:
                        AddIntToDS(entity, 'openModelAccuracy', 2)
                    else:
                        AddIntToDS(entity, 'openModelAccuracy', 3)

                    slope, intercept, r_value, p_value, std_err = stats.linregress(closePrice[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1])
                    AddFloatToDS(entity, 'closePredSlope', slope)
                    if np.mean([1.0-closeR2,abs(1.0-slope)]) <= 0.05:
                        AddIntToDS(entity, 'closeModelAccuracy', 1)
                    elif np.mean([1.0-closeR2,abs(1.0-slope)]) < 0.1 and np.mean([1.0-closeR2,abs(1.0-slope)]) > 0.05:
                        AddIntToDS(entity, 'closeModelAccuracy', 2)
                    else:
                        AddIntToDS(entity, 'closeModelAccuracy', 3)

                    slope, intercept, r_value, p_value, std_err = stats.linregress(high[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,HIGH][:-1])
                    AddFloatToDS(entity, 'highPredSlope', slope)
                    if np.mean([1.0-highR2,abs(1.0-slope)]) <= 0.05:
                        AddIntToDS(entity, 'highModelAccuracy', 1)
                    elif np.mean([1.0-highR2,abs(1.0-slope)]) < 0.1 and np.mean([1.0-highR2,abs(1.0-slope)]) > 0.05:
                        AddIntToDS(entity, 'highModelAccuracy', 2)
                    else:
                        AddIntToDS(entity, 'highModelAccuracy', 3)

                    slope, intercept, r_value, p_value, std_err = stats.linregress(low[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,LOW][:-1])
                    AddFloatToDS(entity, 'lowPredSlope', slope)
                    if np.mean([1.0-lowR2,abs(1.0-slope)]) <= 0.05:
                        AddIntToDS(entity, 'lowModelAccuracy', 1)
                    elif np.mean([1.0-lowR2,abs(1.0-slope)]) < 0.1 and np.mean([1.0-lowR2,abs(1.0-slope)]) > 0.05:
                        AddIntToDS(entity, 'lowModelAccuracy', 2)
                    else:
                        AddIntToDS(entity, 'lowModelAccuracy', 3)

                    slope, intercept, r_value, p_value, std_err = stats.linregress(volume[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,VOLUME][:-1])
                    AddFloatToDS(entity, 'volumePredSlope', slope)
                    if np.mean([1.0-volR2,abs(1.0-slope)]) <= 0.05:
                        AddIntToDS(entity, 'volumeModelAccuracy', 1)
                    elif np.mean([1.0-volR2,abs(1.0-slope)]) < 0.1 and np.mean([1.0-volR2,abs(1.0-slope)]) > 0.05:
                        AddIntToDS(entity, 'volumeModelAccuracy', 2)
                    else:
                        AddIntToDS(entity, 'volumeModelAccuracy', 3)

                    #computed values
    #                AddFloatToDS(entity, 'openPriceChange', np.array(savedPrediction[symbols[i]])[:,OPEN][-1] - openPrice[i][-1])
    #                AddFloatToDS(entity, 'openPriceChangePercent', (np.array(savedPrediction[symbols[i]])[:,OPEN][-1] - openPrice[i][-1])/abs(openPrice[i][-1])*100.0)
    #                AddFloatToDS(entity, 'closePriceChange', np.array(savedPrediction[symbols[i]])[:,CLOSE][-1] - closePrice[i][-1])
    #                AddFloatToDS(entity, 'closePriceChangePercent', (np.array(savedPrediction[symbols[i]])[:,CLOSE][-1] - closePrice[i][-1])/abs(closePrice[i][-1])*100.0)
    #                AddFloatToDS(entity, 'highPriceChange', np.array(savedPrediction[symbols[i]])[:,HIGH][-1] - high[i][-1])
    #                AddFloatToDS(entity, 'highPriceChangePercent', (np.array(savedPrediction[symbols[i]])[:,HIGH][-1] - high[i][-1])/abs(high[i][-1])*100.0)
    #                AddFloatToDS(entity, 'lowPriceChange', np.array(savedPrediction[symbols[i]])[:,LOW][-1] - low[i][-1])
    #                AddFloatToDS(entity, 'lowPriceChangePercent', (np.array(savedPrediction[symbols[i]])[:,LOW][-1] - low[i][-1])/abs(low[i][-1])*100.0)
    #                AddFloatToDS(entity, 'volumeChange', np.array(savedPrediction[symbols[i]])[:,VOLUME][-1] - volume[i][-1])
    #                AddFloatToDS(entity, 'volumeChangePercent', (np.array(savedPrediction[symbols[i]])[:,VOLUME][-1] - volume[i][-1])/abs(volume[i][-1])*100.0)

                    #Market snapshot
     #               AddFloatToDS(entity, 'predOpen', np.array(savedPrediction[symbols[i]])[:,OPEN][-1])
     #               AddFloatToDS(entity, 'predClose', np.array(savedPrediction[symbols[i]])[:,CLOSE][-1])
     #               AddFloatToDS(entity, 'predHigh', np.array(savedPrediction[symbols[i]])[:,HIGH][-1])
     #               AddFloatToDS(entity, 'predLow', np.array(savedPrediction[symbols[i]])[:,LOW][-1])
     #               AddFloatToDS(entity, 'predVolume', np.array(savedPrediction[symbols[i]])[:,VOLUME][-1])
                   
                    # Execute the Commit RPC synchronously and ignore the response:
                    # Apply the insert mutation if the entity was not found and close
                    # the transaction.
                    datastore.commit(req)
              
                except datastore.RPCError as e:
                    # RPCError is raised if any error happened during a RPC.
                    # It includes the `method` called and the `reason` of the
                    # failure as well as the original `HTTPResponse` object.
                    logging.error('Error while doing datastore operation')
                    logging.error('RPCError: %(method)s %(reason)s',
                                  {'method': e.method,
                                   'reason': e.reason})
                    logging.error('HTTPError: %(status)s %(reason)s',
                                  {'status': e.response.status,
                                   'reason': e.response.reason})
            if rank[symbols[i]] <= 25:
                #Also commit to the stock list, for faster and cheaper dataastore queries
                try:
                    req = datastore.CommitRequest()
                    req.mode = datastore.CommitRequest.NON_TRANSACTIONAL
                    entity = req.mutation.insert_auto_id.add()

                    # Create a new entity key.
                    key = datastore.Key()
                    
                    # Set the entity key with only one `path_element`: no parent.
                    path = key.path_element.add()
                    path.kind = 'StockList'

                    # Copy the entity key.
                    entity.key.CopyFrom(key)
                    
                    # - a dateTimeValue 64bit integer: `date`
                    prop = entity.property.add()
                    prop.name = 'date'
                    prop.value.timestamp_microseconds_value = long(tt.mktime(dayToPredict.timetuple()) * 1e6)
                    #prop.value.timestamp_microseconds_value = long(tt.time() * 1e6)

                    AddIntToDS(entity, 'rank', rank[symbols[i]], True)
                    AddStringToDS(entity, 'symbol', symbols[i], True)
                    AddStringToDS(entity, 'company', names[i], True)
                    AddStringToDS(entity, 'exchange', exchanges[i], True)

                    AddFloatToDS(entity, 'currentPrice', closePrice[i][-1])

                    AddFloatToDS(entity, 'forecastedPrice', np.array(savedPrediction[symbols[i]])[:,CLOSE][-1])

                    R2 = np.corrcoef(np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1], closePrice[i][-NPredPast+1:])[0][1]
                    slope, intercept, r_value, p_value, std_err = stats.linregress(closePrice[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1])
                    if np.mean([1.0-R2,abs(1.0-slope)]) <= 0.05:
                        AddIntToDS(entity, 'modelAccuracy', 1)
                    elif np.mean([1.0-R2,abs(1.0-slope)]) < 0.1 and np.mean([R2,abs(1.0-slope)]) > 0.05:
                        AddIntToDS(entity, 'modelAccuracy', 2)
                    else:
                        AddIntToDS(entity, 'modelAccuracy', 3)
                   
                    # Execute the Commit RPC synchronously and ignore the response:
                    # Apply the insert mutation if the entity was not found and close
                    # the transaction.
                    datastore.commit(req)
              
                except datastore.RPCError as e:
                    # RPCError is raised if any error happened during a RPC.
                    # It includes the `method` called and the `reason` of the
                    # failure as well as the original `HTTPResponse` object.
                    logging.error('Error while doing datastore operation')
                    logging.error('RPCError: %(method)s %(reason)s',
                                  {'method': e.method,
                                   'reason': e.reason})
                    logging.error('HTTPError: %(status)s %(reason)s',
                                  {'status': e.response.status,
                                   'reason': e.response.reason})
    
    logging.info("\nTime of Simulation: {0:,.0f} seconds\n".format((tt.time() - startTime)))
    print("\nTime of Simulation: {0:,.0f} seconds, {1:,.0f} minutes\n".format((tt.time() - startTime), (tt.time() - startTime)/60.0))

    #If a small run was done, view the results.
    if len(symbols) <= 3 and platform.system() == 'Windows':
        for i in np.arange(len(symbols)):

            
            labels = ["High","Low","Open","Close", "Volume"]
            colors = ["r","g","b","c", "o"]
            
            fig = plt.figure()
            #plt.subplots_adjust(left=0.12, bottom=0.06, right=0.90, top=0.96, wspace=0.20, hspace=0.08)
            plt.suptitle("%s Cross Validation of SVR"%symbols[i])
            plt.subplot(3, 2, 1)

            yPredHigh = np.array(savedPrediction[symbols[i]])[:,HIGH][:-1]
            #print high[i][-NPredPast+1:].shape, yPredHigh.shape
            plt.plot( high[i][-NPredPast+1:], yPredHigh, '%s.'%colors[0], label=labels[0], markersize=5, zorder=4)
            #linear fit
            slope, intercept, r_value, p_value, std_err = stats.linregress(high[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,HIGH][:-1])
            line = slope*high[i][-NPredPast+1:]+intercept
            plt.plot(high[i][-NPredPast+1:],line,'k-', label="%.3f"%slope)
            plt.plot([],[],label= np.corrcoef(np.array(savedPrediction[symbols[i]])[:,HIGH][:-1], high[i][-NPredPast+1:])[0][1] )
            #
            
            plt.ylabel('Predicted')
            plt.grid(True)
            plt.legend(loc='upper left', numpoints=1, ncol=1, fancybox=True, prop={'size':10}, framealpha=0.50)
            
            plt.subplot(3, 2, 2)

            yPredLow = np.array(savedPrediction[symbols[i]])[:,LOW][:-1]
            plt.plot(low[i][-NPredPast+1:], yPredLow, '%s.'%colors[1], label=labels[1], markersize=5, zorder=4)
            #linear fit
            slope, intercept, r_value, p_value, std_err = stats.linregress(low[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,LOW][:-1])
            line = slope*low[i][-NPredPast+1:]+intercept
            plt.plot(low[i][-NPredPast+1:],line,'k-', label="%.3f"%slope)
            plt.plot([],[],label= np.corrcoef(np.array(savedPrediction[symbols[i]])[:,LOW][:-1], low[i][-NPredPast+1:])[0][1] )
            #
            plt.grid(True)
            plt.legend(loc='upper left', numpoints=1, ncol=1, fancybox=True, prop={'size':10}, framealpha=0.50)

            plt.subplot(3, 2, 3)

            yPredOpen = np.array(savedPrediction[symbols[i]])[:,OPEN][:-1]
            plt.plot(openPrice[i][-NPredPast+1:], yPredOpen, '%s.'%colors[2], label=labels[2], markersize=5, zorder=4)
            #linear fit
            slope, intercept, r_value, p_value, std_err = stats.linregress(openPrice[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,OPEN][:-1])
            line = slope*openPrice[i][-NPredPast+1:]+intercept
            plt.plot(openPrice[i][-NPredPast+1:],line,'k-', label="%.3f"%slope)
            plt.plot([],[],label= np.corrcoef(np.array(savedPrediction[symbols[i]])[:,OPEN][:-1], openPrice[i][-NPredPast+1:])[0][1] )
            #
            plt.xlabel('Real')
            plt.ylabel('Predicted')
            plt.grid(True)
            plt.legend(loc='upper left', numpoints=1, ncol=1, fancybox=True, prop={'size':10}, framealpha=0.50)

            
            plt.subplot(3, 2, 4)

            yPredClose = np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1]
            plt.plot(closePrice[i][-NPredPast+1:], yPredClose, '%s.'%colors[3], label=labels[3], markersize=5, zorder=4)
            #linear fit
            slope, intercept, r_value, p_value, std_err = stats.linregress(closePrice[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1])
            line = slope*closePrice[i][-NPredPast+1:]+intercept
            plt.plot(closePrice[i][-NPredPast+1:],line,'k-', label="%.3f"%slope)
            plt.plot([],[],label=np.corrcoef(np.array(savedPrediction[symbols[i]])[:,CLOSE][:-1], closePrice[i][-NPredPast+1:])[0][1] )
            #
            plt.xlabel('Real')
            plt.grid(True)
            plt.legend(loc='upper left', numpoints=1, ncol=1, fancybox=True, prop={'size':10}, framealpha=0.50)

            #plt.show()




            plt.subplot(3, 2, 5)

            plt.ticklabel_format(style='sci')
            vol = np.array(savedPrediction[symbols[i]])[:,VOLUME][:-1]
            plt.plot(volume[i][-NPredPast+1:], vol, '%s.'%colors[3], label=labels[3], markersize=5, zorder=4)
            #linear fit
            slope, intercept, r_value, p_value, std_err = stats.linregress(volume[i][-NPredPast+1:], np.array(savedPrediction[symbols[i]])[:,VOLUME][:-1])
            line = slope*volume[i][-NPredPast+1:]+intercept
            plt.plot(volume[i][-NPredPast+1:],line,'k-', label="%.3f"%slope)
            #print np.corrcoef(np.array(savedPrediction[symbols[i]])[:,VOLUME][:-1], volume[i][-NPredPast+1:])[0][1]
            plt.plot([],[],label= np.corrcoef(np.array(savedPrediction[symbols[i]])[:,VOLUME][:-1], volume[i][-NPredPast+1:])[0][1] )
            #
            plt.xlabel('Real')
            plt.grid(True)
            plt.legend(loc='upper left', numpoints=1, ncol=1, fancybox=True, prop={'size':10}, framealpha=0.50)


            plt.show()


            
            plt.clf()
            plt.cla()
            plt.close()
    
