import json
import os
from collections import Counter
from datetime import datetime, timedelta
from glob import glob

import flask
import polars as pl
from babel.numbers import format_currency
from flask import render_template
from scipy.stats import zscore
from zoneinfo import ZoneInfo

# this whole file is to render the html table
app = flask.Flask("leaderboard")


def get_five_number_summary(df):
    average_money = df.select(pl.col("Money In Account").mean())[0,0]
    q1_money = df.select(pl.col("Money In Account").quantile(0.25))[0,0]
    median_money = df.select(pl.col("Money In Account").median())[0,0]
    q3_money = df.select(pl.col("Money In Account").quantile(0.75))[0,0]
    std_money = df.select(pl.col("Money In Account").std())[0,0]
    return average_money, q1_money, median_money, q3_money, std_money


def make_index_page():
    with app.app_context():
        leaderboard_files = sorted(
            glob("./backend/leaderboards/in_time/*")
        )  # This section formats everything nicely for the charts!
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
            date_time_str = (
                datetime.strptime(date_time_str, "%Y-%m-%d-%H:%M")
                - timedelta(hours=3, minutes=0)
            ).strftime("%H:%M:%S %m-%d-%Y")  # The final string in the right format
            labels.append(date_time_str)

            df2 = pl.DataFrame(
                {k: [v[0], v[1], v[2], v[3] if len(v) > 3 else 0] for k, v in dict_leaderboard.items()}
            ).with_columns([
                pl.col("column_0").alias("Account Name"),
                pl.col("column_1").alias("Money In Account"),
                pl.col("column_2").alias("Stocks Invested In"),
                pl.col("column_3").alias("Investopedia Link"),
            ])
            
            df2 = df2.sort("Money In Account", descending=True)
            _1, q1_money, median_money, q3_money, _2 = get_five_number_summary(df2)
            min_monies.append(int(df2.select(pl.col("Money In Account").min())[0,0]))
            max_monies.append(int(df2.select(pl.col("Money In Account").max())[0,0]))
            q1_monies.append(int(q1_money))
            median_monies.append(int(median_money))
            q3_monies.append(int(q3_money))

        ### This whole section makes the Individual Statistics
        # Load json as dictionary, then organise it properly: https://stackoverflow.com/a/44607210
        with open("backend/leaderboards/leaderboard-latest.json", "r") as file:
            dict_leaderboard = json.load(file)
            
        df = pl.DataFrame(
            {k: [v[0], v[1], v[2], v[3]] for k, v in dict_leaderboard.items()}
        ).with_columns([
            pl.col("column_0").alias("Account Name"),
            pl.col("column_1").alias("Money In Account"),
            pl.col("column_2").alias("Investopedia Link"),
            pl.col("column_3").alias("Stocks Invested In"),
        ])
        
        df = df.sort("Money In Account", descending=True)
        df = df.with_row_count("Ranking", offset=1)

        all_stocks = []
        for stocks in df.select("Stocks Invested In").to_series():
            if len(stocks) > 0:
                for x in stocks:
                    all_stocks.append(x[0])
        stock_cnt = Counter(all_stocks).most_common()

        # Convert stocks to string
        df = df.with_columns([
            pl.col("Stocks Invested In").map_elements(
                lambda x: ", ".join([stock[0] for stock in x])
            )
        ])

        # Calculate Z-Score
        df = df.with_columns([
            ((pl.col("Money In Account") - pl.col("Money In Account").mean()) / 
             pl.col("Money In Account").std()).alias("Z-Score")
        ])

        # Create Account Link column
        df = df.with_columns([
            pl.col("Account Name").map_elements(
                lambda x: f'<a href="/players/{x}.html" class="underline text-blue-600 hover:text-blue-800 visited:text-purple-600" target="_blank">{x}</a>'
            ).alias("Account Link")
        ])

        # This gets the location of the the GOAT himself, Mr. Miller
        miller_location = df.filter(pl.col("Account Name") == "teachermiller")["Ranking"][0]

        # Drop the old Account Name and Investopedia Link columns
        df = df.drop(columns=["Account Name", "Investopedia Link"])

        # Rearrange columns with Account Link
        df = df.select([
            "Ranking",
            "Account Link",
            "Money In Account",
            "Stocks Invested In",
            "Z-Score"
        ])

        # Update column_names
        column_names = [
            "Ranking",
            "Account Link",
            "Money In Account",
            "Stocks Invested In",
            "Z-Score",
        ]
        # This rearranges the columns to make things be in the right order
        average_money, q1_money, median_money, q3_money, std_money = (
            get_five_number_summary(df)
        )
        df = df.with_columns([
            pl.col("Money In Account").map_elements(
                lambda x: format_currency(x, currency="USD", locale="en_US")
            )
        ])

        # Convert to list for template rendering
        row_data = df.to_pandas().values.tolist()

        # Render the html template as shown here: https://stackoverflow.com/a/56296451
        rendered = render_template(
            "index.html",
            average_money="${:,.2f}".format(average_money),
            q1_money="${:,.2f}".format(q1_money),
            median_money="${:,.2f}".format(median_money),
            q3_money="${:,.2f}".format(q3_money),
            std_money="${:,.2f}".format(std_money),
            column_names=column_names,  # Updated column names
            row_data=row_data,
            link_column="Account Link",  # Update link column
            update_time=datetime.utcnow()
            .astimezone(ZoneInfo("US/Pacific"))
            .strftime("%H:%M:%S %m-%d-%Y"),
            labels=labels,
            miller_location=miller_location,
            min_monies=min_monies,
            max_monies=max_monies,
            q1_monies=q1_monies,
            median_monies=median_monies,
            q3_monies=q3_monies,
            stock_cnt=stock_cnt,
            zip=zip,
        )
        return rendered


def make_user_page(player_name):
    with app.app_context():
        leaderboard_files = sorted(
            glob("./backend/leaderboards/in_time/*")
        )  # This section formats everything nicely for the charts!
        labels = []
        player_money = []
        rankings = []
        for file in leaderboard_files:
            with open(file, "r") as file:
                dict_leaderboard = json.load(file)
            # Get a date time object from the file name, so I can use it as a label for the chart
            file_name = os.path.basename(file.name)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time_str = date_time_str.replace("_", ":")
            date_time_str = (
                datetime.strptime(date_time_str, "%Y-%m-%d-%H:%M")
                - timedelta(hours=3, minutes=0)
            ).strftime("%H:%M:%S %m-%d-%Y")  # The final string in the right format
            labels.append(date_time_str)

            df = pl.DataFrame(
                {k: [v[0], v[1], v[2], v[3] if len(v) > 3 else 0] for k, v in dict_leaderboard.items()}
            ).with_columns([
                pl.col("column_0").alias("Account Name"),
                pl.col("column_1").alias("Money In Account"),
                pl.col("column_2").alias("Stocks Invested In"),
                pl.col("column_3").alias("Investopedia Link"),
            ])
            
            df = df.sort("Money In Account", descending=True)
            df = df.with_row_count("Ranking", offset=1)
            if player_name in df["Account Name"].to_list():
                rankings.append(
                    float(
                        df.filter(pl.col("Account Name") == player_name)["Ranking"][0]
                    )
                )
                player_money.append(
                    float(
                        df.filter(pl.col("Account Name") == player_name)["Money In Account"][0]
                    )
                )
        investopedia_link = df.filter(pl.col("Account Name") == player_name)["Investopedia Link"][0]
        player_stocks = []
        player_stocks_data = df.filter(pl.col("Account Name") == player_name)["Stocks Invested In"][0]
        for stock in player_stocks_data:
            player_stocks.append(
                [
                    stock[0],  # ticker
                    float(
                        stock[1].replace("$", "").replace(",", "")
                    ),  # invested amount
                    float(stock[2].replace("%", "")),  # percentage change
                ]
            )

        rendered = render_template(
            "player.html",
            labels=labels,
            player_money=player_money,
            player_name=player_name,
            investopedia_link=investopedia_link,
            player_stocks=player_stocks,  # Add player_stocks to template
            update_time=datetime.utcnow()
            .astimezone(ZoneInfo("US/Pacific"))
            .strftime("%H:%M:%S %m-%d-%Y"),
            zip=zip,
        )
        return rendered


if __name__ == "__main__":
    with app.app_context():
        ### This whole section makes the chart shown at the top of the page!
        print(make_index_page())
