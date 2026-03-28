"""
Sistema de Gerenciamento de Arquivos - Velox
Similar ao django.core.files
"""

import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO


class File:
    """Representa um arquivo"""
    
    def __init__(self, file: BinaryIO, name: str = None):
        self.file = file
        self.name = name or getattr(file, 'name', '')
        self.mode = getattr(file, 'mode', 'rb')
        self._closed = False
    
    def __iter__(self):
        return iter(self.file)
    
    def read(self, size: int = -1):
        return self.file.read(size)
    
    def write(self, content):
        return self.file.write(content)
    
    def seek(self, offset: int):
        return self.file.seek(offset)
    
    def tell(self):
        return self.file.tell()
    
    def close(self):
        self.file.close()
        self._closed = True
    
    @property
    def closed(self):
        return self._closed
    
    @property
    def size(self):
        """Tamanho do arquivo"""
        self.file.seek(0, 2)
        size = self.file.tell()
        self.file.seek(0)
        return size


class UploadedFile(File):
    """Arquivo enviado via upload"""

    def __init__(self, file: BinaryIO, name: str, content_type: str = None):
        super().__init__(file, name)
        self.content_type = content_type
        # Calcula tamanho a partir do objeto file, não do caminho de origem
        try:
            pos = file.tell()
            file.seek(0, 2)
            self._upload_size = file.tell()
            file.seek(pos)
        except Exception:
            self._upload_size = 0

    @property
    def size(self):
        return self._upload_size


class FileField:
    """Campo de arquivo para modelos"""
    
    def __init__(self, upload_to: str = '', max_length: int = 100):
        self.upload_to = upload_to
        self.max_length = max_length
    
    def generate_filename(self, instance, filename: str) -> str:
        """Gera nome do arquivo"""
        import uuid
        ext = os.path.splitext(filename)[1]
        new_name = f"{uuid.uuid4().hex}{ext}"
        
        if callable(self.upload_to):
            return self.upload_to(instance, new_name)
        
        folder = self.upload_to or 'uploads'
        return f"{folder}/{new_name}"


def upload_to(instance, filename: str) -> str:
    """Função padrão de upload"""
    import uuid
    ext = os.path.splitext(filename)[1]
    return f"uploads/{uuid.uuid4().hex}{ext}"


def save_upload(file: UploadedFile, destination: str) -> str:
    """Salva arquivo enviado"""
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    
    with open(destination, 'wb') as dest:
        shutil.copyfileobj(file.file, dest)
    
    return destination


def delete_file(path: str) -> bool:
    """Deleta arquivo"""
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception as e:
        print(f"Erro ao deletar arquivo: {e}")
    return False


def get_file_extension(filename: str) -> str:
    """Obtém extensão do arquivo"""
    return os.path.splitext(filename)[1].lower()


def get_file_size(path: str) -> int:
    """Obtém tamanho do arquivo em bytes"""
    return os.path.getsize(path)


def file_exists(path: str) -> bool:
    """Verifica se arquivo existe"""
    return os.path.isfile(path)


def read_file(path: str, mode: str = 'r') -> str:
    """Lê conteúdo do arquivo"""
    with open(path, mode) as f:
        return f.read()


def write_file(path: str, content: str, mode: str = 'w') -> None:
    """Escreve conteúdo no arquivo"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode) as f:
        f.write(content)
