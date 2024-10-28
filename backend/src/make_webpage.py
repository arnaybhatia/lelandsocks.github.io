from flask import render_template
import pandas as pd
from scipy.stats import zscore
import flask
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.tz import tzutc
import json

# this whole file is to render the html table
app = flask.Flask("leaderboard")

if __name__ == "__main__":
    with app.app_context():
        # Load json as dictionary, then organise it properly: https://stackoverflow.com/a/44607210
        with open("backend/leaderboards/leaderboard-latest.json", "r") as file:
            dict_leaderboard = json.load(file)
        df = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
        df.reset_index(level=0, inplace=True)
        df.columns = ["Account Name", "Money In Account", "Investopedia Link"]
        df = df.sort_values(by=["Money In Account"], ascending=False)
        df["Ranking"] = range(1, 1 + len(df))
        df["Z-Score"] = zscore(df['Money In Account'])
        df = df[["Ranking", "Account Name", "Money In Account", "Z-Score", "Investopedia Link"]]

        # Get Statistics of the data

        average_money = df["Money In Account"].mean()
        q1_money = df["Money In Account"].quantile(0.25)
        median_money = df["Money In Account"].median()
        q3_money = df["Money In Account"].quantile(0.75)
        std_money = df["Money In Account"].std()


        # Render the html template as shown here: https://stackoverflow.com/a/56296451
        rendered = render_template(
            "index.html",
            average_money=average_money,
            q1_money=q1_money,
            median_money=median_money,
            q3_money=q3_money,
            std_money=std_money,
            column_names=df.columns.values,
            row_data=list(df.values.tolist()),
            link_column="Investopedia Link",
            update_time= datetime.utcnow().astimezone(ZoneInfo('US/Pacific')).strftime("%H:%M:%S %m-%d-%Y"),
            zip=zip,
        )
        print(rendered)
