export $(xargs < /config/environment.sh)
python scraper.py
tail -f /dev/null