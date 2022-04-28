export $(xargs < /config/environment.sh)
python3 scraper.py
tail -f /dev/null
