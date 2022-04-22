import requests
import os
import csv
from dotenv import load_dotenv
from flask import Flask, request, jsonify

app = Flask(__name__)

load_dotenv()

YOUTUBE_API_URL = os.getenv("YOUTUBE_API_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

@app.route('/', methods=['GET'])
def index():
    return "Hello, World!"

@app.route('/channelId', methods=['POST'])
def channel_id_vid():
    vid = request.json["vid"]
    parts = "%2C".join(["snippet","contentDetails","statistics","status", "topicDetails"])
    response = requests.get(f"{YOUTUBE_API_URL}/videos?part={parts}&id={vid}&key={GOOGLE_API_KEY}")
    data = response.json()["items"][0]
    return data["snippet"]["channelId"]

@app.route("/channel", methods=['POST'])
def channel():
    channelIds = request.json["channelId"]
    channels = []
    videos = []
    for cid in channelIds:
        channel, vids = channel_metadata(cid)
        channels.append(channel)
        videos += process_videos(vids)
    write_dict_csv("./data/channels.csv", channels)
    write_dict_csv("./data/videos.csv", videos)
    return f"Successfully processed {len(channels)} channels and {len(videos)} videos"

def write_dict_csv(path, data):
    with open(path, "a") as f:
        dict_writer = csv.DictWriter(f, fieldnames=data[0].keys())
        #dict_writer.writeheader()
        dict_writer.writerows(data)

def process_videos(vids):
    result = []
    for vid in vids:
        metadata = video_metadata(vid)
        result.append(metadata)
    return result

def video_metadata(vid):
    parts = "%2C".join(["snippet","contentDetails","statistics","status", "topicDetails"])
    response = requests.get(f"{YOUTUBE_API_URL}/videos?part={parts}&id={vid}&key={GOOGLE_API_KEY}")
    data = response.json()["items"][0]
    print(data)
    filtered_result = {
        "vid": vid,
        "viewCount": data["statistics"]["viewCount"] if "viewCount" in data["statistics"] else None,
        "channelId": data["snippet"]["channelId"] if "channelId" in data["snippet"] else None,
        "likeCount": data["statistics"]["likeCount"] if "likeCount" in data["statistics"] else None,
        "favoriteCount": data["statistics"]["favoriteCount"] if "favoriteCount" in data["statistics"] else None,
        "commentCount": data["statistics"]["commentCount"] if "commentCount" in data["statistics"] else None,
        "madeForKids": data["status"]["madeForKids"] if "madeForKids" in data["status"] else None,
        "duration": data["contentDetails"]["duration"] if "duration" in data["contentDetails"] else None,
        "publishedAt": data["snippet"]["publishedAt"] if "publishedAt" in data["snippet"] else None,
        "caption": data["contentDetails"]["caption"] if "caption" in data["contentDetails"] else None,
        "tags": data["snippet"]["tags"] if "tags" in data["snippet"] else None,
        "thumbnails": data["snippet"]["thumbnails"]["default"] if "thumbnails" in data["snippet"] else None,
    }
    return filtered_result

def channel_metadata(cid):
    max_results = 100
    channel_parts = "%2C".join(["snippet", "contentDetails", "statistics"])
    activity_parts = "%2C".join(["contentDetails"])
    channel_response = requests.get(f"{YOUTUBE_API_URL}/channels?part={channel_parts}&id={cid}&key={GOOGLE_API_KEY}").json()["items"][0]
    activity_response = requests.get(f"{YOUTUBE_API_URL}/activities?part={activity_parts}&channelId={cid}&maxResults={max_results}&key={GOOGLE_API_KEY}").json()
    data = list(filter(lambda item: "upload" in item["contentDetails"], activity_response["items"]))
    data = list(map(lambda item: item["contentDetails"]["upload"]["videoId"],data))
    return {
            "channel_name": channel_response["snippet"]["title"],
            "cid": cid,
            "videoIds": data,
            "videoCount": len(data),
            "totalViews": channel_response["statistics"]["viewCount"],
            "totalVideos": channel_response["statistics"]["videoCount"],
            "subscriberCount": channel_response["statistics"]["subscriberCount"],
    }, data

if(__name__ == '__main__'):
    app.run(debug=True, port=8080)