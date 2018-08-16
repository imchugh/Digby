#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu May  3 15:19:55 2018

@author: ian
"""
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pdb

input_path = '/media/ian/24B8-140D/Converted/'
output_path = '/media/ian/24B8-140D/Collated/'


class digby_data(object):
        
    #--------------------------------------------------------------------------
    def __init__(self, parent_directory):
        
        self.parent_directory = parent_directory
        self.file_substrings = ['Flux_CSIFormat', 'Flux_NOTES']
        self.dataframe = self.make_new_df()
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def _correct_sonic(self, df):
        """Sonic azimuth was set to zero from the beginning of the time series 
           to 2018-07-12; this routine correct the dataframe to account for 
           this"""

        correct_from = 360
        correct_to = 270
        correct_period = [dt.datetime(2017, 1, 1), 
                          dt.datetime(2018, 7, 12, 12)]
        df.loc[correct_period[0]: correct_period[1], 'WD'] = (
            df.loc[correct_period[0]: correct_period[1], 'WD'] - 
            (correct_from - correct_to))
        df.loc[df.WD < 0, 'WD'] = 360 + df.loc[df.WD < 0, 'WD']
        return
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def _get_common_variables(self, substring):
        
        file_dict = self.get_file_dictionary()
        
        l = []
        for path in file_dict[substring]:
            with open(path) as f:
                f.readline()
                header = f.readline()
                sub_header_list = [x.replace('"', '').strip() 
                                   for x in header.split(',')]
                record_flag = 'RECORD' in sub_header_list
                if record_flag:
                    idx = sub_header_list.index('RECORD')
                    sub_header_list.remove('RECORD')
                units = f.readline()
                sub_units_list = [x.replace('"', '').strip() 
                                  for x in units.split(',')]
                if record_flag: del sub_units_list[idx]
                l.append(zip(sub_header_list, sub_units_list))
        first_set = set(l[0])
        for next_set in l[1:]: (first_set.intersection_update(set(next_set)))
        return next_set
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def get_common_variables(self):
        """Lists all of the variables common to all files"""
        
        a = self._get_common_variables(self.file_substrings[0])
        b = self._get_common_variables(self.file_substrings[1])
        c = a + b
        l1 = [x[0] for x in c]
        l2 = [x[1] for x in c]
        idx = np.argsort(np.array(map(lambda x: x.lower(), l1)))
        return zip(np.array(l1)[idx], np.array(l2)[idx])
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def get_file_dictionary(self):
        """Steps through all subdirectories in parent directory and find all 
           files that contain the unique substrings in the init"""
        
        d = {key: [] for key in self.file_substrings}
        for snippet in sorted(d.keys()):
            for root, dirs, files in os.walk(self.parent_directory):    
                f_list = filter(lambda f: snippet in f, files)
                full_f_list = map(lambda f: os.path.join(root, f), f_list)
                if full_f_list: d[snippet] += full_f_list
        return d
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def make_new_df(self):
        """Opens all csv files and converts to dataframe, handles dupes and 
           missing data and forces all data to numeric"""
        
        file_dict = self.get_file_dictionary()
        df_dict = {}
        for snippet in sorted(file_dict.keys()):
            df = pd.concat(map(lambda x: pd.read_csv(x, skiprows = [0, 2, 3], 
                                                     na_values = 'NAN'),
                               file_dict[snippet]))
            df.index = map(lambda x: dt.datetime.strptime(x, '%Y-%m-%d %H:%M:%S'), 
                           df.TIMESTAMP)
            df.drop('TIMESTAMP', axis = 1, inplace = True)
            if 'RECORD' in df.columns: df.drop('RECORD', axis = 1, inplace = True)
            df_dict[snippet] = df
        df = df_dict['Flux_CSIFormat'].join(df_dict['Flux_NOTES'], rsuffix = '_2')
        df.drop_duplicates(inplace = True)
        df.sort_index(inplace = True)
        df = df.loc['2017-12':]
        df = df[~df.index.duplicated(keep = 'first')]
        new_range = pd.date_range(df.index[0], df.index[-1], freq = '30T')
        df = df.reindex(new_range)
        for column in df.columns:
            df.loc[:, column] = pd.to_numeric(df[column], errors = 'ignore')
        self._correct_sonic(df)
        return df
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------

    def write_df_to_file(self, output_path):
        
        output_file = os.path.join(output_path, 'flux_data.csv')
        df = self.make_new_df()
        #with open(output_file, 'w') as f:
        #    f.writelines(header_list)
        #    df.to_csv(f, header = False)
        df.to_csv(output_file, index_label = 'date_time')        


    def plot_time_series(self, variable, diel_average = False):

        if not variable in self.dataframe.columns: 
            raise KeyError('No variable called {}'.format(variable))        
        a = self.get_common_variables(self.file_substrings[0])
        b = self.get_common_variables(self.file_substrings[1])
        a.update(b)
        if diel_average:
            df = self.dataframe[variable].groupby([lambda x: x.hour, 
                                                   lambda y: y.minute]).mean()
            df = pd.DataFrame(df)
            df.index = np.linspace(0, 23.5, 48)
            xlab = 'Time'
        else:
            df = self.dataframe
            xlab = 'Date'
        fig, ax = plt.subplots(1, figsize = (12, 8))
        fig.patch.set_facecolor('white')
        ax.set_ylabel('${0}\/({1})$'.format(variable, a[variable]), fontsize = 22)
        ax.set_xlabel('${}$'.format(xlab), fontsize = 22)
        ax.tick_params(axis = 'x', labelsize = 14)
        ax.tick_params(axis = 'y', labelsize = 14)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')    
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.plot(df[variable])


#sonic_correction = 270
#
#df.WD = df.WD - (360 - sonic_correction)
#df.loc[df.WD < 0, 'WD'] = 360 + df.loc[df.WD < 0, 'WD']
#
#header_dict = {}
#for key in f_dict.keys():
#    f = open(sorted(f_dict[key])[0])
#    header_dict[key] = f.readlines()[:4]
#    f.close()
#header_list = []
#header_list.append(header_dict['Flux_CSIFormat'][0])
#for i in range(1, 4):
#    csi_line = header_dict['Flux_CSIFormat'][i].rstrip() + ','
#    notes_line = ','.join(header_dict['Flux_NOTES'][i].rstrip().split(',')[1:]) + '\r\n'
#    header_list.append(''.join([csi_line, notes_line]))
