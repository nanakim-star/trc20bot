import requests
import sys

def send_telegram_alert(bot_token, chat_id, message):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(api_url, data=payload, timeout=15)
        print(f"Telegram API Response: Status Code={response.status_code}, Body={response.text}")
        sys.stdout.flush()
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"!!! Exception occurred while sending Telegram alert: {type(e).__name__} - {e}")
        sys.stdout.flush()

def send_server_alert(url, api_key, data):
    if not url: return
    headers = {'Content-Type': 'application/json'}
    if api_key: headers['x-api-key'] = api_key
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        print(f"Server API Response: Status Code={response.status_code}, Body={response.text}")
        sys.stdout.flush()
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"!!! Exception occurred while sending server alert: {type(e).__name__} - {e}")
        sys.stdout.flush()
