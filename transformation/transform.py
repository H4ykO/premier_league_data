import pandas as pd

def transform_standings(df):
    df['goal_difference'] = df['goals_for'] - df['goals_against']
    df['win_rate'] = (df['won'] / df['played']).round(2)
    return df

def transform_matches(df):
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['status'] == 'FINISHED'].copy()

    def get_result(row):
        if row ['home_score'] > row['away_score']:
            return 'HOME'
        elif row['home_score'] < row['away_score']:
            return 'AWAY'
        return 'DRAW'
    
    df['result'] = df.apply(get_result, axis=1)
    return df