import discord
import os
import pandas as pd
from dotenv import load_dotenv
import json
from discord.ext import tasks
import datetime
from pytz import timezone

load_dotenv()

# Load the JSON file
json_file_path = "./backend/leaderboards/leaderboard-latest.json"
with open(json_file_path, "r") as file:
    data = json.load(file)

# Convert the JSON data to a DataFrame
df = pd.DataFrame.from_dict(data, orient="index")
df.reset_index(inplace=True)
df.columns = [
    "Account Name",
    "Money In Account",
    "Investopedia Link",
    "Stocks Invested In",
]


# Top ranked person's information function
def get_top_ranked_person_info(df):
    # Ensure the "Money In Account" column is of numeric type
    df["Money In Account"] = pd.to_numeric(df["Money In Account"], errors="coerce")

    # Sort the DataFrame by the "Money In Account" column in descending order
    df = df.sort_values(by=["Money In Account"], ascending=False)

    # Extract the top-ranked person's information
    top_ranked_person = df.iloc[0]
    top_ranked_name = top_ranked_person["Account Name"]
    top_ranked_money = top_ranked_person["Money In Account"]
    top_ranked_stocks = top_ranked_person["Stocks Invested In"]

    # Format the holdings nicely
    formatted_holdings = "\n".join(
        [f"{stock[0]}: {stock[1]} ({stock[2]})" for stock in top_ranked_stocks]
    )

    return top_ranked_name, top_ranked_money, formatted_holdings


# Get the top ranked person's information
top_ranked_name, top_ranked_money, top_ranked_stocks = get_top_ranked_person_info(df)

print(f"Top ranked person: {top_ranked_name}")
print(f"Money in account: {top_ranked_money}")
print(f"Stocks invested in: {top_ranked_stocks}")


# Run discord bot
class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        self.send_leaderboard.start()

    @tasks.loop(minutes=5)
    async def send_leaderboard(self):
        now = datetime.datetime.now(timezone("US/Eastern"))
        if now.weekday() < 5:  # Monday-Friday are 0-4
            start_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
            end_time = now.replace(hour=16, minute=15, second=0, microsecond=0)
            if start_time <= now <= end_time:
                # Load the JSON file
                json_file_path = "./backend/leaderboards/leaderboard-latest.json"
                with open(json_file_path, "r") as file:
                    data = json.load(file)
                # Convert the JSON data to a DataFrame
                df = pd.DataFrame.from_dict(data, orient="index")
                df.reset_index(inplace=True)
                df.columns = [
                    "Account Name",
                    "Money In Account",
                    "Investopedia Link",
                    "Stocks Invested In",
                ]
                # Get the top ranked person's information
                top_ranked_name, top_ranked_money, top_ranked_stocks = (
                    get_top_ranked_person_info(df)
                )
                # Send the Discord message
                channel = self.get_channel(int(os.environ.get("DISCORD_CHANNEL_ID")))
                embed = discord.Embed(
                    colour=discord.Colour.dark_red(),
                    title="Leaderboard Update!",
                    description=(
                        f"**Top Ranked Person:** {top_ranked_name}\n\n"
                        f"**Current Money:** {top_ranked_money}\n\n"
                        f"**Current Holdings:**\n{top_ranked_stocks}"
                    ),
                    timestamp=discord.utils.utcnow(),
                )
                await channel.send(embed=embed)


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
client.run(DISCORD_BOT_TOKEN)
