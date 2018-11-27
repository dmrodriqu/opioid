import numpy as np
import pandas as pd
from glob import glob
from dask.diagnostics import ProgressBar
import dask
import dask.dataframe as dd
from multiprocessing.pool import ThreadPool

medicarefile ='Medicare_Part_D_Opioid_Prescribing_Geographic_2016.xlsx'
overdoses = 'NCHS_-_Drug_Poisoning_mortality_by_State__United_States.csv'
overdosesCounty = 'NCHS_-_Drug_Poisoning_Mortality_by_County__United_States.csv'

def readToPandas():
    #overdosebyState = dd.read_csv(overdoses)
    overdosesbyCounty = dd.read_csv(overdosesCounty)
    medicareframe = pd.read_excel(medicarefile, sheet_name = [0,1], header = 4)
    medicarestate, medicarecounty = medicareframe[0], medicareframe[1]
    medicarestate, medicarecounty = dd.from_pandas(medicarestate, npartitions = 10), dd.from_pandas(medicarecounty, npartitions = 10)
   # overdoseState= overdosebyState[overdosebyState['Year']==  2016]
    return overdosesbyCounty, medicarecounty

def splitcolumn(df, column, sep, part, exp = True):
    return df[column].str.split(sep, n = part, expand = exp)

def partition(df, itemtoreplace, replace, inp = True):
    return df.replace(itemtoreplace, replace, inplace = inp)

def divide(df, column1, column2, newcolumnname):
    df[newcolumnname]= df[column1]/df[column2]
    return df

def replaceAndCleanInf(df):
    return df.replace([np.inf,-np.inf], np.nan).dropna()



def main():
    overdosesbyCounty, medicarecounty = readToPandas()
    listOfCols = overdosesbyCounty.columns
    overdosestomerge = overdosesbyCounty[[listOfCols[0],
                                        'Year',
                                        'FIPS State',
                                        listOfCols[5],
                                        listOfCols[-1]]].compute()
    deathratesplit = splitcolumn(overdosestomerge, listOfCols[-1], '-', 1)
    placement = {'<2': 1, '30+' : 31}
    for i in placement:
        partition(deathratesplit,[i], placement[i])
    overdosestomerge['deathmin'], overdosestomerge['deathmax'] = deathratesplit[0].astype('f8'), deathratesplit[1].astype('f8')
    overdosestomerge = overdosestomerge[overdosestomerge['Year'] == 2016]
    overdosestomerge.drop(columns = 'Year', inplace = True)
    prescriberoverdose = medicarecounty.merge(overdosestomerge, on = 'FIPS').compute()
    prescriberoverdose= divide(prescriberoverdose, 'deathmin', 'Opioid Prescribing Rate', 'Death per prescribing rate lower')
    prescriberoverdose= divide(prescriberoverdose, 'deathmax', 'Opioid Prescribing Rate', 'Death per prescribing rate upper')
    prescriberoverdose = replaceAndCleanInf(prescriberoverdose)
    prescriberoverdose.to_csv('opiateprescriptiondeaths.csv')



with dask.config.set(pool = ThreadPool()):
    with ProgressBar():
        main()
        #parallel file joining
        '''
        files = glob("opiateprescriptiondeaths-*.csv")
        with open('opiatedata.csv','w') as output:
            for filename in files:
                with open(filename) as part:
                    output.write(part.read())
        '''
