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
    def _get_all_variables(self, substring):
        
        file_dict = self.get_file_dictionary()
        variables_list, units_list = [], []
        for path in file_dict[substring]:
            with open(path) as f:
                f.readline()
                variables_list += [x.replace('"', '').strip() 
                                   for x in f.readline().split(',')]
                units_list += [x.replace('"', '').strip() 
                               for x in f.readline().split(',')]
        return sorted(list(set(zip(variables_list, units_list))))
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def get_all_variables(self):
        """Lists all of the variables across all files"""
        
        a = self._get_all_variables(self.file_substrings[0])
        b = self._get_all_variables(self.file_substrings[1])
        c = a + b
        l1 = np.array([x[0] for x in c])
        l2 = np.array([x[1] for x in c])
        units_dict = dict(zip(l1, l2))
        l1 = list(set(l1))
        l2 = [units_dict[x] for x in l1]
        idx = np.argsort(np.array(map(lambda x: x.lower(), l1)))
        l1, l2 = list(np.array(l1)[idx]), list(np.array(l2)[idx])
        for var in ['RECORD', 'TIMESTAMP']:
            idx = l1.index(var)
            unit = l2[idx]
            l1.remove(var)
            l2.remove(unit)
        return zip(l1, l2)
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
        """Opens all csv files and concatenates to dataframe, handles dupes and 
           missing data, forces all data to numeric and alphabetises"""
        
        file_dict = self.get_file_dictionary()
        df_dict = {}
        for snippet in sorted(file_dict.keys()):
            df = pd.concat(map(lambda x: pd.read_csv(x, skiprows = [0, 2, 3], 
                                                     na_values = 'NAN'),
                               file_dict[snippet]), sort = True)
            df.index = map(lambda x: dt.datetime.strptime(x, '%Y-%m-%d %H:%M:%S'), 
                           df.TIMESTAMP)
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
        new_order = [x[0] for x in self.get_all_variables()]
        df = df[new_order]
        return df
    #--------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------
    def write_df_to_file(self, output_path, include_units = True):
        
        output_file = os.path.join(output_path, 'flux_data.csv')
        df = self.dataframe.copy()
        if include_units:
            tuple_list = self.get_all_variables()
            header_list = pd.MultiIndex.from_tuples(tuple_list)
            df.columns = header_list
        df.to_csv(output_file, index_label = 'Date_time')
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def plot_ustar(self, num_bins = 30):
        
        num_bins = 30
        
        noct_df = self.dataframe.loc[self.dataframe.SW_IN < 20]
        noct_df = noct_df.loc[noct_df.FC_QC < 7]
        noct_df.loc[(noct_df.FC<-10)|(noct_df.FC>20),'FC']=np.nan
        noct_df['ustar_cat'] = pd.qcut(self.dataframe.USTAR, num_bins, 
                                       labels = np.linspace(1, num_bins, num_bins))
        means_df = noct_df.groupby('ustar_cat').mean()
        fig, ax = plt.subplots(1, figsize = (12, 8))
        fig.patch.set_facecolor('white')
        ax.set_ylabel(r'$R_e\/(\mu mol\/m^{-2}\/s^{-1})$', fontsize = 22)
        ax.set_xlabel('$u_{*}\/(m\/s^{-1})$', fontsize = 22)
        ax.tick_params(axis = 'x', labelsize = 14)
        ax.tick_params(axis = 'y', labelsize = 14)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')    
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.axvline(0.248, color = 'grey')
        ax.plot(means_df.USTAR, means_df.FC, marker = 'o', mfc = '0.5', color = 'grey')
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def plot_time_series(self, variable, diel_average = False):

        if not variable in self.dataframe.columns: 
            raise KeyError('No variable called {}'.format(variable))        
        a = dict(self.get_all_variables())
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
        ax.set_ylabel('{0} ({1})'.format(variable, a[variable]), fontsize = 22)
        ax.set_xlabel('${}$'.format(xlab), fontsize = 22)
        ax.tick_params(axis = 'x', labelsize = 14)
        ax.tick_params(axis = 'y', labelsize = 14)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')    
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.plot(df[variable])
    #--------------------------------------------------------------------------