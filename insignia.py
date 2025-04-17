# insignia.py

import os, sys, requests
from colorama import Fore, Style, init
import config

init(autoreset=True)

MENU_COLOR = Fore.CYAN + Style.BRIGHT
PROMPT_COLOR = Fore.YELLOW + Style.BRIGHT
ERROR_COLOR = Fore.RED + Style.BRIGHT
OK_COLOR = Fore.GREEN + Style.BRIGHT
INFO_COLOR = Fore.MAGENTA + Style.BRIGHT

API_URL = os.environ.get("API_URL", "http://localhost:5000/api")
API_SECRET = os.environ.get("API_SECRET", "")
HEADERS = {"X-API-KEY": API_SECRET}


def load_guilds():
    try:
        r = requests.get(f"{API_URL}/guilds", headers=HEADERS, timeout=3)
        r.raise_for_status()
        return r.json()
    except:
        print(
            ERROR_COLOR
            + "⚠️ Cannot reach backend. Make sure the Docker container is running."
        )
        sys.exit(1)

def export_users_flow():
    print(MENU_COLOR + "\n--- Export Users to CSV ---\n")
    try:
        r = requests.post(f"{API_URL}/export_users", headers=HEADERS, timeout=5)
        r.raise_for_status()
    except requests.RequestException:
        print(ERROR_COLOR + "⚠️ Cannot reach backend. Make sure the Docker container is running.")
        return
    data = r.json()
    url = data.get("download_url")
    if url:
        print(OK_COLOR + "✅ Export ready!")
        print(OK_COLOR + "One-time download link:")
        print(url)
        print(INFO_COLOR + "ℹ️ After the file is downloaded, the link will expire.")
    else:
        print(ERROR_COLOR + "❌ Unexpected response:", data)


def add_guild_flow():
    print(MENU_COLOR + "\n--- Add a New Guild ---\n")
    try:
        gid = int(input(PROMPT_COLOR + "▶ Guild ID: ").strip())
    except:
        print(ERROR_COLOR + "Invalid Guild ID.")
        return

    # check membership
    try:
        r = requests.get(f"{API_URL}/check_guild/{gid}", headers=HEADERS, timeout=3)
        r.raise_for_status()
    except:
        print(ERROR_COLOR + "⚠️ Cannot reach backend.")
        return

    d = r.json()
    if not d["in_guild"]:
        print(ERROR_COLOR + "⚠️ Bot is not in that guild.")
        print(ERROR_COLOR + d["invite_link"])
        print(
            ERROR_COLOR + "→ Make sure the bot’s role is ABOVE your verification role."
        )
        return

    try:
        rid = int(input(PROMPT_COLOR + "▶ Verified Role ID: ").strip())
    except:
        print(ERROR_COLOR + "Invalid Role ID.")
        return

    # check role position
    try:
        r2 = requests.get(
            f"{API_URL}/check_role/{gid}/{rid}", headers=HEADERS, timeout=3
        )
        r2.raise_for_status()
        c = r2.json()
    except:
        print(ERROR_COLOR + "⚠️ Cannot check role positions.")
        return

    if not c["can_assign"]:
        print(
            ERROR_COLOR
            + f"❌ Your bot's highest role position ({c['bot_pos']}) is not above the verify role ({c['role_pos']})."
        )
        print(
            ERROR_COLOR
            + "→ Move the bot’s role above the verification role in Discord settings."
        )
        return

    # save guild
    resp = requests.post(
        f"{API_URL}/guilds",
        headers=HEADERS,
        json={"guild_id": gid, "verified_role_id": rid},
    )
    if resp.status_code == 204:
        print(OK_COLOR + f"✅ Saved guild {gid} with role {rid}")
    else:
        print(ERROR_COLOR + f"❌ Failed ({resp.status_code}): {resp.text}")


def drag_users_flow():
    guilds = load_guilds()
    if not guilds:
        print(ERROR_COLOR + "No guilds configured.")
        return

    print(INFO_COLOR + "\nSelect a guild to drag users into:")
    for i, g in enumerate(guilds, 1):
        print(PROMPT_COLOR + f"[{i}] {g['guild_id']}")
    try:
        gid = guilds[int(input(PROMPT_COLOR + "Choice: ").strip()) - 1]["guild_id"]
    except:
        print(ERROR_COLOR + "Invalid choice.")
        return

    r = requests.post(f"{API_URL}/drag_users", headers=HEADERS, json={"guild_id": gid})
    if not r.ok:
        print(ERROR_COLOR + f"❌ Drag failed ({r.status_code}): {r.text}")
        return

    for res in r.json():
        mark = (
            OK_COLOR + "✅" if res["status"] in (200, 201, 204) else ERROR_COLOR + "❌"
        )
        print(f"{mark} User {res['user_id']} → {res['status']}")


def send_verify_prompt_flow():
    guilds = load_guilds()
    if not guilds:
        print(ERROR_COLOR + "No guilds configured.")
        return

    print(INFO_COLOR + "\nSelect a guild to send a verify prompt in:")
    for i, g in enumerate(guilds, 1):
        print(PROMPT_COLOR + f"[{i}] {g['guild_id']}")
    try:
        gid = guilds[int(input(PROMPT_COLOR + "Choice: ").strip()) - 1]["guild_id"]
    except:
        print(ERROR_COLOR + "Invalid choice.")
        return

    channel_id = input(PROMPT_COLOR + "▶ Channel ID: ").strip()
    r = requests.post(
        f"{API_URL}/send_verify_prompt",
        headers=HEADERS,
        json={"guild_id": gid, "channel_id": channel_id},
    )
    if r.status_code in (200, 201, 204):
        print(OK_COLOR + "✅ Verification prompt sent!")
    elif r.status_code == 403 and r.json().get("error") == "bot_not_in_guild":
        err = r.json()
        print(ERROR_COLOR + "⚠️ Bot is not in that guild.")
        print(ERROR_COLOR + err["invite_link"])
        print(
            ERROR_COLOR + "→ Make sure the bot’s role is ABOVE your verification role."
        )
    else:
        print(ERROR_COLOR + f"❌ Failed ({r.status_code}): {r.text}")


def main():
    while True:
        guilds = load_guilds()
        print(MENU_COLOR + "\n=== Insignia CLI ===")
        print(PROMPT_COLOR + "[1] " + Style.NORMAL + "Add a new guild")
        if guilds:
            print(PROMPT_COLOR + "[2] " + Style.NORMAL + "Drag users")
            print(PROMPT_COLOR + "[3] " + Style.NORMAL + "Send verify prompt")
            print(PROMPT_COLOR + "[4] " + Style.NORMAL + "Export users CSV")
            print(PROMPT_COLOR + "[5] " + Style.NORMAL + "Exit")
        else:
            print(PROMPT_COLOR + "[2] " + Style.NORMAL + "Export users CSV")
            print(PROMPT_COLOR + "[3] " + Style.NORMAL + "Exit")

        choice = input(PROMPT_COLOR + "Select an option: ").strip()
        if choice == "1":
            add_guild_flow()
        elif choice == "2":
            if guilds:
                drag_users_flow()
            else:
                export_users_flow()
        elif choice == "3":
            if guilds:
                send_verify_prompt_flow()
            else:
                print(INFO_COLOR + "Goodbye.")
                break
        elif choice == "4" and guilds:
            export_users_flow()
        elif choice == "5" and guilds:
            print(INFO_COLOR + "Goodbye.")
            break
        else:
            print(ERROR_COLOR + "Invalid choice.")


if __name__ == "__main__":
    main()
