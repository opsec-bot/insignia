# oauth_server.py


import os
import time
import uuid
import csv
import requests
from flask import Flask, redirect, request, jsonify, abort, send_file
import config, db

app = Flask(__name__)
API_SECRET = os.environ.get("API_SECRET", "")
EXPORT_DIR = os.environ.get("EXPORT_DIR", "/data/exports")


def check_secret():
    if request.headers.get("X-API-KEY", "") != API_SECRET:
        abort(401, "Invalid API key")


@app.before_request
def ensure_db():
    db.init_db()


@app.route("/")
def index():
    scopes = "identify email guilds.join"
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={config.CLIENT_ID}"
        f"&redirect_uri={config.REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scopes}"
    )
    return f'<a href="{url}">Login with Discord</a>'


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.REDIRECT_URI,
            "scope": "identify email guilds.join",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_res.raise_for_status()
    tokens = token_res.json()

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    expires_at = int(time.time()) + tokens.get("expires_in", 0)

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_res.raise_for_status()
    user = user_res.json()
    user_id = int(user["id"])
    username = f"{user['username']}#{user['discriminator']}"
    email = user.get("email", "")
    ip_addr = request.remote_addr or ""

    db.upsert_user(
        user_id, username, access_token, refresh_token, expires_at, email, ip_addr
    )

    return f"✅ {username}, authentication complete. You may close this tab."


@app.route("/api/guilds", methods=["GET"])
def api_get_guilds():
    check_secret()
    return jsonify(db.get_guilds())


@app.route("/api/guilds", methods=["POST"])
def api_add_guild():
    check_secret()
    data = request.get_json() or {}
    try:
        gid = int(data["guild_id"])
        rid = int(data["verified_role_id"])
    except (KeyError, ValueError):
        abort(400, "Must provide numeric guild_id and verified_role_id")
    db.add_guild(gid, rid)
    return ("", 204)


@app.route("/api/check_guild/<int:gid>", methods=["GET"])
def api_check_guild(gid):
    check_secret()
    me = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/users/@me",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    me.raise_for_status()
    bot_id = me.json()["id"]

    check = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/guilds/{gid}/members/{bot_id}",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    if check.status_code in (403, 404):
        invite = (
            f"https://discord.com/oauth2/authorize"
            f"?client_id={config.CLIENT_ID}"
            f"&scope=bot"
            f"&permissions=8"
            f"&guild_id={gid}"
            f"&disable_guild_select=true"
        )
        return jsonify({"in_guild": False, "invite_link": invite}), 200
    check.raise_for_status()
    return jsonify({"in_guild": True}), 200


@app.route("/api/check_role/<int:gid>/<int:rid>", methods=["GET"])
def api_check_role(gid, rid):
    check_secret()
    # fetch roles
    roles = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/guilds/{gid}/roles",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    ).json()
    # bot member
    me = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/users/@me",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    me.raise_for_status()
    bot_id = me.json()["id"]
    member = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/guilds/{gid}/members/{bot_id}",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    member.raise_for_status()
    member = member.json()

    target = next((r for r in roles if r["id"] == str(rid)), None)
    if not target:
        abort(404, "Role not found")
    bot_positions = [r["position"] for r in roles if r["id"] in member.get("roles", [])]
    highest = max(bot_positions, default=0)
    can_assign = target["position"] < highest
    return (
        jsonify(
            {
                "can_assign": can_assign,
                "role_pos": target["position"],
                "bot_pos": highest,
            }
        ),
        200,
    )


@app.route("/api/send_verify_prompt", methods=["POST"])
def api_send_verify_prompt():
    check_secret()
    data = request.get_json() or {}
    try:
        gid = int(data["guild_id"])
        channel_id = str(data["channel_id"])
    except:
        abort(400, "Must provide guild_id and channel_id")

    me = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/users/@me",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    me.raise_for_status()
    bot_id = me.json()["id"]

    check = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/guilds/{gid}/members/{bot_id}",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    if check.status_code in (403, 404):
        invite = (
            f"https://discord.com/oauth2/authorize"
            f"?client_id={config.CLIENT_ID}"
            f"&scope=bot"
            f"&permissions=8"
            f"&guild_id={gid}"
            f"&disable_guild_select=true"
        )
        return jsonify({"error": "bot_not_in_guild", "invite_link": invite}), 403
    check.raise_for_status()

    resp = requests.get(
        f"https://discord.com/api/{config.API_VERSION}/guilds/{gid}",
        headers={"Authorization": f"Bot {config.BOT_TOKEN}"},
    )
    guild_name = resp.json().get("name", "this server") if resp.ok else "this server"

    auth_link = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={config.CLIENT_ID}"
        f"&redirect_uri={config.REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20email%20guilds.join"
    )
    embed = {
        "title": f"🔐 Verify Yourself for {guild_name}",
        "description": "Click **Verify** to authenticate and receive your Verified role.",
        "color": 0x5865F2,
    }
    button = {
        "type": 1,
        "components": [{"type": 2, "style": 5, "label": "✅ Verify", "url": auth_link}],
    }
    payload = {"embeds": [embed], "components": [button]}

    r = requests.post(
        f"https://discord.com/api/{config.API_VERSION}/channels/{channel_id}/messages",
        headers={
            "Authorization": f"Bot {config.BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if not r.ok:
        abort(r.status_code, r.text)
    return ("", 204)


@app.route("/api/drag_users", methods=["POST"])
def api_drag_users():
    check_secret()
    data = request.get_json() or {}
    try:
        gid = int(data["guild_id"])
    except:
        abort(400, "Must provide numeric guild_id")
    results = []
    users = db.get_users()
    now = int(time.time())
    for u in users:
        if u["expires_at"] <= now:
            # refresh logic...
            pass  # omitted
        r = requests.put(
            f"https://discord.com/api/{config.API_VERSION}/guilds/{gid}/members/{u['id']}",
            headers={
                "Authorization": f"Bot {config.BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"access_token": u["access_token"]},
        )
        results.append({"user_id": u["id"], "status": r.status_code})
    return jsonify(results)


@app.route("/api/export_users", methods=["POST"])
def api_export_users():
    check_secret()
    token = uuid.uuid4().hex
    filename = f"{token}.csv"
    path = os.path.join(EXPORT_DIR, filename)

    # write CSV
    users = db.get_users()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "username", "email", "ip", "expires_at"])
        for u in users:
            writer.writerow(
                [
                    u["id"],
                    u["username"],
                    u.get("email", ""),
                    u.get("ip", ""),
                    u["expires_at"],
                ]
            )

    # build one-time download URL
    download_url = request.host_url.rstrip("/") + f"/download/{filename}"
    return jsonify({"download_url": download_url}), 200


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    # serve then delete
    path = os.path.join(EXPORT_DIR, filename)
    if not os.path.isfile(path):
        abort(404)
    # stream file
    response = send_file(path, as_attachment=True, download_name="insignia_users.csv")
    # remove after sending
    try:
        os.remove(path)
    except:
        pass
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
