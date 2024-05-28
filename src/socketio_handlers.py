import socketio
import json
from httpx import AsyncClient

from redis_settings import redis_instance
from config import settings


sio_server = socketio.AsyncServer(
    async_mode="asgi", async_handlers=True, cors_allowed_origins=[]
)

sio_app = socketio.ASGIApp(socketio_server=sio_server, socketio_path="socketio")

GAME_API_HOST = settings.api.GAME_API_HOST
AUTH_API_HOST = settings.api.AUTH_API_HOST


@sio_server.event
async def connect(sid, environ, auth):
    if auth["token"]:
        async with AsyncClient() as client:
            print("TEST1")
            response = await client.get(
                f"http://{AUTH_API_HOST}:8080/api/players/profile",
                headers={"authorization": auth["token"]},
            )
            print("TEST2")
            print(response.json())
            if response.status_code == 200:
                profile = response.json()
                user_id = profile.get("id")
                username = profile.get("nickname")
                await redis_instance.set(f"session:{sid}:user_id", user_id)
                await redis_instance.set(f"session:{sid}:username", username)


@sio_server.event
async def disconnect(sid):
    username = await redis_instance.get(f"session:{sid}:username")
    user_id = await redis_instance.get(f"session:{sid}:user_id")
    print(f"SID {sid} - {username} - {user_id} disconnected")


@sio_server.event
async def create_game(sid, players_count):
    username = await redis_instance.get(f"session:{sid}:username")
    user_id = await redis_instance.get(f"session:{sid}:user_id")
    async with AsyncClient() as client:
        response = await client.post(
            f"http://{GAME_API_HOST}:8081/rooms/",
            data=json.dumps(
                {
                    "user_id": user_id,
                    "players_count": players_count,
                    "username": username,
                }
            ),
        )
        if response.status_code == 200:
            await sio_server.emit("add_game", response.json())


@sio_server.event
async def get_games_list(sid):
    async with AsyncClient() as client:
        response = await client.get(f"http://{GAME_API_HOST}:8081/rooms/")
        if response.status_code == 200:
            await sio_server.emit("games", data=response.json())


@sio_server.event
async def join_game(sid, room_id):
    async with AsyncClient() as client:
        user_id = await redis_instance.get(f"session:{sid}:user_id")
        username = await redis_instance.get(f"session:{sid}:username")
        response = await client.post(
            f"http://{GAME_API_HOST}:8081/rooms/{room_id}",
            data=json.dumps({"user_id": user_id, "username": username}),
        )
        if response.status_code == 200:
            await sio_server.emit("add_player", data=response.json())


@sio_server.event
async def disconnect_game(sid):
    async with AsyncClient() as client:
        user_id = await redis_instance.get(f"session:{sid}:user_id")
        response_delete_player = await client.delete(
            f"http://{GAME_API_HOST}:8081/rooms/players/{user_id}",
        )
        if response_delete_player.status_code == 200:
            if response_delete_player.json():
                room_id = response_delete_player.json()["room_id"]
                room = await client.get(f"http://{GAME_API_HOST}:8081/rooms/{room_id}")
                if room.status_code == 200:
                    print("ROOM INFO")
                    print(room.json())
                    if room.json()["users"] == []:
                        response_delete_room = await client.delete(
                            f"http://{GAME_API_HOST}:8081/rooms/{room_id}"
                        )
                        await sio_server.emit(
                            "delete_game", data=response_delete_room.json()
                        )
                    else:
                        await sio_server.emit(
                            "delete_player", data=response_delete_player.json()
                        )
