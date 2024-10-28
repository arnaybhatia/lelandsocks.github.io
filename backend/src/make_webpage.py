from flask import render_template
import pandas as pd
import flask
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
        df = df[["Ranking", "Account Name", "Money In Account", "Investopedia Link"]]

        # Render the html template as shown here: https://stackoverflow.com/a/56296451
        rendered = render_template(
            "index.html",
            column_names=df.columns.values,
            row_data=list(df.values.tolist()),
            link_column="Investopedia Link",
            zip=zip,
        )
        print(rendered)
