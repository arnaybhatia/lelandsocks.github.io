from flask import render_template
import pandas as pd
from scipy.stats import zscore
import flask
from glob import glob
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.tz import tzutc
import json
import os
from babel.numbers import format_currency

# this whole file is to render the html table
app = flask.Flask("leaderboard")


def get_five_number_summary(df):
    average_money = df["Money In Account"].mean()
    q1_money = df["Money In Account"].quantile(0.25)
    median_money = df["Money In Account"].median()
    q3_money = df["Money In Account"].quantile(0.75)
    std_money = df["Money In Account"].std()
    return average_money, q1_money, median_money, q3_money, std_money


if __name__ == "__main__":
    with app.app_context():
        ### This whole section makes the chart shown at the top of the page!
        leaderboard_files = sorted(glob(
            "./backend/leaderboards/in_time/*"
        ))  # This section formats everything nicely for the charts!
        labels = []
        min_monies = []
        max_monies = []
        q1_monies = []
        median_monies = []
        q3_monies = []
        for file in leaderboard_files:
            with open(file, "r") as file:
                dict_leaderboard = json.load(file)
            # Get a date time object from the file name, so I can use it as a label for the chart
            file_name = os.path.basename(file.name)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time_str = date_time_str.replace("_", ":")
            date_time_str = datetime.strptime(date_time_str, "%Y-%m-%d-%H:%M").strftime(
                "%H:%M:%S %m-%d-%Y"
            )  # The final string in the right format
            labels.append(date_time_str)

            df2 = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
            df2.reset_index(level=0, inplace=True)
            df2.columns = ["Account Name", "Money In Account", "Investopedia Link"]
            df2 = df2.sort_values(by=["Money In Account"], ascending=False)
            _1, q1_money, median_money, q3_money, _2 = get_five_number_summary(
                df2
            )  # get some key numbers for the charts
            min_monies.append(int(df2["Money In Account"].min()))
            max_monies.append(int(df2["Money In Account"].max()))
            q1_monies.append(int(q1_money))
            median_monies.append(int(median_money))
            q3_monies.append(int(q3_money))

        ### This whole section makes the Individual Statistics
        # Load json as dictionary, then organise it properly: https://stackoverflow.com/a/44607210
        with open("backend/leaderboards/leaderboard-latest.json", "r") as file:
            dict_leaderboard = json.load(file)
        df = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
        df.reset_index(level=0, inplace=True)
        df.columns = ["Account Name", "Money In Account", "Investopedia Link"]
        df = df.sort_values(by=["Money In Account"], ascending=False)
        df["Ranking"] = range(1, 1 + len(df))
        df["Z-Score"] = zscore(df["Money In Account"])
        df = df[
            [
                "Ranking",
                "Account Name",
                "Money In Account",
                "Z-Score",
                "Investopedia Link",
            ]
        ]  # This rearranges the columns to make things be in the right order
        average_money, q1_money, median_money, q3_money, std_money = (
            get_five_number_summary(df)
        )

        df["Money In Account"] = df["Money In Account"].apply(
            lambda x: format_currency(x, currency="USD", locale="en_US")
        )
        # Render the html template as shown here: https://stackoverflow.com/a/56296451
        rendered = render_template(
            "index.html",
            average_money="${:,.2f}".format(average_money),
            q1_money="${:,.2f}".format(q1_money),
            median_money="${:,.2f}".format(median_money),
            q3_money="${:,.2f}".format(q3_money),
            std_money="${:,.2f}".format(std_money),
            column_names=df.columns.values,
            row_data=list(df.values.tolist()),
            link_column="Investopedia Link",
            update_time=datetime.utcnow()
            .astimezone(ZoneInfo("US/Pacific"))
            .strftime("%H:%M:%S %m-%d-%Y"),
            labels=labels,
            min_monies=min_monies,
            max_monies=max_monies,
            q1_monies=q1_monies,
            median_monies=median_monies,
            q3_monies=q3_monies,
            zip=zip,
        )
        print(rendered)
