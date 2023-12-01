import json
import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ChatClone.settings")
django.setup()
import websocket
from core.models import User
from rest_framework.authtoken.models import Token

user_ids = User.objects.only("id").values_list("id", flat=True)
socket_type = input("channels [general, private, chats/<id>]: ")
user_id = input(f"user id [{','.join(map(str,user_ids))}]: ")
user = User.objects.get(id=int(user_id))
token, _ = Token.objects.get_or_create(user=user)
websocket_url = f"ws://localhost:8001/ws/{token.key}/{socket_type}/"


def on_message(ws, message):
    try:
        data = json.loads(message)
        print(data)
        # if "payload" in data:
        #     if int(data['payload']['sender']['id']) != int(sys.argv[1]):
        #         print(sys.argv[1], data["payload"])
    except:
        data = message
        print(data)


# Create a WebSocket connection
ws = websocket.WebSocketApp(websocket_url, on_message=on_message)

# Start the WebSocket connection
ws.run_forever()
