# Leland High School's Stock Trading Leaderboard
The investopedia one was really slow to update (sometimes taking 2 weeks!). I wanted near real time leaderboard updates, making this cooler.


## How to Use?
First, using your own browser (will hopefully be fixed in a future update), download the entire leaderboard as html. For the 128 players, this was 3 pages of 50 leaderboards. Notably, you only have to do this once!

Then, fill out the .env.example file with your login credentials, and the number of leaderboards (and rename it to .env).

To get your Discord Channel ID, right click on the channel you want the bot to post in and click "Copy ID"

TO add the bot to your server:
In the OAuth2 tab, grab the Client ID.
Replace <CLIENT_ID_HERE> in the following URL and visit it in the browser to invite your bot to your new test server.
https://discordapp.com/api/oauth2/authorize?client_id=<CLIENT_ID_HERE>&permissions=8&scope=bot

Then simply run `pixi run all`

