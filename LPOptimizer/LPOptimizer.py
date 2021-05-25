import pandas as pd
from pulp import *
import openpyxl
import re
import numpy as np

Sport = input('Enter Sport..... ')
teams = pd.DataFrame()
dfplayers = pd.DataFrame()
if Sport == 'NBA':
    pos_num_available = {"PG": 2,
                    "SG": 2,
                    "SF": 2, 
                    "PF": 2,
                    "C": 1}
    salary_cap = 60000
    players = pd.read_csv('FanDuel-NBA-2021-05-19.csv', usecols= ['Id', 'Position', 'FPPG', 'Salary', 'Nickname', 'Injury Indicator'])
    dfplayers = pd.read_excel('Players-2021-02-12.xlsx', 'Players')
    dfteams = pd.read_excel('MinProjection.xlsx', 'Output2')
    dfteams = dfteams[['TEAM', 'Game_ID', 'Team_ID', 'MIN', 'FGA','FTA', 'TOV']]
    dfteams = dfteams.rename(columns = {'MIN': 'TM_MIN', 'FGA':'TM_FGA', 'FTA': 'TM_FTA', 'TOV': 'TM_TOV'} )
    dfplayers = pd.merge(dfplayers, dfteams, how = 'left', left_on = ['Game_ID'], right_on = ['Game_ID'])
    dfplayers['Usage'] = 100 * ((dfplayers['FGA'] + 0.44 * dfplayers['FTA'] + dfplayers['TOV']) * 
                            (dfplayers['TM_MIN'] / 5)) / (dfplayers['MIN'] * (dfplayers['TM_FGA'] + 0.44 * dfplayers['TM_FTA'] + dfplayers['TM_TOV']))

    Player_level_agg =  dfplayers.groupby('Player').agg({
    'PTS': 'mean',
    'FGA': 'mean',
    'FTA': 'mean',
    'TOV': 'mean',
    'MIN': 'mean',
    'Usage': 'mean'}).round(1)
    players= pd.merge(players, Player_level_agg, how = 'left', left_on = ['Nickname'], right_on = ['Player'] )
    players['Mscore'] = (players['Usage'] * .03) + (players['PTS'] * .03) + (players['MIN'] * .02)

elif Sport == 'WNBA':
    pos_num_available = {"G": 3,
                         "F": 4}
    salary_cap = 40000
    players = pd.read_csv('FanDuel-WNBA-2021-05-25.csv', usecols= ['Id', 'Position', 'FPPG', 'Salary', 'Nickname', 'Injury Indicator'])
    teams2021 = pd.read_excel('WNBA-teams.xlsx', 'Sheet1')
    teams2020 = pd.read_excel('WNBA-teams.xlsx', 'Sheet2')
    teams2019 = pd.read_excel('WNBA-teams.xlsx', 'Sheet3')
    #teams = teams.append(teams2019)
    teams = teams.append(teams2020)
    #teams = teams.append(teams2021)
    dfplayers2021 = pd.read_excel('WNBA-2021.xlsx', 'Sheet1')
    dfplayers2020 = pd.read_excel('WNBA-2020.xlsx', 'Sheet1')
    dfplayers2019 = pd.read_excel('WNBA-2019.xlsx', 'Sheet1')
    dfplayers = dfplayers.append(dfplayers2021)
    #dfplayers = dfplayers.append(dfplayers2020)
    players = pd.merge(players, dfplayers, how = 'left', left_on= ['Nickname'], right_on = ['PLAYER'])
    players['Mscore'] = (players['MIN']*0.03) + (players['REB'] * 0.01) + (players['AST'] *0.01) + (players['STL'] *0.01) + (players['PTS'] * 0.04)
   # dfplayers['Usage'] = 100 * ((dfplayers['FGA'] + 0.44 * dfplayers['FTA'] + dfplayers['TOV']) * 
   #                         (dfplayers['TM_MIN'] / 5)) / (dfplayers['MIN'] * (dfplayers['TM_FGA'] + 0.44 * dfplayers['TM_FTA'] + dfplayers['TM_TOV']))
elif Sport == 'MLB':
    pos_num_available = {"P": 1,
                         "C/1B": 1,
                         "2B": 1,
                         "3B": 1,
                         "SS": 1,
                         "OF": 4}
    salary_cap = 35000
    players = pd.read_csv('FanDuel-MLB-2021-05-25.csv', usecols= ['Id', 'Position', 'FPPG', 'Salary', 'Nickname', 'Injury Indicator', 'Batting Order', 'Mscore'])
    players = players[players['Batting Order'] > 0]


playersNameDict = dict(zip(players['Id'], players['Nickname']))
players['Injury Indicator'] = players['Injury Indicator'].astype(str)
players = players[players['Injury Indicator'] != 'O']
players = players[players['Injury Indicator'] != 'IL']

#players['Score'] = (players['FPPG'] * .75) * players['Mscore']

conditions = [
    (players['Mscore'] > 0)]

choices = [(players['FPPG'] * .75) * players['Mscore']]
players['Score'] = np.select(conditions, choices, default = players['FPPG'] * .95)

players.to_csv('Players.csv')

#players['Usage'] = 100 * ((dfplayers['FGA'] + 0.44 * dfplayers['FTA'] + dfplayers['TOV']) * 
#                            (dfplayers['TM_MIN'] / 5)) / (dfplayers['MIN'] * (dfplayers['TM_FGA'] + 0.44 * dfplayers['TM_FTA'] + dfplayers['TM_TOV']))


availables = players.groupby(["Position", "Id", "Score", "Salary"]).agg('count')
availables = availables.reset_index()

salaries = {}
points = {}
teams = {}
lineups_dict = {}

for pos in availables.Position.unique():
    available_pos = availables[availables.Position == pos]
    salary = list(available_pos[['Id', 'Salary']].set_index("Id").to_dict().values())[0]
    point = list(available_pos[['Id', 'Score']].set_index("Id").to_dict().values())[0]

    salaries[pos] = salary
    points[pos] = point


df2 = pd.DataFrame()
for lineup in range(1, 10):
    _vars = {k: LpVariable.dict(k, v, cat='Binary') for k, v in points.items()}
    prob = LpProblem("Fantasy", LpMaximize)
    
    rewards = []
    costs = []
    position_constraints = []

    for k, v in _vars.items():
        costs += lpSum([salaries[k][i] * _vars[k][i] for i in v])
        rewards += lpSum([points[k][i] * _vars[k][i] for i in v])
        prob += lpSum([_vars[k][i] for i in v]) == pos_num_available[k]

    prob += lpSum(rewards)
    prob += lpSum(costs) <= salary_cap
    if not lineup == 1:
        prob += (lpSum(rewards) <= total_score-0.01)
    prob.solve()
    
    score= str(prob.objective)
    constraints = [str(const) for const in prob.constraints.values()]
    #colnum = 1
    lineupList = []
    for v in prob.variables():
        score = score.replace(v.name, str(v.varValue))
        if v.varValue !=0:
            lineupList.append(v.name)
            print(lineupList)
        
    total_score = eval(score)
    print(lineup, total_score)
    lineupList.append(total_score)
    lineups_dict.update({lineup: lineupList})    
df = pd.DataFrame(lineups_dict)
df = df.T
df.to_csv('output.csv')

if Sport == 'NBA':
    newcols = ['C', 'PF1', 'PF2', 'PG1', 'PG2', 'SF1', 'SF2', 'SG1', 'SG2', 'Total Score']
    df.columns = newcols
    positions = ['C', 'PF1', 'PF2', 'PG1', 'PG2', 'SF1', 'SF2', 'SG1', 'SG2']
    removeKeys = ['C_', 'PF_', 'SF_', 'SG_', 'PG_']
    for pos in positions:
        for removeKey in removeKeys:
            df[pos] = df[pos].str.replace(removeKey,"")
        df[pos] = df[pos].str.replace("_", "-")

    df = df[['PG1', 'PG2', 'SG1', 'SG2', 'SF1', 'SF2', 'PF1', 'PF2', 'C', 'Total Score']]
    dfPlayerName = df
    for pos in positions:
        dfPlayerName[pos] = dfPlayerName[pos].replace(playersNameDict)
elif Sport == 'WNBA':
     newcols = ['F1', 'F2', 'F3', 'F4', 'G1', 'G2', 'G3', 'Total Score']
     df.columns = newcols
     positions = ['F1', 'F2', 'F3', 'F4', 'G1', 'G2', 'G3']
     removeKeys = ['F_', 'G_']
     for pos in positions:
        for removeKey in removeKeys:
            df[pos] = df[pos].str.replace(removeKey,"")
        df[pos] = df[pos].str.replace("_", "-")
     df = df[['G1', 'G2', 'G3', 'F1', 'F2', 'F3', 'F4','Total Score']]
     dfPlayerName = df
     for pos in positions:
        dfPlayerName[pos] = dfPlayerName[pos].replace(playersNameDict)
elif Sport == 'MLB':
     newcols = ['2B', '3B', 'C_1B', 'OF1', 'OF2', 'OF3', 'OF4', 'P', 'SS', 'Total Score']
     print(df.columns)
     df.columns = newcols
     positions = ['P', 'C_1B', '2B', '3B', 'SS', 'OF1', 'OF2', 'OF3', 'OF4']
     removeKeys = ['P_', 'C_1B_', '2B_', '3B_', 'SS_', 'OF_']
     for pos in positions:
        for removeKey in removeKeys:
            try:
                df[pos] = df[pos].str.replace(removeKey,"")
            except:
                print("here")
        df[pos] = df[pos].str.replace("_", "-")
     df = df[['P', 'C_1B', '2B', '3B', 'SS', 'OF1', 'OF2', 'OF3', 'OF4', 'Total Score']]
     dfPlayerName = df
     for pos in positions:
        dfPlayerName[pos] = dfPlayerName[pos].replace(playersNameDict)



df.to_csv('FD.csv')
dfPlayerName.to_csv('FD_Players.csv')

