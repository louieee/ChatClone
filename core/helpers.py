import asyncio
import json
import logging
from collections import OrderedDict
from typing import List

import websocket
import websockets
from decouple import config
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    """
    This helps pagination more flexible allowing page sizes to be determined by the frontend
    """
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    (
                        "next",
                        self.page.next_page_number() if self.page.has_next() else None,
                    ),
                    (
                        "previous",
                        self.page.previous_page_number()
                        if self.page.has_previous()
                        else None,
                    ),
                    ("page", self.page.number),
                    ("results", data),
                ]
            )
        )


async def websocket_client(url, payload):
    async with websockets.connect(url) as websocket:
        await websocket.send(payload)
        await websocket.recv()


def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


def send_ws_to_chat(user, chat_id: int, event: str, data: dict):
    """
        Utility used to send messages to the websocket ( a chat route)
    :param user: User Instance
    :param chat_id:
    :param event:
    :param data:
    :return:
    """
    try:
        payload = dict(event=event, data=data)
        if not user:
            return
        payload["sender"] = user.id
        token, created = Token.objects.get_or_create(user=user)
        url = f"ws://{config('WEBSOCKET_URL', 'localhost')}:8001/ws/{token.key}/chats/{chat_id}/"
        loop = get_or_create_eventloop()
        loop.run_until_complete(websocket_client(url, json.dumps(payload)))
    except Exception as e:
        logging.critical(e, exc_info=True)


def send_ws_to_general(user, event: str, data: dict):
    """
           Utility used to send messages to the websocket ( a general route)
       :param user: User Instance
       :param event:
       :param data:
       :return:
       """
    try:
        payload = dict(event=event, data=data)
        if not user:
            return
        payload["sender"] = user.id
        token, created = Token.objects.get_or_create(user=user)
        url = f"ws://{config('WEBSOCKET_URL', 'localhost')}:8001/ws/{token.key}/general/"
        loop = get_or_create_eventloop()
        loop.run_until_complete(send_data(url, payload))

    except Exception as e:
        logging.critical(e, exc_info=True)

def send_ws_to_private(user, event: str, data: dict):
    """
           Utility used to send messages to the websocket ( a private route)
       :param user: User Instance
       :param event:
       :param data:
       :return:
       """
    try:
        payload = dict(event=event, data=data)
        if not user:
            return
        payload["sender"] = user.id
        token, created = Token.objects.get_or_create(user=user)
        url = f"ws://{config('WEBSOCKET_URL', 'localhost')}:8001/ws/{token.key}/private/"
        loop = get_or_create_eventloop()
        loop.run_until_complete(websocket_client(url, json.dumps(payload)))
    except Exception as e:
        logging.critical(e, exc_info=True)


async def send_data(url, data:dict):
    async with websockets.connect(url) as websocket:
        await websocket.send(json.dumps(data))

# Run the event loop to send data
