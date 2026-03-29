"""
WebSocket - Velox Framework
============================
Sistema avançado de WebSocket com:
- Gerenciador de conexões
- Rooms/canais
- Broadcast
- Eventos de conexão/desconexão
- Auto-cleanup de conexões mortas

Uso:
    from velox.websocket import WebSocketManager, ws_route

    # Criar gerenciador
    ws_manager = WebSocketManager()

    # Definir rota WebSocket
    @app.websocket('/ws/chat')
    async def chat_ws(ws):
        await ws_manager.connect(ws, room='chat')
        try:
            while True:
                msg = await ws.receive()
                if msg is None: break
                # Broadcast para todos na sala
                await ws_manager.broadcast(msg, room='chat')
        finally:
            ws_manager.disconnect(ws)
"""

import asyncio
import json
import os
import weakref
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime

# Limite máximo de mensagem WebSocket (padrão: 1MB)
WS_MAX_MESSAGE_SIZE = int(os.getenv('WS_MAX_MESSAGE_SIZE', 1024 * 1024))


# ─────────────────────────────────────────────────────────────────
# WebSocket Message
# ─────────────────────────────────────────────────────────────────

class WebSocketMessage:
    """Mensagem WebSocket estruturada"""

    def __init__(self, type: str, data: Any, sender: str = None, room: str = None):
        self.type      = type
        self.data      = data
        self.sender    = sender
        self.room      = room
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'type':      self.type,
            'data':      self.data,
            'sender':    self.sender,
            'room':      self.room,
            'timestamp': self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WebSocketMessage':
        msg = cls(
            type=data.get('type', 'message'),
            data=data.get('data'),
            sender=data.get('sender'),
            room=data.get('room'),
        )
        if 'timestamp' in data:
            msg.timestamp = datetime.fromisoformat(data['timestamp'])
        return msg

    def __repr__(self):
        return f'<WebSocketMessage type={self.type} room={self.room}>'


# ─────────────────────────────────────────────────────────────────
# WebSocket Manager
# ─────────────────────────────────────────────────────────────────

class WebSocketManager:
    """
    Gerenciador de conexões WebSocket.

    Features:
    - Conexões por sala (rooms)
    - Broadcast para sala ou todos
    - Contagem de conexões
    - Cleanup automático

    Uso:
        manager = WebSocketManager()

        # Conectar
        await manager.connect(ws, room='chat', user_id='user1')

        # Enviar para sala
        await manager.send_to_room('hello', room='chat')

        # Broadcast global
        await manager.broadcast({'msg': 'hello all'})

        # Desconectar
        manager.disconnect(ws)
    """

    def __init__(self, heartbeat_interval: int = 30):
        # Conexões ativas: ws -> info
        self._connections: Dict[Any, Dict] = {}

        # Rooms: room_name -> set of ws
        self._rooms: Dict[str, Set[Any]] = defaultdict(set)

        # Callbacks de eventos
        self._on_connect:    List[Callable] = []
        self._on_disconnect: List[Callable] = []
        self._on_message:    List[Callable] = []

        # Heartbeat para cleanup
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ── Gerenciamento de Conexões ─────────────────

    async def connect(self, ws, room: str = 'default',
                      user_id: str = None, metadata: Dict = None) -> None:
        """
        Registra uma conexão WebSocket.

        Args:
            ws: Instância do WebSocket
            room: Nome da sala (default: 'default')
            user_id: ID do usuário (opcional)
            metadata: Dados adicionais (opcional)
        """
        info = {
            'room':               room,
            'user_id':            user_id,
            'metadata':           metadata or {},
            'connected_at':       datetime.now(),
            'messages_sent':      0,
            'messages_received':  0,
        }

        self._connections[ws] = info
        self._rooms[room].add(ws)

        for cb in self._on_connect:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(ws, info)
                else:
                    cb(ws, info)
            except Exception as e:
                print(f'[WS] Erro no on_connect: {e}')

        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

    def disconnect(self, ws) -> None:
        """Remove uma conexão WebSocket."""
        if ws not in self._connections:
            return

        info = self._connections.pop(ws)
        room = info['room']

        if room in self._rooms:
            self._rooms[room].discard(ws)
            if not self._rooms[room]:
                del self._rooms[room]

        for cb in self._on_disconnect:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(ws, info))
                else:
                    cb(ws, info)
            except Exception as e:
                print(f'[WS] Erro no on_disconnect: {e}')

    # ── Envio de Mensagens ────────────────────────

    async def send(self, ws, message: Any) -> bool:
        """Envia mensagem para um cliente específico."""
        try:
            if isinstance(message, (dict, list)):
                payload = json.dumps(message, ensure_ascii=False)
                if len(payload.encode()) > WS_MAX_MESSAGE_SIZE:
                    raise ValueError(f'Mensagem excede limite de {WS_MAX_MESSAGE_SIZE} bytes')
                await ws.send(payload)
            elif isinstance(message, WebSocketMessage):
                await ws.send_json(message.to_dict())
            else:
                payload = str(message)
                if len(payload.encode()) > WS_MAX_MESSAGE_SIZE:
                    raise ValueError(f'Mensagem excede limite de {WS_MAX_MESSAGE_SIZE} bytes')
                await ws.send(payload)

            if ws in self._connections:
                self._connections[ws]['messages_sent'] += 1
            return True
        except Exception as e:
            print(f'[WS] Erro ao enviar: {e}')
            return False

    async def send_to_room(self, message: Any, room: str) -> int:
        """
        Envia mensagem para todos em uma sala.
        Retorna número de destinatários.
        """
        count = 0
        for ws in list(self._rooms.get(room, [])):
            if await self.send(ws, message):
                count += 1
        return count

    async def send_to_user(self, message: Any, user_id: str) -> bool:
        """Envia mensagem para um usuário específico."""
        for ws, info in self._connections.items():
            if info.get('user_id') == user_id:
                return await self.send(ws, message)
        return False

    async def broadcast(self, message: Any, room: str = None) -> int:
        """
        Envia mensagem para todos ou para uma sala específica.
        Retorna número de destinatários.
        """
        if room:
            return await self.send_to_room(message, room)

        count = 0
        for ws in list(self._connections.keys()):
            if await self.send(ws, message):
                count += 1
        return count

    # ── Rooms ─────────────────────────────────────

    def join_room(self, ws, room: str) -> None:
        """Adiciona conexão a uma sala."""
        if ws not in self._connections:
            return

        old_room = self._connections[ws]['room']

        if old_room in self._rooms:
            self._rooms[old_room].discard(ws)

        self._connections[ws]['room'] = room
        self._rooms[room].add(ws)

    def leave_room(self, ws, room: str = None) -> None:
        """Remove conexão de uma sala."""
        if ws not in self._connections:
            return

        if room is None:
            room = self._connections[ws]['room']

        if room in self._rooms:
            self._rooms[room].discard(ws)

    def get_room_users(self, room: str) -> List[Dict]:
        """Retorna lista de usuários em uma sala."""
        users = []
        for ws, info in self._connections.items():
            if info['room'] == room:
                users.append({
                    'user_id':      info.get('user_id'),
                    'metadata':     info.get('metadata', {}),
                    'connected_at': info['connected_at'].isoformat(),
                })
        return users

    # ── Informações ───────────────────────────────

    @property
    def connection_count(self) -> int:
        """Número de conexões ativas."""
        return len(self._connections)

    @property
    def room_count(self) -> int:
        """Número de rooms ativas."""
        return len(self._rooms)

    def get_stats(self) -> Dict:
        """Estatísticas do gerenciador."""
        return {
            'connections':  len(self._connections),
            'rooms':        len(self._rooms),
            'room_details': {
                room: len(ws_list)
                for room, ws_list in self._rooms.items()
            },
        }

    # ── Callbacks de Eventos ─────────────────────

    def on_connect(self, callback: Callable):
        """Registra callback de conexão."""
        self._on_connect.append(callback)
        return callback

    def on_disconnect(self, callback: Callable):
        """Registra callback de desconexão."""
        self._on_disconnect.append(callback)
        return callback

    def on_message(self, callback: Callable):
        """Registra callback de mensagem."""
        self._on_message.append(callback)
        return callback

    # ── Heartbeat / Cleanup ───────────────────────

    async def _heartbeat(self):
        """Remove conexões mortas periodicamente."""
        while self._connections:
            await asyncio.sleep(self._heartbeat_interval)

            dead = [ws for ws in self._connections if getattr(ws, 'closed', False)]
            for ws in dead:
                self.disconnect(ws)

            if not self._connections:
                break

    async def close_all(self):
        """Fecha todas as conexões."""
        for ws in list(self._connections.keys()):
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()
        self._rooms.clear()

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None


# ─────────────────────────────────────────────────────────────────
# WebSocket Handler Helper
# ─────────────────────────────────────────────────────────────────

class WebSocketHandler:
    """
    Helper para criar handlers WebSocket com o gerenciador.

    Uso:
        handler = WebSocketHandler(manager)

        @app.websocket('/ws/chat')
        async def chat(ws):
            await handler.handle(ws, room='chat')
    """

    def __init__(self, manager: WebSocketManager = None):
        self.manager   = manager or WebSocketManager()
        self._handlers: Dict[str, Callable] = {}

    def register(self, event_type: str):
        """Registra handler para tipo de mensagem específico."""
        def decorator(fn):
            self._handlers[event_type] = fn
            return fn
        return decorator

    async def handle(self, ws, room: str = 'default', user_id: str = None):
        """Processa mensagens WebSocket."""
        await self.manager.connect(ws, room=room, user_id=user_id)

        try:
            while True:
                msg = await ws.receive()
                if msg is None:
                    break

                try:
                    data     = json.loads(msg)
                    msg_type = data.get('type', 'message')
                    msg_data = data.get('data')
                except (json.JSONDecodeError, TypeError):
                    msg_type = 'message'
                    msg_data = msg

                if ws in self.manager._connections:
                    self.manager._connections[ws]['messages_received'] += 1

                if msg_type in self._handlers:
                    handler = self._handlers[msg_type]
                    if asyncio.iscoroutinefunction(handler):
                        await handler(ws, msg_data)
                    else:
                        handler(ws, msg_data)

                for cb in self.manager._on_message:
                    try:
                        if asyncio.iscoroutinefunction(cb):
                            await cb(ws, msg_type, msg_data)
                        else:
                            cb(ws, msg_type, msg_data)
                    except Exception as e:
                        print(f'[WS] Erro no on_message: {e}')

        finally:
            self.manager.disconnect(ws)


# ─────────────────────────────────────────────────────────────────
# Decorator para rotas WebSocket
# ─────────────────────────────────────────────────────────────────

def ws_route(path: str, manager: WebSocketManager = None):
    """
    Decorator para criar rotas WebSocket com gerenciador.

    Uso:
        ws_manager = WebSocketManager()

        @ws_route('/ws/chat', ws_manager)
        async def chat_handler(ws, mgr):
            msg = await ws.receive()
            await mgr.broadcast({'type': 'chat', 'message': msg}, room='chat')
    """
    def decorator(fn):
        async def wrapper(ws):
            # FIX: usava 'ws_manager' (undefined) em vez de 'manager' (parâmetro)
            mgr = manager or get_manager()
            await mgr.connect(ws)
            try:
                await fn(ws, mgr)
            finally:
                mgr.disconnect(ws)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────
# Instância global (singleton)
# ─────────────────────────────────────────────────────────────────

_default_manager: Optional[WebSocketManager] = None


def get_manager() -> WebSocketManager:
    """Retorna o gerenciador padrão (singleton)."""
    global _default_manager
    if _default_manager is None:
        _default_manager = WebSocketManager()
    return _default_manager
