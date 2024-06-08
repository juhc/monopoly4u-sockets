import socketio
import json
from httpx import AsyncClient

from redis_settings import redis_instance
from config import settings


sio_server = socketio.AsyncServer(
    async_mode="asgi", async_handlers=True, cors_allowed_origins=[]
)

sio_app = socketio.ASGIApp(socketio_server=sio_server, socketio_path="socketio")

GAME_API_URL = settings.api.game_api_url
AUTH_API_URL = settings.api.auth_api_url


@sio_server.event
async def connect(sid, environ, auth):
    print("CONNECT")
    if auth["token"]:
        print(auth)
        async with AsyncClient() as client:
            response = await client.get(
                f"{AUTH_API_URL}/api/players/profile",
                headers={"authorization": auth["token"]},
            )
            if response.status_code == 200:
                profile = response.json()
                user_id = profile.get("id")
                username = profile.get("nickname")
                await redis_instance.set(f"session:{sid}:user_id", user_id)
                await redis_instance.set(f"session:{sid}:username", username)


@sio_server.event
async def disconnect(sid):
    await disconnect_game(sid)
    await redis_instance.delete(f"session:{sid}:username")
    await redis_instance.delete(f"session:{sid}:user_id")
    await sio_server.disconnect(sid)


@sio_server.event
async def create_game(sid, players_count):
    username = await redis_instance.get(f"session:{sid}:username")
    user_id = await redis_instance.get(f"session:{sid}:user_id")
    async with AsyncClient() as client:
        response = await client.post(
            f"{GAME_API_URL}/rooms/",
            data=json.dumps(
                {
                    "user_id": user_id,
                    "players_count": players_count,
                    "username": username,
                }
            ),
        )
        if response.status_code == 200:
            room_id = response.json().get("room_id")
            await sio_server.enter_room(sid, room=str(room_id))
            await sio_server.emit("add_game", response.json())


@sio_server.event
async def get_games_list(sid):
    async with AsyncClient() as client:
        response = await client.get(f"{GAME_API_URL}/rooms/")
        if response.status_code == 200:
            await sio_server.emit("games", data=response.json())


@sio_server.event
async def join_game(sid, room_id):
    async with AsyncClient() as client:
        user_id = await redis_instance.get(f"session:{sid}:user_id")
        username = await redis_instance.get(f"session:{sid}:username")
        response = await client.post(
            f"{GAME_API_URL}/rooms/{room_id}",
            data=json.dumps({"user_id": user_id, "username": username}),
        )
        if response.status_code == 200:
            await sio_server.enter_room(sid, str(room_id))
            await sio_server.emit("add_player", data=response.json())

        response = await client.get(f"{GAME_API_URL}/rooms/{room_id}")
        if response.status_code == 200:
            room_info = response.json()

            if len(room_info.get("users")) == room_info.get("players_total"):
                created_game_response = await client.post(
                    f"{GAME_API_URL}/rooms/{room_id}/game"
                )
                if created_game_response.status_code == 200:
                    await sio_server.emit(
                        "room_teleport", data=room_id, room=str(room_id)
                    )


@sio_server.event
async def disconnect_game(sid):
    async with AsyncClient() as client:
        user_id = await redis_instance.get(f"session:{sid}:user_id")
        response_delete_player = await client.delete(
            f"{GAME_API_URL}/rooms/players/{user_id}",
        )
        if response_delete_player.status_code == 200:
            if response_delete_player.json():
                room_id = response_delete_player.json()["room_id"]
                room = await client.get(f"{GAME_API_URL}/rooms/{room_id}")
                if room.status_code == 200:
                    if room.json()["users"] == []:
                        response_delete_room = await client.delete(
                            f"{GAME_API_URL}/rooms/{room_id}"
                        )
                        print("CLOSE", room_id)
                        await sio_server.close_room(room_id)
                        await sio_server.emit(
                            "delete_game", data=response_delete_room.json()
                        )
                    else:
                        await sio_server.leave_room(sid, room_id)
                        await sio_server.emit(
                            "delete_player", data=response_delete_player.json()
                        )


@sio_server.event
async def get_game_info(sid, room_id):
    async with AsyncClient() as client:
        response = await client.get(f"{GAME_API_URL}/rooms/{room_id}/game")

        if response.status_code == 200:
            await sio_server.emit("get_game_info", data=response.json(), room=sid)


@sio_server.event
async def connect_to_game(sid, room_id):
    username = await redis_instance.get(f"session:{sid}:username")
    async with AsyncClient() as client:
        response = await client.patch(
            f"{GAME_API_URL}/rooms/{room_id}/game",
            data=json.dumps({"username": username}),
        )

        if response.status_code == 200:
            await sio_server.emit(
                "player_added", data=response.json(), room=str(room_id)
            )
            await sio_server.emit("get_game_info", data=response.json(), room=sid)

            response_room = await client.get(f"{GAME_API_URL}/rooms/{room_id}")
            response_game = await client.get(f"{GAME_API_URL}/rooms/{room_id}/game")

            if response_room.status_code == 200 and response_game.status_code == 200:
                if len(response_room.json()["users"]) == len(
                    response_game.json()["players"]
                ):
                    response = await client.post(
                        f"{GAME_API_URL}/rooms/{room_id}/game/start"
                    )
                    if response.status_code == 200:
                        await sio_server.emit(
                            "start_game", data=response.json(), room=str(room_id)
                        )


@sio_server.event
async def make_move(sid, room_id):
    username = await redis_instance.get(f"session:{sid}:username")
    async with AsyncClient() as client:
        response = await client.post(
            f"{GAME_API_URL}/rooms/{room_id}/game/make-move",
            data=json.dumps({"username": username}),
        )

        if response.status_code == 200:
            await sio_server.emit(
                "update_game", data=response.json(), room=str(room_id)
            )


@sio_server.event
async def roll_dice(sid, room_id):
    username = await redis_instance.get(f"session:{sid}:username")
    async with AsyncClient() as client:
        response = await client.post(
            f"{GAME_API_URL}/rooms/{room_id}/game/roll-dice",
            data=json.dumps({"username": username}),
        )

        if response.status_code == 200:
            await sio_server.emit("dice_info", data=response.json(), room=str(room_id))
            await make_move(sid, room_id)
