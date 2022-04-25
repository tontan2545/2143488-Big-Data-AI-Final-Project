import requests, time, os, gspread, schedule, json
from dotenv import load_dotenv

# List of simple to collect features
snippet_features = ["title",
                    "publishedAt",
                    "channelId",
                    "channelTitle",
                    "categoryId"]

# Any characters to exclude, generally these are things that become problematic in CSV files
unsafe_characters = ['\n', '"']

# Used to identify columns, currently hardcoded order
header = ["video_id"] + snippet_features + ["trending_date", "tags", "view_count", "likes", "dislikes",
                                            "comment_count", "thumbnail_link", "comments_disabled",
                                            "ratings_disabled", "description"]

# load variable from env file
load_dotenv()
YOUTUBE_API_URL = os.getenv("YOUTUBE_API_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

country_codes = ["TH"]

def create_service_account():
    # make file name service_account.json in .config/gspread
    service_account = {
        "type": os.getenv("SERVICE_ACCOUNT_TYPE"),
        "project_id": os.getenv("SERVICE_ACCOUNT_PROJECT_ID"),
        "private_key_id": os.getenv("SERVICE_ACCOUNT_PRIVATE_KEY_ID"),
        "private_key": os.getenv("SERVICE_ACCOUNT_PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("SERVICE_ACCOUNT_CLIENT_EMAIL"),
        "client_id": os.getenv("SERVICE_ACCOUNT_CLIENT_ID"),
        "auth_uri": os.getenv("SERVICE_ACCOUNT_AUTH_URI"),
        "token_uri": os.getenv("SERVICE_ACCOUNT_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("SERVICE_ACCOUNT_CLIENT_X509_CERT_URL")
    }

    if(not os.path.exists(".config")):
        os.mkdir(".config")
    if(not os.path.exists(".config/gspread")):
        os.mkdir(".config/gspread")

    # write service account to .config/gspread
    with open(".config/gspread/service_account.json", "w") as f:
        f.write(json.dumps(service_account, indent=4))


def prepare_feature(feature):
    # Removes any character from the unsafe characters list and surrounds the whole item in quotes
    for ch in unsafe_characters:
        feature = str(feature).replace(ch, "")
    return f'"{feature}"'


def api_request(page_token, country_code):
    # Builds the URL and requests the JSON from it
    request_url = f"{YOUTUBE_API_URL}/videos?part=id,statistics,snippet{page_token}chart=mostPopular&regionCode={country_code}&maxResults=50&key={GOOGLE_API_KEY}"
    request = requests.get(request_url)
    if request.status_code == 429:
        print("Temp-Banned due to excess requests, please wait and continue later")
        time.sleep(3000)
        api_request(page_token, country_code)
    return request.json()


def get_tags(tags_list):
    # Takes a list of tags, prepares each tag and joins them into a string by the pipe character
    return prepare_feature("|".join(tags_list))


def get_videos(items):
    lines = []
    for video in items:
        comments_disabled = False
        ratings_disabled = False

        # We can assume something is wrong with the video if it has no statistics, often this means it has been deleted
        # so we can just skip it
        if "statistics" not in video:
            continue

        # A full explanation of all of these features can be found on the GitHub page for this project
        video_id = prepare_feature(video['id'])

        # Snippet and statistics are sub-dicts of video, containing the most useful info
        snippet = video['snippet']
        statistics = video['statistics']

        # This list contains all of the features in snippet that are 1 deep and require no special processing
        features = [prepare_feature(snippet.get(feature, "")) for feature in snippet_features]

        # The following are special case features which require unique processing, or are not within the snippet dict
        description = snippet.get("description", "")
        thumbnail_link = snippet.get("thumbnails", dict()).get("default", dict()).get("url", "")
        trending_date = time.strftime("%y.%d.%m")
        tags = get_tags(snippet.get("tags", ["[none]"]))
        view_count = statistics.get("viewCount", 0)

        # This may be unclear, essentially the way the API works is that if a video has comments or ratings disabled
        # then it has no feature for it, thus if they don't exist in the statistics dict we know they are disabled
        if 'likeCount' in statistics and 'dislikeCount' in statistics:
            likes = statistics['likeCount']
            dislikes = statistics['dislikeCount']
        else:
            ratings_disabled = True
            likes = 0
            dislikes = 0

        if 'commentCount' in statistics:
            comment_count = statistics['commentCount']
        else:
            comments_disabled = True
            comment_count = 0

        # Compiles all of the various bits of info into one consistently formatted line
        line = [video_id] + features + [prepare_feature(x) for x in [trending_date, tags, view_count, likes, dislikes,
                                                                       comment_count, thumbnail_link, comments_disabled,
                                                                       ratings_disabled, description]]
        lines.append(",".join(line))
    return lines


def get_pages(country_code, next_page_token="&"):
    country_data = []

    print(f"Fetching trending {country_code} data for {time.strftime('%Y-%m-%d')}")
    # Because the API uses page tokens (which are literally just the same function of numbers everywhere) it is much
    # more inconvenient to iterate over pages, but that is what is done here.
    while next_page_token is not None:
        # A page of data i.e. a list of videos and all needed data
        video_data_page = api_request(next_page_token, country_code)

        # Get the next page token and build a string which can be injected into the request with it, unless it's None,
        # then let the whole thing be None so that the loop ends after this cycle
        next_page_token = video_data_page.get("nextPageToken", None)
        next_page_token = f"&pageToken={next_page_token}&" if next_page_token is not None else next_page_token

        # Get all of the items as a list and let get_videos return the needed features
        items = video_data_page.get('items', [])
        country_data += get_videos(items)
    return country_data


def write_to_gg_sheet(country_code, country_data):

    print(f"{len(country_data)} videos found")
    print(f"Writing {country_code} data to google sheet...")

    gc = gspread.service_account(".config/gspread/service_account.json")
    sh = gc.open("Big Data Final Project (Youtube)").sheet1
    sh.append_rows([[data[1:-1] for data in datas.split(',')] for datas in country_data[1:5]])

def next_available_row(worksheet):
    str_list = list(filter(None, worksheet.col_values(1)))
    return str(len(str_list) + 1)

def get_data():
    print("============================================================")
    for country_code in country_codes:
        country_data = [",".join(header)] + get_pages(country_code)
        write_to_gg_sheet(country_code, country_data)


if __name__ == "__main__":
    create_service_account()
    schedule.every(10).seconds.do(get_data)
    print("Starting schedule")
    while True:
        print("hello")
        schedule.run_pending()
        time.sleep(1)
