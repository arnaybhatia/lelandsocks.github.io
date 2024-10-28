while true
do
	cd /home/supersketchy/git/lelandstocks.github.io
	pixi run all
	git add -A .
	git commit -m "leaderboard update"
	git push origin
	sleep 90
done
