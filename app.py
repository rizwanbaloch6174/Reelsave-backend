from flask import Flask, request, jsonify
import yt_dlp
from urllib.parse import urlparse

app = Flask(__name__)

ALLOWED_HOSTS = (
    "instagram.com",
    "facebook.com",
    "fb.watch",
    "x.com",
    "twitter.com",
)

def platform_name(url):
    host = urlparse(url).hostname or ""
    host = host.lower().replace("www.", "")

    if host.endswith("instagram.com"):
        return "instagram"
    if host.endswith("facebook.com") or host == "fb.watch":
        return "facebook"
    if host.endswith("x.com") or host.endswith("twitter.com"):
        return "x"
    return None

@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "service": "ReelSave API"
    })

@app.route("/resolve", methods=["POST", "OPTIONS"])
def resolve():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()

    platform = platform_name(url)

    if not platform:
        return jsonify({
            "error": "Please enter a valid Instagram, Facebook, or X link."
        }), 400

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "format": "best[ext=mp4]/best"
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        formats = []

        for f in info.get("formats", []):
            direct_url = f.get("url")
            if not direct_url:
                continue

            if f.get("vcodec") == "none":
                continue

            height = f.get("height")
            width = f.get("width")

            if height:
                quality = f"{height}p"
            else:
                quality = f.get("format_note") or "Source"

            formats.append({
                "label": quality,
                "quality": height,
                "width": width,
                "height": height,
                "url": direct_url,
                "ext": f.get("ext")
            })

        if not formats and info.get("url"):
            formats.append({
                "label": "Source",
                "quality": info.get("height"),
                "width": info.get("width"),
                "height": info.get("height"),
                "url": info.get("url"),
                "ext": info.get("ext")
            })

        unique = {}
        for f in formats:
            key = (f.get("quality"), f.get("width"), f.get("height"))
            unique[key] = f

        formats = list(unique.values())
        formats.sort(
            key=lambda x: x.get("quality") or 0,
            reverse=True
        )

        return jsonify({
            "platform": platform,
            "title": info.get("title") or "Video",
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "width": info.get("width"),
            "height": info.get("height"),
            "formats": formats
        })

    except Exception as e:
        return jsonify({
            "error": "Could not process this video.",
            "details": str(e)
        }), 422
