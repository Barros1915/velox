"""
Sistema de Sinais/Eventos - Velox
Similar ao django.core.signals
"""

from typing import Callable, Any, List, Dict
from collections import defaultdict


class Signal:
    """Sistema de sinais e eventos"""
    
    def __init__(self, providing_args: List[str] = None):
        self.providing_args = providing_args or []
        self._receivers = []
        self._dead_receivers = False
    
    def connect(self, receiver: Callable, sender: Any = None, weak: bool = True, dispatch_uid: str = None):
        """Conecta um receiver ao sinal"""
        # Criar receiver wrapper
        lookup_key = (sender, dispatch_uid)
        
        # Verificar se já existe
        for existing in self._receivers:
            if (existing[0] == sender and existing[1] == dispatch_uid):
                return  # Já conectado
        
        self._receivers.append((sender, dispatch_uid, receiver))
        self._dead_receivers = False
    
    def disconnect(self, receiver: Callable = None, sender: Any = None, dispatch_uid: str = None):
        """Desconecta um receiver"""
        if receiver is None:
            # Desconectar por sender e uid
            self._receivers = [
                r for r in self._receivers 
                if not (r[0] == sender and r[1] == dispatch_uid)
            ]
        else:
            self._receivers = [
                r for r in self._receivers 
                if r[2] != receiver
            ]
    
    def send(self, sender: Any = None, **kwargs):
        """Envia o sinal para todos os receivers"""
        responses = []
        
        for receiver in self._receivers:
            r_sender, r_uid, r_func = receiver
            
            # Verificar se o receiver deve receber este sinal
            if r_sender is not None and r_sender != sender:
                continue
            
            try:
                response = r_func(sender, **kwargs)
                responses.append((r_func, response))
            except Exception as e:
                print(f"Erro no receiver {r_func}: {e}")
        
        return responses
    
    def send_robust(self, sender: Any = None, **kwargs):
        """Envia o sinal, capturando exceções"""
        responses = []
        
        for receiver in self._receivers:
            r_sender, r_uid, r_func = receiver
            
            if r_sender is not None and r_sender != sender:
                continue
            
            try:
                response = r_func(sender, **kwargs)
                responses.append((r_func, response))
            except Exception as e:
                responses.append((r_func, e))
        
        return responses


class SignalManager:
    """Gerenciador de sinais globais"""
    
    def __init__(self):
        self._signals = {}
    
    def create_signal(self, name: str, providing_args: List[str] = None) -> Signal:
        """Cria um novo sinal"""
        signal = Signal(providing_args)
        self._signals[name] = signal
        return signal
    
    def get_signal(self, name: str) -> Signal:
        """Obtém um sinal pelo nome"""
        return self._signals.get(name)


# Sinais padrão do Velox
request_started = Signal(['request'])
request_finished = Signal(['request'])
request_error = Signal(['request', 'exception'])
template_rendered = Signal(['template', 'context'])
database_query = Signal(['query', 'time'])
user_logged_in = Signal(['request', 'user'])
user_logged_out = Signal(['request', 'user'])


# Instância global
_signals = SignalManager()


# Decorador para conectar sinais
def receiver(signal: Signal, sender: Any = None, dispatch_uid: str = None):
    """Decorador para conectar funções a sinais"""
    def decorator(func: Callable):
        signal.connect(func, sender=sender, dispatch_uid=dispatch_uid)
        return func
    return decorator


# Funções de conveniência
def create_signal(name: str, **kwargs) -> Signal:
    """Cria um sinal customizado"""
    return _signals.create_signal(name, **kwargs)


def connect(signal_name: str, func: Callable, sender: Any = None, **kwargs):
    """Conecta uma função a um sinal"""
    signal = _signals.get_signal(signal_name)
    if signal:
        signal.connect(func, sender=sender, **kwargs)


def emit(signal_name: str, sender: Any = None, **kwargs):
    """Emite um sinal"""
    signal = _signals.get_signal(signal_name)
    if signal:
        return signal.send(sender, **kwargs)
    return []
