while true
do
	git add -A . &&	git commit -m 'leaderboard update' && git push origin && rm -rf /tmp/.org.chromium.Chromium.*
done
