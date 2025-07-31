import os
import winreg
import subprocess
import ctypes
import shutil
import time
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import logging
import sys

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_admin() -> bool:
    """Verifica se o programa está sendo executado como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

def relaunch_as_admin():
    """Relança o script como administrador, se não estiver"""
    if not is_admin():
        try:
            params = " ".join([f'"{arg}"' if " " in arg else arg for arg in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
            sys.exit(0)
        except Exception as e:
            logger.error(f"Falha ao tentar relançar como administrador: {e}")
            print("Este programa precisa ser executado como administrador.")
            sys.exit(1)

# Garante que o script só continue se estiver em modo administrador
relaunch_as_admin()

@dataclass
class ProgramInfo:
    name: str
    version: str
    size: int  # em KB
    uninstall_string: Optional[str]
    install_location: Optional[str]
    publisher: Optional[str]
    icon_path: Optional[str] = None  # Novo campo para ícone do programa

@dataclass
class FileInfo:
    path: str
    size: int  # em bytes
    last_accessed: float
    last_modified: float
    extension: str
    is_directory: bool = False  # Novo campo para identificar diretórios

class SystemScanner:
    # Cache para resultados de disco para evitar chamadas repetidas
    _disk_cache = {}
    _last_disk_check = 0
    
    @staticmethod
    def get_installed_programs(include_updates: bool = False) -> List[ProgramInfo]:
        """Retorna lista de programas instalados com opção para incluir atualizações"""
        programs = []
        seen_programs = set()  # Para evitar duplicatas
        
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for key, subkey in registry_keys:
            try:
                with winreg.OpenKey(key, subkey) as registry_key:
                    for i in range(0, winreg.QueryInfoKey(registry_key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(registry_key, i)
                            with winreg.OpenKey(registry_key, subkey_name) as subkey:
                                name = SystemScanner._get_reg_value(subkey, "DisplayName")
                                if not name or (not include_updates and "Update" in name):
                                    continue
                                
                                # Verifica se já vimos este programa
                                if name in seen_programs:
                                    continue
                                seen_programs.add(name)
                                
                                install_location = SystemScanner._get_reg_value(subkey, "InstallLocation")
                                programs.append(ProgramInfo(
                                    name=name,
                                    version=SystemScanner._get_reg_value(subkey, "DisplayVersion") or "N/A",
                                    size=int(SystemScanner._get_reg_value(subkey, "EstimatedSize") or 0),
                                    uninstall_string=SystemScanner._get_reg_value(subkey, "UninstallString"),
                                    install_location=install_location,
                                    publisher=SystemScanner._get_reg_value(subkey, "Publisher"),
                                    icon_path=SystemScanner._get_program_icon(subkey, install_location)
                                ))
                        except (WindowsError, OSError) as e:
                            logger.debug(f"Error reading registry subkey {subkey_name}: {e}")
                            continue
            except (WindowsError, OSError) as e:
                logger.debug(f"Error opening registry key {subkey}: {e}")
                continue
        
        # Ordena por tamanho (maiores primeiro) e depois por nome
        programs.sort(key=lambda x: (-x.size, x.name.lower()))
        return programs

    @staticmethod
    def _get_program_icon(subkey, install_location: Optional[str]) -> Optional[str]:
        """Tenta obter o caminho do ícone do programa"""
        icon_path = SystemScanner._get_reg_value(subkey, "DisplayIcon")
        if icon_path:
            # Limpa o caminho do ícone (pode conter índices ou parâmetros)
            if "," in icon_path:
                icon_path = icon_path.split(",")[0]
            if os.path.exists(icon_path):
                return icon_path
        
        if install_location:
            # Tenta encontrar um ícone padrão no diretório de instalação
            for ext in ['.exe', '.ico']:
                for root, _, files in os.walk(install_location):
                    for file in files:
                        if file.lower().endswith(ext):
                            full_path = os.path.join(root, file)
                            return full_path
        return None

    @staticmethod
    def _get_reg_value(key, value_name: str) -> Optional[str]:
        """Obtém um valor do registro com tratamento de erros"""
        try:
            value, reg_type = winreg.QueryValueEx(key, value_name)
            if reg_type == winreg.REG_EXPAND_SZ:
                return os.path.expandvars(value)
            return str(value) if value is not None else None
        except (WindowsError, ValueError):
            return None

    @staticmethod
    def uninstall_program(uninstall_string: str) -> bool:
        """Executa o comando de desinstalação com tratamento aprimorado"""
        try:
            # Limpa a string de desinstalação (pode conter aspas ou parâmetros)
            if uninstall_string.lower().startswith(('msiexec', 'msexec')):
                # Para instalações MSI
                cmd = uninstall_string
            else:
                # Para executáveis normais
                if '"' in uninstall_string:
                    cmd = uninstall_string
                else:
                    parts = uninstall_string.split()
                    cmd = f'"{parts[0]}"' + (' ' + ' '.join(parts[1:]) if len(parts) > 1 else '')
            
            # Executa como administrador sempre
            # Se já for admin, executa normalmente, senão relança como admin
            if is_admin():
                subprocess.run(cmd, check=True, shell=True, timeout=300)
            else:
                # Executa o comando como administrador
                # ShellExecuteW espera o caminho do executável e argumentos separados
                if cmd.startswith('"') and '"' in cmd[1:]:
                    # Se o comando já está entre aspas, separa o executável dos argumentos
                    exe_end = cmd.find('"', 1)
                    exe_path = cmd[1:exe_end]
                    args = cmd[exe_end+1:].strip()
                else:
                    parts = cmd.split(" ", 1)
                    exe_path = parts[0].strip('"')
                    args = parts[1] if len(parts) > 1 else ""
                # Chama como administrador
                ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, args, None, 1)
            
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            logger.error(f"Failed to uninstall program: {e}")
            return False

    @staticmethod
    def scan_files(
        directories: List[str],
        min_size: int = 0,
        max_size: Optional[int] = None,
        extensions: Optional[List[str]] = None,
        include_directories: bool = False
    ) -> List[FileInfo]:
        """
        Encontra arquivos com base em critérios de tamanho e extensão
        
        Args:
            directories: Lista de diretórios para escanear
            min_size: Tamanho mínimo em bytes
            max_size: Tamanho máximo em bytes (None para ilimitado)
            extensions: Lista de extensões para filtrar (None para todas)
            include_directories: Se deve incluir diretórios nos resultados
        """
        file_list = []
        extensions_set = {ext.lower() for ext in extensions} if extensions else None
        processed_dirs = set()

        for directory in directories:
            # Normaliza o caminho para evitar duplicatas
            norm_dir = os.path.normpath(directory)
            if norm_dir in processed_dirs:
                continue
            processed_dirs.add(norm_dir)

            try:
                # Verifica se o diretório existe
                if not os.path.isdir(norm_dir):
                    logger.warning(f"Directory not found: {norm_dir}")
                    continue

                # Adiciona o próprio diretório se solicitado
                if include_directories:
                    dir_stat = os.stat(norm_dir)
                    file_list.append(FileInfo(
                        path=norm_dir,
                        size=0,
                        last_accessed=dir_stat.st_atime,
                        last_modified=dir_stat.st_mtime,
                        extension="",
                        is_directory=True
                    ))

                # Percorre o diretório
                for root, dirs, files in os.walk(norm_dir, onerror=lambda e: logger.warning(f"Error accessing {e.filename}: {e.strerror}")):
                    # Processa arquivos
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            stat = os.stat(file_path)
                            size = stat.st_size
                            
                            # Aplica filtros
                            if size < min_size:
                                continue
                            if max_size and size > max_size:
                                continue
                            
                            ext = os.path.splitext(file)[1].lower()
                            if extensions_set and ext not in extensions_set:
                                continue
                            
                            file_list.append(FileInfo(
                                path=file_path,
                                size=size,
                                last_accessed=stat.st_atime,
                                last_modified=stat.st_mtime,
                                extension=ext
                            ))
                        except (PermissionError, OSError) as e:
                            logger.debug(f"Error accessing file {file}: {e}")
                            continue

                    # Adiciona subdiretórios se solicitado
                    if include_directories:
                        for dir_name in dirs:
                            try:
                                dir_path = os.path.join(root, dir_name)
                                dir_stat = os.stat(dir_path)
                                file_list.append(FileInfo(
                                    path=dir_path,
                                    size=0,
                                    last_accessed=dir_stat.st_atime,
                                    last_modified=dir_stat.st_mtime,
                                    extension="",
                                    is_directory=True
                                ))
                            except (PermissionError, OSError) as e:
                                logger.debug(f"Error accessing directory {dir_name}: {e}")
                                continue

            except Exception as e:
                logger.error(f"Error scanning directory {norm_dir}: {e}")
                continue
        
        # Ordena por tamanho (maiores primeiro) e depois por caminho
        file_list.sort(key=lambda x: (-x.size, x.path.lower()))
        return file_list

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Remove um arquivo ou diretório do sistema"""
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path, ignore_errors=False)
            else:
                os.remove(file_path)
            return True
        except PermissionError:
            # Tenta com elevação de privilégios
            try:
                if is_admin():
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path, ignore_errors=False)
                    else:
                        os.remove(file_path)
                    return True
                else:
                    # Relança o script como administrador para deletar o arquivo/diretório
                    params = f'"{sys.argv[0]}" --delete "{file_path}"'
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                    return True
            except Exception as e:
                logger.error(f"Failed to delete with admin rights: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False

    @staticmethod
    def is_admin() -> bool:
        """Verifica se o programa está sendo executado como administrador"""
        # Agora utiliza a função global is_admin()
        return is_admin()

    @staticmethod
    def get_disk_usage(path: str = "C:\\") -> Dict[str, float]:
        """Retorna estatísticas de uso do disco com cache de 5 segundos"""
        current_time = time.time()
        
        # Usa cache se disponível e não expirado
        if path in SystemScanner._disk_cache:
            cached_data, timestamp = SystemScanner._disk_cache[path]
            if current_time - timestamp < 5:  # 5 segundos de cache
                return cached_data
        
        try:
            total, used, free = shutil.disk_usage(path)
            result = {
                "total": total,
                "used": used,
                "free": free,
                "percent_used": (used / total) * 100 if total > 0 else 0,
                "path": path
            }
            
            # Atualiza cache
            SystemScanner._disk_cache[path] = (result, current_time)
            return result
        except Exception as e:
            logger.error(f"Error getting disk usage for {path}: {e}")
            return {
                "total": 0,
                "used": 0,
                "free": 0,
                "percent_used": 0,
                "path": path
            }

    @staticmethod
    def open_file_location(file_path: str) -> bool:
        """Abre o explorador de arquivos na localização do arquivo em modo administrador"""
        try:
            if os.path.exists(file_path):
                # Abre o explorer como administrador e seleciona o arquivo
                explorer_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "explorer.exe")
                args = f'/select,"{os.path.normpath(file_path)}"'
                ctypes.windll.shell32.ShellExecuteW(None, "runas", explorer_path, args, None, 1)
                return True
            return False
        except Exception as e:
            logger.error(f"Error opening file location {file_path}: {e}")
            return False

    @staticmethod
    def get_file_properties(file_path: str) -> Optional[Dict]:
        """Obtém propriedades estendidas do arquivo"""
        try:
            if not os.path.exists(file_path):
                return None
                
            stat = os.stat(file_path)
            return {
                "path": file_path,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "is_dir": os.path.isdir(file_path),
                "extension": os.path.splitext(file_path)[1].lower() if not os.path.isdir(file_path) else ""
            }
        except Exception as e:
            logger.error(f"Error getting file properties {file_path}: {e}")
            return None