#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  8 07:01:08 2025

@author: galengao
"""

from shiny import App, reactive, render, ui

from urllib.request import urlretrieve

import datetime

import pandas as pd

def generate_url(startdate, enddate, passkey):
    # format passkey to account for whitespace
    passkey = passkey.replace(' ', '%20')
    
    '''Download amion datatable of interest'''
    # Use the 625c extension to figure out wtf people are doing
    urlstem = "http://www.amion.com/cgi-bin/ocs?Lo={}&Rpt=625ctabs".format(passkey)
    
    # parse date information
    y, m, d = startdate.strftime('%y'), startdate.month, startdate.day
    delta = (enddate - startdate).days

    datestring = "&Day={}&Month={}-{}&Days={}".format(d, m, y, delta)

    return urlstem + datestring

def download_df(startdate, enddate, passkey):
    
    url = generate_url(startdate, enddate, passkey)     
    # url="http://www.amion.com/cgi-bin/ocs?Lo=uwmed%20medres&Rpt=625c&Month=7-24&Days=365"

    path, headers = urlretrieve(url)

    try:
        df = pd.read_table(path, skiprows=7, header=None, \
                       usecols=[0,3,6,7,8,9,15,16])
    except pd.errors.EmptyDataError:
        return pd.DataFrame([])
    
    else:
        # rename columns
        columns = ['Name', 'Assignment', 'Date', 'Start', 'Stop', 'Role', 'Type', 'Assgn']
        df.columns = columns
    
        # Get rid of role == null columns and role == "Services" (e.g. "H MICU A")
        df = df[~df.Role.isnull()]
        df = df[df.Role != 'Services']
        df = df[df.Role.str[-1] != '*']
    
        # replace instances of "(" and ")" with "'" to encode nicknames the same way
        df['Name'] = df.Name.str.replace('\'', '').str.replace('\"', '')
    
        return df
        

def generate_rezzy_dictionary(df):
    # Sorting code
    listRoles = ['IM R1', 'IM R2', 'IM R3', 'RM R1', 'Psych R1', 'Anes R1', \
                 'FM R1', 'FM R2', 'EM UW', 'EM UW R1', 'EM Madigan R1', 'IM R4']
    roleDict = {x:y for x,y in zip(listRoles, range(len(listRoles)))}
    
    # get only role assignments from the first date in the date range
    # this avoids duplication of 
    df_x = df[df.Date == df.Date.iloc[0]]
    
    # drop duplicates name entries and then sort first by role (e.g. PGY year)
    # and then alphebetically by name
    df_x = df_x[~df_x.Name.duplicated()].sort_values(["Role", "Name"], \
                                                 key=lambda x: x.map(roleDict))
    
    masterDict = {r:{x:x for x in df_x[df_x.Role == r]['Name']} \
                  for r in df_x.Role.unique()}
    
    return masterDict

def match_schedules(df, rezzies):
    # define types of days to look for under "Assignments" in Amion file    
    noWorkTypes = ['Off', 'Holiday', 'Vac', 'Panel', 'Risk']
    
    # construct final output table df_out
    masterList = []
    for r in rezzies:
        df_r = df[df.Name == r]
        workingList = []
        for noWork in noWorkTypes:
            df_nw =  df_r[df_r.Assignment.astype(str).str.contains(noWork)][['Date']]
            df_nw[r] = noWork
            
            workingList.append(df_nw[~df_nw.duplicated()])
        
        df_r_out = pd.concat(workingList)
        # default to label priority as above in noWork: Off -> Vac -> Panel -> Risk
        df_r_out = df_r_out[~df_r_out['Date'].duplicated(keep='first')]
        masterList.append(df_r_out.set_index('Date'))
       
    df_out = pd.concat(masterList, axis=1)
    
    # sort df_out chronologically
    originalCols = list(df_out.columns)

    # Sort Dates (now in index)
    df_out['Year'] = df_out.index.str.split('-').str[2].astype(int)
    df_out['Month'] = df_out.index.str.split('-').str[0].astype(int)
    df_out['Day'] = df_out.index.str.split('-').str[1].astype(int)
    df_out = df_out.sort_values(['Year', 'Month', 'Day'])

    # Convert index dates to [DOW Month DD, YYYY] format
    dates = []
    for d in df_out.index:
        if type(d) is str:
            date = datetime.datetime.strptime(d, '%m-%d-%y') # -> datetime obj
            date = date.strftime("%A %b %d, %Y") # -> 
            dates.append(date)
        else:
            dates.append('')
    df_out.index = dates
    
    # reset index and rename "Date"
    df_out = df_out[originalCols].reset_index()
    df_out.columns = ['Date'] + originalCols
    
    # construct list of CSS styles
    colors = ['#8dd3c7', '#80b1d3', '#b3de69', '#fccde5', '#d9d9d9']
    styles = [{"class": "text-center",}]
    for col in df_out.columns[1:]:
        for noWork, color in zip(noWorkTypes, colors):
            rowIndices = list(df_out[df_out[col] == noWork].index)
            styles.append({
                "rows": rowIndices,
                "cols": [df_out.columns.get_loc(col)],
                "style": {"background-color": color}
            })
    
    return df_out, styles



app_ui = ui.page_fluid(
    ui.row(
        ui.column(4, 
                  ui.h4("Enter Schedule Information:"),
                  
                  # Amion password
                  ui.input_password("password", "Amion Password", ""),  
              
                  # Date range
                  ui.input_date_range("daterange", "Date Range", \
                                      start=datetime.date.today(), \
                                      end=datetime.date.today() + datetime.timedelta(30)),  

                  # Submit button to populate list of residents
                  ui.input_action_button("submit_daterange", "Submit Dates"),  
              
                  ui.HTML("<br><br><br>"),  
              
                  ui.input_select(  
                      "rezzies",  
                      "Select resident schedules to compare:",  
                      [],  
                      multiple=True,
                      width="100%",
                      size=12,
                  ),  
              
                  ui.input_action_button("submit_residents", "Submit Rezzies"),  
                  
                  ui.HTML("<br><br><br>"),  
                  
                  ui.input_text("alert", label=""),

              
        ),
    
        ui.column(8,
                  ui.h2("Common Days Off"),
                  ui.output_data_frame("daysOff_df"),
                  ui.output_data_frame("legend"),
        ),

    ),
    
)

def server(input, output, session):

    @reactive.effect()
    @reactive.event(input.submit_daterange)
    def update_select_rezzies():
        df = download_df(input.daterange()[0], input.daterange()[1], input.password())
        if len(df) == 0:
            ui.update_text('alert', value='Error: check password or dates!')
        else:
            masterDict = generate_rezzy_dictionary(df)            
            ui.update_select("rezzies", choices=masterDict)
        
    @reactive.Calc
    @reactive.event(input.submit_residents)
    def data():
        df = download_df(input.daterange()[0], input.daterange()[1], input.password())
        df_out, styles = match_schedules(df, input.rezzies())
        return df_out, styles

    @render.data_frame    
    def daysOff_df():
        df_out, styles = data()       
        return render.DataGrid(
            df_out,
            filters=False,
            summary=False,
            width="100%",
            styles=styles,            
        )

    @output
    @render.data_frame
    def legend():
        legend = pd.DataFrame({' ': ['Off Day', 'Holiday/Personal Day', \
                                     'Vacation Day', 'Panel Management', \
                                     'Risk Day']})
        return render.DataGrid(
            legend,
            styles=[
                {
                    'rows': [0],
                    'style': {'background-color': '#8dd3c7'},
                },
                {
                    'rows': [1],
                    'style': {'background-color': '#80b1d3'},
                },
                {
                    'rows': [2],
                    'style': {'background-color': '#b3de69'},
                },
                {
                    'rows': [3],
                    'style': {'background-color': '#fccde5'},
                },
                {
                    'rows': [4],
                    'style': {'background-color': '#d9d9d9'},
                },
            ],
        )
    
    
app = App(app_ui, server)