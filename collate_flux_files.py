#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu May  3 15:19:55 2018

@author: ian
"""
import datetime as dt
import os
import pandas as pd
import pdb

input_path = '/mnt/fluxdata/Digby_data/Converted/'
output_path = '/mnt/fluxdata/Digby_data/Collated/'

full_f_list = []
data_list = []
notes_list = []
csi_list = []
sonic_correction = 270

f_dict = {'Flux_NOTES': notes_list, 'Flux_CSIFormat': csi_list}
data_dict = {}
for snippet in sorted(f_dict.keys()):
    df_list = []
    for root, dirs, files in os.walk(input_path):    
        f_list = filter(lambda f: snippet in f, files)
        full_f_list = map(lambda f: os.path.join(root, f), f_list)
        if full_f_list:
            df_list.append(pd.concat(map(lambda x: pd.read_csv(x, 
                                                               skiprows = [0, 2, 3], 
                                                               na_values = 'NAN'),
                           full_f_list)))
            f_dict[snippet] = f_dict[snippet] + full_f_list
    df = pd.concat(df_list)
    df.index = map(lambda x: dt.datetime.strptime(x, '%Y-%m-%d %H:%M:%S'), 
                   df.TIMESTAMP)
    df.drop('TIMESTAMP', axis = 1, inplace = True)
    data_dict[snippet] = df
df = data_dict['Flux_CSIFormat'].join(data_dict['Flux_NOTES'], rsuffix = '_2')
df.drop_duplicates(inplace = True)
df.sort_index(inplace = True)
df = df.loc['2017-12':]
new_range = pd.date_range(df.index[0], df.index[-1], freq = '30T')
df = df.reindex(new_range)
for column in df.columns:
    df.loc[:, column] = pd.to_numeric(df[column], errors = 'ignore')
df.WD = df.WD - (360 - sonic_correction)
df.loc[df.WD < 0, 'WD'] = 360 + df.loc[df.WD < 0, 'WD']

header_dict = {}
for key in f_dict.keys():
    f = open(sorted(f_dict[key])[0])
    header_dict[key] = f.readlines()[:4]
    f.close()
header_list = []
header_list.append(header_dict['Flux_CSIFormat'][0])
for i in range(1, 4):
    csi_line = header_dict['Flux_CSIFormat'][i].rstrip() + ','
    notes_line = ','.join(header_dict['Flux_NOTES'][i].rstrip().split(',')[1:]) + '\r\n'
    header_list.append(''.join([csi_line, notes_line]))
output_file = os.path.join(output_path, 'flux_data.csv')
with open(output_file, 'w') as f:
    f.writelines(header_list)
    df.to_csv(f, header = False)