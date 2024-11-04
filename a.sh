while true
do
	cd /home/supersketchy/git/lelandstocks.github.io
	pixi run all
	git add -A .
	git commit -m "leaderboard update"
	git push origin
	rm -rf /tmp/.org.chromium.Chromium.*
done
