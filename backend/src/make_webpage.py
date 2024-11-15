import json
import os
from collections import Counter
from datetime import datetime, timedelta
from glob import glob

import flask
import pandas as pd
from babel.numbers import format_currency
from flask import render_template
from scipy.stats import zscore
from zoneinfo import ZoneInfo
import yfinance as yf

# this whole file is to render the html table
app = flask.Flask("leaderboard")


def get_five_number_summary(df):
    average_money = df["Money In Account"].mean()
    q1_money = df["Money In Account"].quantile(0.25)
    median_money = df["Money In Account"].median()
    q3_money = df["Money In Account"].quantile(0.75)
    std_money = df["Money In Account"].std()
    return average_money, q1_money, median_money, q3_money, std_money


def make_index_page():
    with app.app_context():
        leaderboard_files = sorted(glob("./backend/leaderboards/in_time/*"))
        labels = []
        min_monies = []
        max_monies = []
        q1_monies = []
        median_monies = []
        q3_monies = []
        sp500_prices = []
        timestamps = []

        # First pass - collect all timestamps
        for file in leaderboard_files:
            file_name = os.path.basename(file)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time = datetime.strptime(
                date_time_str.replace("_", ":"), "%Y-%m-%d-%H:%M"
            )
            timestamps.append(date_time)

        # Fetch S&P 500 data for the entire period
        start_date = min(timestamps).date()
        end_date = max(timestamps).date() + timedelta(days=1)
        sp500 = yf.download("SPY", start=start_date, end=end_date, interval="1h")

        # Get initial S&P 500 price for relative calculation
        initial_sp500_price = None
        initial_date = start_date
        while initial_sp500_price is None and initial_date <= end_date:
            try:
                initial_sp500_price = float(sp500.loc[initial_date, "Close"])
            except KeyError:
                initial_date += timedelta(days=1)

        if initial_sp500_price is None:
            initial_sp500_price = float(sp500["Close"].iloc[0])

        # Process each file
        for file, timestamp in zip(leaderboard_files, timestamps):
            with open(file, "r") as f:
                dict_leaderboard = json.load(f)

            # Format timestamp for label (with full UTC date-time info)
            date_time_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
            labels.append(date_time_str)

            # Get S&P 500 price for this date and convert to relative value from 100k investment
            date_for_sp500 = timestamp.date()
            try:
                current_sp500_price = float(sp500.loc[date_for_sp500, "Close"])
                relative_return = current_sp500_price / initial_sp500_price
                sp500_price = 100000 * relative_return
            except KeyError:
                # If exact date not found, get the most recent previous date
                previous_dates = sp500.index[sp500.index.date <= date_for_sp500]
                if len(previous_dates) > 0:
                    current_sp500_price = float(
                        sp500.loc[previous_dates[-1], "Close"].iloc[0]
                    )
                    relative_return = current_sp500_price / initial_sp500_price
                    sp500_price = 100000 * relative_return
                else:
                    sp500_price = None
            sp500_prices.append(sp500_price)

            # Process money data
            df2 = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
            df2.reset_index(level=0, inplace=True)
            if (
                len(df2.columns) == 3
            ):  # IF the file has only 3 columns, then add a new column to the dataframe as a place holder
                df2["Stocks Invested In"] = [0 for i in range(len(df2))]
            df2.columns = [
                "Account Name",
                "Money In Account",
                "Stocks Invested In",
                "Investopedia Link",
            ]
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
        df.columns = [
            "Account Name",
            "Money In Account",
            "Investopedia Link",
            "Stocks Invested In",
        ]
        df = df.sort_values(by=["Money In Account"], ascending=False)
        df["Ranking"] = range(1, 1 + len(df))
        all_stocks = []
        for stocks in df["Stocks Invested In"]:
            if len(stocks) > 0:
                for x in stocks:
                    all_stocks.append(x[0])
        stock_cnt = Counter(all_stocks)
        stock_cnt = stock_cnt.most_common()  # In order to determine the most common stocks. Now stock_cnt is a list of tuples
        df["Stocks Invested In"] = df["Stocks Invested In"].apply(
            lambda x: ", ".join([stock[0] for stock in x])
        )
        df["Z-Score"] = zscore(df["Money In Account"])
        # Replace Account Name with Account Link
        df["Account Link"] = df.apply(
            lambda row: f'<a href="/players/{row["Account Name"]}.html" class= "underline text-blue-600 hover:text-blue-800 visited:text-purple-600 {row["Account Name"]}" target="_blank">{row["Account Name"]}</a>',
            axis=1,
        )

        # This gets the location of the the GOAT himself, Mr. Miller
        miller_location = df.loc[
            df["Account Name"] == "teachermiller", "Ranking"
        ].values[0]

        # Drop the old Account Name and Investopedia Link columns
        df = df.drop(columns=["Account Name", "Investopedia Link"])

        # Rearrange columns with Account Link
        df = df[
            [
                "Ranking",
                "Account Link",
                "Money In Account",
                "Stocks Invested In",
                "Z-Score",
            ]
        ]

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
            column_names=column_names,  # Updated column names
            row_data=list(df.values.tolist()),
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
            sp500_prices=sp500_prices,  # Add S&P 500 prices
            zip=zip,
        )
        # print("all done with the index page")
        return rendered


def make_user_page(player_name):
    with app.app_context():
        leaderboard_files = sorted(glob("./backend/leaderboards/in_time/*"))
        labels = []
        player_money = []
        sp500_prices = []
        timestamps = []

        # First collect all timestamps
        for file in leaderboard_files:
            file_name = os.path.basename(file)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time = datetime.strptime(
                date_time_str.replace("_", ":"), "%Y-%m-%d-%H:%M"
            )
            timestamps.append(date_time)

        # Fetch S&P 500 data
        start_date = min(timestamps).date()
        end_date = max(timestamps).date() + timedelta(days=1)
        sp500 = yf.download("SPY", start=start_date, end=end_date, interval="1h")

        # Get initial S&P 500 price
        initial_sp500_price = None
        initial_date = start_date
        while initial_sp500_price is None and initial_date <= end_date:
            try:
                initial_sp500_price = float(sp500.loc[initial_date, "Close"])
            except KeyError:
                initial_date += timedelta(days=1)

        if initial_sp500_price is None:
            initial_sp500_price = float(sp500["Close"].iloc[0])

        # Process each file
        for file, timestamp in zip(leaderboard_files, timestamps):
            with open(file, "r") as file:
                dict_leaderboard = json.load(file)

            # Format timestamp
            date_time_str = (timestamp - timedelta(hours=3)).strftime(
                "%Y-%m-%d"  # Changed format to yyyy-mm-dd
            )
            labels.append(date_time_str)

            # Get S&P 500 price
            date_for_sp500 = timestamp.date()
            try:
                current_sp500_price = float(sp500.loc[date_for_sp500, "Close"])
                relative_return = current_sp500_price / initial_sp500_price
                sp500_price = 100000 * relative_return
            except KeyError:
                previous_dates = sp500.index[sp500.index.date <= date_for_sp500]
                if len(previous_dates) > 0:
                    current_sp500_price = float(
                        sp500.loc[previous_dates[-1], "Close"].iloc[0]
                    )
                    relative_return = current_sp500_price / initial_sp500_price
                    sp500_price = 100000 * relative_return
                else:
                    sp500_price = None
            sp500_prices.append(sp500_price)

            # Process player data
            df = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
            df.reset_index(level=0, inplace=True)
            if (
                len(df.columns) == 3
            ):  # IF the file has only 3 columns, then add a new column to the dataframe as a place holder
                df["Stocks Invested In"] = [0 for i in range(len(df))]
            df.columns = [
                "Account Name",
                "Money In Account",
                "Investopedia Link",
                "Stocks Invested In",
            ]

            df = df.sort_values(by=["Money In Account"], ascending=False)
            df["Ranking"] = range(1, 1 + len(df))
            if player_name in df["Account Name"].values:
                player_money.append(
                    float(
                        df.loc[
                            df["Account Name"] == player_name, "Money In Account"
                        ].values[0]
                    )
                )
        investopedia_link = df.loc[
            df["Account Name"] == player_name, "Investopedia Link"
        ].values[0]
        player_stocks = []
        player_stocks_data = df.loc[
            df["Account Name"] == player_name, "Stocks Invested In"
        ].iloc[0]
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
            player_stocks=player_stocks,
            update_time=datetime.utcnow()
            .astimezone(ZoneInfo("US/Pacific"))
            .strftime("%H:%M:%S %m-%d-%Y"),
            sp500_prices=sp500_prices,
            zip=zip,
        )
        return rendered


def make_user_pages(usernames):
    """Generate HTML pages for multiple users at once"""
    with app.app_context():
        leaderboard_files = sorted(glob("./backend/leaderboards/in_time/*"))
        labels = []
        all_dfs = []
        timestamps = []
        sp500_prices = []

        # Collect timestamps and process files
        for file in leaderboard_files:
            file_name = os.path.basename(file)
            date_time_str = file_name[len("leaderboard-") : -len(".json")]
            date_time = datetime.strptime(
                date_time_str.replace("_", ":"), "%Y-%m-%d-%H:%M"
            )
            timestamps.append(date_time)

        # Fetch S&P 500 data
        start_date = min(timestamps).date()
        end_date = max(timestamps).date() + timedelta(days=1)
        sp500 = yf.download("SPY", start=start_date, end=end_date, interval="1h")

        # Get initial S&P 500 price
        initial_sp500_price = None
        initial_date = start_date
        while initial_sp500_price is None and initial_date <= end_date:
            try:
                initial_sp500_price = float(sp500.loc[initial_date, "Close"])
            except KeyError:
                initial_date += timedelta(days=1)

        if initial_sp500_price is None:
            initial_sp500_price = float(sp500["Close"].iloc[0])

        # Process each timestamp
        for file, timestamp in zip(leaderboard_files, timestamps):
            # Process datetime for label
            date_time_str = (timestamp - timedelta(hours=3)).strftime(
                "%Y-%m-%d"  # Changed format to yyyy-mm-dd
            )
            labels.append(date_time_str)

            # Get S&P 500 price
            date_for_sp500 = timestamp.date()
            try:
                current_sp500_price = float(sp500.loc[date_for_sp500, "Close"])
                relative_return = current_sp500_price / initial_sp500_price
                sp500_price = 100000 * relative_return
            except KeyError:
                previous_dates = sp500.index[sp500.index.date <= date_for_sp500]
                if len(previous_dates) > 0:
                    current_sp500_price = float(
                        sp500.loc[previous_dates[-1], "Close"].iloc[0]
                    )
                    relative_return = current_sp500_price / initial_sp500_price
                    sp500_price = 100000 * relative_return
                else:
                    sp500_price = None
            sp500_prices.append(sp500_price)

            # Process leaderboard data
            with open(file, "r") as f:
                dict_leaderboard = json.load(f)
            # ...existing DataFrame processing code...
            df = pd.DataFrame.from_dict(dict_leaderboard, orient="index")
            df.reset_index(level=0, inplace=True)
            if len(df.columns) == 3:
                df["Stocks Invested In"] = [0 for i in range(len(df))]
            df.columns = [
                "Account Name",
                "Money In Account",
                "Investopedia Link",
                "Stocks Invested In",
            ]
            df = df.sort_values(by=["Money In Account"], ascending=False)
            df["Ranking"] = range(1, 1 + len(df))
            all_dfs.append(df)

        # Get latest df for stock information
        latest_df = all_dfs[-1]

        # Process each user using the pre-processed data
        for player_name in usernames:
            player_money = []
            rankings = []

            # Check if player exists in latest data
            if player_name not in latest_df["Account Name"].values:
                continue

            # Extract data for this player from all timepoints
            for df in all_dfs:
                if player_name in df["Account Name"].values:
                    rankings.append(
                        float(
                            df.loc[df["Account Name"] == player_name, "Ranking"].values[
                                0
                            ]
                        )
                    )
                    player_money.append(
                        float(
                            df.loc[
                                df["Account Name"] == player_name, "Money In Account"
                            ].values[0]
                        )
                    )

            # Get player details from latest data
            investopedia_link = latest_df.loc[
                latest_df["Account Name"] == player_name, "Investopedia Link"
            ].values[0]
            player_stocks_data = latest_df.loc[
                latest_df["Account Name"] == player_name, "Stocks Invested In"
            ].iloc[0]

            # Process stock data
            player_stocks = [
                [
                    stock[0],
                    float(stock[1].replace("$", "").replace(",", "")),
                    float(stock[2].replace("%", "")),
                ]
                for stock in player_stocks_data
            ]

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
                sp500_prices=sp500_prices,
                zip=zip,
            )

            with open(f"players/{player_name}.html", "w") as f:
                f.write(rendered)


if __name__ == "__main__":
    with app.app_context():
        ### This whole section makes the chart shown at the top of the page!
        print(make_index_page())
