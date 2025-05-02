#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 23:47:50 2025

@author: galengao
"""

from shiny import App, reactive, render, ui

from urllib.request import urlretrieve

import calendar
import datetime

import numpy as np
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
    
    df_x = df[~df.Name.duplicated()].sort_values(["Role", "Name"], \
                                                 key=lambda x: x.map(roleDict))
    
    masterDict = {r:{x:x for x in df_x[df_x.Role == r]['Name']} \
                  for r in df_x.Role.unique()}
    
    return masterDict


def match_schedules(df, rezzies):
    # filter rezzies of interest    
    dfs = [df[df.Name == x] for x in rezzies]
    
    # True off days
    offDays = [set(df[df.Assignment.astype(str).str.contains('Off')]['Date']) \
                   for df in dfs]
    # Risk days
    riskDays = [set(df[df.Assignment.astype(str).str.contains('Risk')]['Date']) \
                   for df in dfs]
    
    sharedOff = set.intersection(*offDays)
    
    dfs_out = [pd.DataFrame(offDays[i], index=list(offDays[i]), columns=[rezzies[i]]) \
               for i in range(len(rezzies))]
        
    df_out = pd.concat(dfs_out, axis=1)
    
    # sort df_out chronologically
    originalCols = list(df_out.columns)
    
    for r in rezzies:
        dates = []
        for d in df_out[r]:
            if type(d) is str:
                date = datetime.datetime.strptime(d, '%m-%d-%y') # -> datetime obj
                date = date.strftime("%A %b %-d, %Y") # -> 
                dates.append(date)
            else:
                dates.append('')
        df_out[r] = dates
    
    df_out['Year'] = df_out.index.str.split('-').str[2].astype(int)
    df_out['Month'] = df_out.index.str.split('-').str[0].astype(int)
    df_out['Day'] = df_out.index.str.split('-').str[1].astype(int)
        
    df_out = df_out.sort_values(['Year', 'Month', 'Day'])

    return df_out[originalCols], sharedOff

app_ui = ui.page_fluid(
    ui.row(
        ui.column(4, 
                  # Amion password
                  ui.input_password("password", "Password", "mypassword1"),  
              
                  # Date range
                  ui.input_date_range("daterange", "Date range", \
                                      start=datetime.date.today(), \
                                      end=datetime.date.today() + datetime.timedelta(30)),  

                  # Submit button to populate list of residents
                  ui.input_action_button("submit_daterange", "Submit"),  
              
                  ui.input_select(  
                      "rezzies",  
                      "Select resident schedules to compare:",  
                      [],  
                      multiple=True,  
                  ),  
              
                  ui.input_action_button("submit_residents", "Submit"),  

                  ui.output_text_verbatim("url"),
                  ui.input_text("residents", label=""),

              
        ),
    
        ui.column(8,
                  ui.h2("Common Days Off"),
                  ui.output_data_frame("daysOff_df"),
                  ui.output_data_frame("legend"),
        ),

    ),
    
)

def server(input, output, session):

    @render.text
    def url():
        return generate_url(input.daterange()[0], input.daterange()[1],\
                            input.password())
    
    @reactive.effect()
    @reactive.event(input.submit_daterange)
    def update_select_rezzies():
        df = download_df(input.daterange()[0], input.daterange()[1], input.password())
        
        if len(df) == 0:
            ui.update_text('residents', value='Check inputs to field!')
        else:
            masterDict = generate_rezzy_dictionary(df)            
            ui.update_select("rezzies", choices=masterDict)
    
    @render.ui()
    def asdf():
        htmlString = '<table border="0" cellpadding="0" cellspacing="0" class="month">\n<tr><th colspan="7" class="month">January 2025</th></tr>\n<tr><th class="mon">Mon</th><th class="tue">Tue</th><th class="wed">Wed</th><th class="thu">Thu</th><th class="fri">Fri</th><th class="sat">Sat</th><th class="sun">Sun</th></tr>\n<tr><td class="noday">&nbsp;</td><td class="noday">&nbsp;</td><td class="wed">1</td><td class="thu">2</td><td class="fri">3</td><td class="sat">4</td><td class="sun">5</td></tr>\n<tr><td class="mon">6</td><td class="tue">7</td><td class="wed">8</td><td class="thu">9</td><td class="fri">10</td><td class="sat">11</td><td class="sun">12</td></tr>\n<tr><td class="mon", bgcolor= "red">13</td><td class="tue", bgcolor= "red">14</td><td class="wed">15</td><td class="thu">16</td><td class="fri">17</td><td class="sat">18</td><td class="sun">19</td></tr>\n<tr><td class="mon", bgcolor= "red">20</td><td class="tue", bgcolor= "red">21</td><td class="wed">22</td><td class="thu">23</td><td class="fri">24</td><td class="sat">25</td><td class="sun">26</td></tr>\n<tr><td class="mon", bgcolor= "red">27</td><td class="tue", bgcolor= "red">28</td><td class="wed">29</td><td class="thu">30</td><td class="fri">31</td><td class="noday">&nbsp;</td><td class="noday">&nbsp;</td></tr>\n</table>\n'
        return ui.HTML(htmlString)
    
    # @render.ui  
    # def calendar():
        # htmlString = '<table border="0" cellpadding="0" cellspacing="0" class="month">\n<tr><th colspan="7" class="month">January 2025</th></tr>\n<tr><th class="mon">Mon</th><th class="tue">Tue</th><th class="wed">Wed</th><th class="thu">Thu</th><th class="fri">Fri</th><th class="sat">Sat</th><th class="sun">Sun</th></tr>\n<tr><td class="noday">&nbsp;</td><td class="noday">&nbsp;</td><td class="wed">1</td><td class="thu">2</td><td class="fri">3</td><td class="sat">4</td><td class="sun">5</td></tr>\n<tr><td class="mon">6</td><td class="tue">7</td><td class="wed">8</td><td class="thu">9</td><td class="fri">10</td><td class="sat">11</td><td class="sun">12</td></tr>\n<tr><td class="mon", bgcolor= "red">13</td><td class="tue", bgcolor= "red">14</td><td class="wed">15</td><td class="thu">16</td><td class="fri">17</td><td class="sat">18</td><td class="sun">19</td></tr>\n<tr><td class="mon", bgcolor= "red">20</td><td class="tue", bgcolor= "red">21</td><td class="wed">22</td><td class="thu">23</td><td class="fri">24</td><td class="sat">25</td><td class="sun">26</td></tr>\n<tr><td class="mon", bgcolor= "red">27</td><td class="tue", bgcolor= "red">28</td><td class="wed">29</td><td class="thu">30</td><td class="fri">31</td><td class="noday">&nbsp;</td><td class="noday">&nbsp;</td></tr>\n</table>\n'
        # htmlString = generate_calendar_HTML(coincidingDaysOff(df, ["a", "b"]))
        # return htmlString
        
    @reactive.Calc
    @reactive.event(input.submit_residents)
    def data():
        df = download_df(input.daterange()[0], input.daterange()[1], input.password())
        df_out, sharedOff = match_schedules(df, input.rezzies())
        return df_out, sharedOff
        
    @render.data_frame
    def daysOff_df():
        df_out, sharedOff = data()
        return render.DataGrid(
            df_out,
            filters=False,
            summary=False,
            width="100%",
            styles=[  
                # Center the text of each cell (using Bootstrap utility class) 
                {  
                    "class": "text-center",
                },  
                # Highlight congruent rows' colors 
                {
                    "rows": [list(df_out.index).index(x) for x in sharedOff],  
                    "cols": list(df_out.columns),
                    "style": {"background-color": "#ffdbaf"},  # (#fdb462)
                },
            ],
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