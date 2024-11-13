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
    average_money = df.select(pl.col("Money In Account").mean()).item()
    q1_money = df.select(pl.col("Money In Account").quantile(0.25)).item()
    median_money = df.select(pl.col("Money In Account").median()).item()
    q3_money = df.select(pl.col("Money In Account").quantile(0.75)).item()
    std_money = df.select(pl.col("Money In Account").std()).item()
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
                dict_leaderboard,
                schema={
                    "Account Name": pl.Utf8,
                    "Money In Account": pl.Float64,
                    "Stocks Invested In": pl.Utf8,
                    "Investopedia Link": pl.Utf8
                }
            ).transpose()
            if (
                len(df2.columns) == 3
            ):  # IF the file has only 3 columns, then add a new column to the dataframe as a place holder
                df2 = df2.with_columns(pl.lit(0).alias("column_3"))
            df2.columns = [
                "Account Name",
                "Money In Account",
                "Stocks Invested In",
                "Investopedia Link",
            ]
            df2 = df2.sort("Money In Account", descending=True)
            _1, q1_money, median_money, q3_money, _2 = get_five_number_summary(
                df2
            )  # get some key numbers for the charts
            min_monies.append(int(df2.select(pl.col("Money In Account").min()).item()))
            max_monies.append(int(df2.select(pl.col("Money In Account").max()).item()))
            q1_monies.append(int(q1_money))
            median_monies.append(int(median_money))
            q3_monies.append(int(q3_money))

        ### This whole section makes the Individual Statistics
        # Load json as dictionary, then organise it properly: https://stackoverflow.com/a/44607210
        with open("backend/leaderboards/leaderboard-latest.json", "r") as file:
            dict_leaderboard = json.load(file)
        df = pl.DataFrame(
            dict_leaderboard,
            schema={
                "Money In Account": pl.Float64,
                "Investopedia Link": pl.Utf8,
                "Stocks Invested In": pl.Utf8
            }
        ).transpose()
        # Set column names in the correct order based on data structure
        df.columns = [
            "Money In Account",
            "Investopedia Link",
            "Stocks Invested In",
        ]
        # Add Account Name from the index
        df = df.with_columns(pl.Series(name="Account Name", values=df.index))
        
        # Sort by Money In Account and add ranking
        df = df.sort("Money In Account", descending=True)
        df = df.with_columns(pl.Series(name="Ranking", values=range(1, 1 + len(df))))
        all_stocks = []
        for stocks in df["Stocks Invested In"]:
            if len(stocks) > 0:
                for x in stocks:
                    all_stocks.append(x[0])
        stock_cnt = Counter(all_stocks)
        stock_cnt = stock_cnt.most_common()  # In order to determine the most common stocks. Now stock_cnt is a list of tuples
        df = df.with_columns(
            pl.col("Stocks Invested In").map_elements(
                lambda x: ", ".join([stock[0] for stock in x])
            ).alias("Stocks Invested In")
        )
        z_scores = zscore(df["Money In Account"].to_numpy())
        df = df.with_columns(pl.Series(name="Z-Score", values=z_scores))
        # Replace Account Name with Account Link
        df = df.with_columns(
            pl.col("Account Name").map_elements(
                lambda name: f'<a href="/players/{name}.html" class="underline text-blue-600 hover:text-blue-800 visited:text-purple-600" target="_blank">{name}</a>'
            ).alias("Account Link")
        )

        # This gets the location of the the GOAT himself, Mr. Miller
        miller_location = df.filter(pl.col("Account Name") == "teachermiller")["Ranking"].item()

        # Drop the old Account Name and Investopedia Link columns
        df = df.drop(["Account Name", "Investopedia Link"])

        # Rearrange columns with Account Link
        df = df.select([
            "Ranking", "Account Link", "Money In Account", 
            "Stocks Invested In", "Z-Score"
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
        df = df.with_columns(
            pl.col("Money In Account").map_elements(
                lambda x: format_currency(x, currency="USD", locale="en_US")
            )
        )
        # Render the html template as shown here: https://stackoverflow.com/a/56296451
        rendered = render_template(
            "index.html",
            average_money="${:,.2f}".format(average_money),
            q1_money="${:,.2f}".format(q1_money),
            median_money="${:,.2f}".format(median_money),
            q3_money="${:,.2f}".format(q3_money),
            std_money="${:,.2f}".format(std_money),
            column_names=column_names,  # Updated column names
            row_data=df.to_numpy().tolist(),
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
        leaderboard_files = sorted(glob("./backend/leaderboards/in_time/*"))
        labels = []
        player_money = []
        rankings = []
        for file in leaderboard_files:
            with open(file, "r") as file:
                dict_leaderboard = json.load(file)
            # Get datetime from filename
            file_name = os.path.basename(file.name)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time_str = date_time_str.replace("_", ":")
            date_time_str = (
                datetime.strptime(date_time_str, "%Y-%m-%d-%H:%M")
                - timedelta(hours=3, minutes=0)
            ).strftime("%H:%M:%S %m-%d-%Y")
            labels.append(date_time_str)

            # Create DataFrame and handle columns properly
            df = pl.DataFrame(
                dict_leaderboard,
                schema={
                    "Account Name": pl.Utf8,
                    "Money In Account": pl.Float64,
                    "Investopedia Link": pl.Utf8,
                    "Stocks": pl.Utf8
                }
            ).transpose()
            if len(df.columns) == 3:
                df = df.with_columns(pl.lit([]).alias("Stocks"))
            
            # Explicitly name columns to avoid confusion
            df.columns = ["Account Name", "Money In Account", "Investopedia Link", "Stocks"]
            
            # Sort and add rankings
            df = df.sort("Money In Account", descending=True)
            df = df.with_columns(pl.Series(name="Ranking", values=range(1, 1 + len(df))))
            
            # Filter for player data
            player_data = df.filter(pl.col("Account Name") == player_name)
            if player_data.height > 0:
                rankings.append(float(player_data["Ranking"].item()))
                player_money.append(float(player_data["Money In Account"].item()))
        
        # Get current player data
        player_data = df.filter(pl.col("Account Name") == player_name)
        investopedia_link = player_data["Investopedia Link"].item()
        
        # Process stocks data
        player_stocks = []
        stocks_data = player_data["Stocks"].item()
        if stocks_data:  # Check if stocks data exists
            for stock in stocks_data:
                player_stocks.append([
                    stock[0],  # ticker
                    float(stock[1].replace("$", "").replace(",", "")),  # invested amount
                    float(stock[2].replace("%", "")),  # percentage change
                ])

        # Render template
        rendered = render_template(
            "player.html",
            labels=labels,
            player_money=player_money,
            player_name=player_name,
            investopedia_link=investopedia_link,
            player_stocks=player_stocks,
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
