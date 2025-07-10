"""
Configuration globale de l'application
"""

import json
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    """Configuration principale de l'application"""
    
    # Chemins
    data_dir: str = "data"
    library_file: str = "library.json"
    cache_dir: str = "cache"
    
    # Interface
    window_width: int = 1300        # AUGMENTÉ de 1200 à 1300
    window_height: int = 900        # AUGMENTÉ de 800 à 900
    splitter_left_width: int = 500  # AUGMENTÉ de 400 à 500 pour la zone vidéo
    media_player_height: int = 400  # AUGMENTÉ de 180 à 400
    
    # Répartition du panel gauche (bibliothèque vs lecteur)
    library_height: int = 300       # RÉDUIT de 400 à 300
    player_height: int = 400        # AUGMENTÉ de 300 à 400
    
    # Fonctionnalités
    auto_save: bool = True
    auto_backup: bool = True
    backup_count: int = 5
    
    # Formats supportés
    document_formats: list = None
    audio_formats: list = None
    video_formats: list = None
    
    # Cloud
    cloud_sync: bool = False
    cloud_provider: str = ""  # "pcloud", "gdrive", "dropbox"
    
    # Thème
    theme: str = "default"  # "default", "dark", "light"
    
    def __post_init__(self):
        """Initialise les listes par défaut"""
        if self.document_formats is None:
            self.document_formats = ['.pdf', '.txt', '.doc', '.docx', '.odt', '.rtf',
                                   '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
        
        if self.audio_formats is None:
            self.audio_formats = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', 
                                '.aac', '.wma']
        
        if self.video_formats is None:
            self.video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', 
                                '.flv', '.webm']


class ConfigManager:
    """Gestionnaire de configuration"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = AppConfig()
        self.load_config()
    
    def load_config(self) -> bool:
        """Charge la configuration depuis le fichier"""
        if not self.config_path.exists():
            # Créer une configuration par défaut
            self.save_config()
            return True
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Mettre à jour la configuration
            for key, value in data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            return True
            
        except Exception as e:
            print(f"Erreur lors du chargement de la configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """Sauvegarde la configuration"""
        try:
            # Créer le dossier parent si nécessaire
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {e}")
            return False
    
    def get_data_dir(self) -> Path:
        """Retourne le dossier de données"""
        data_dir = Path(self.config.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def get_library_path(self) -> Path:
        """Retourne le chemin complet vers la bibliothèque"""
        return self.get_data_dir() / self.config.library_file
    
    def get_supported_formats(self) -> Dict[str, list]:
        """Retourne tous les formats supportés par type"""
        return {
            'documents': self.config.document_formats,
            'audio': self.config.audio_formats,
            'video': self.config.video_formats
        }
        """Retourne le dossier de cache"""
        cache_dir = Path(self.config.cache_dir)
    def get_cache_dir(self) -> Path:
        """Retourne le dossier de cache"""
        cache_dir = Path(self.config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def is_supported_document(self, file_path: Path) -> bool:
        """Vérifie si le format de document est supporté"""
        return file_path.suffix.lower() in self.config.document_formats
    
    def is_supported_audio(self, file_path: Path) -> bool:
        """Vérifie si le format audio est supporté"""
        return file_path.suffix.lower() in self.config.audio_formats
    
    def is_supported_video(self, file_path: Path) -> bool:
        """Vérifie si le format vidéo est supporté"""
        return file_path.suffix.lower() in self.config.video_formats
    
    def is_supported_media(self, file_path: Path) -> str:
        """
        Retourne le type de média supporté
        
        Returns:
            str: 'document', 'audio', 'video' ou 'unsupported'
        """
        if self.is_supported_document(file_path):
            return 'document'
        elif self.is_supported_audio(file_path):
            return 'audio'
        elif self.is_supported_video(file_path):
            return 'video'
        else:
            return 'unsupported'


# Instance globale du gestionnaire de configuration
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Retourne la configuration actuelle"""
    return config_manager.config


def save_config() -> bool:
    """Sauvegarde la configuration actuelle"""
    return config_manager.save_config()


def get_supported_formats() -> Dict[str, list]:
    """Retourne tous les formats supportés"""
    config = get_config()
    return {
        'documents': config.document_formats,
        'audio': config.audio_formats,
        'video': config.video_formats
    }


def get_all_supported_extensions() -> list:
    """Retourne toutes les extensions supportées"""
    formats = get_supported_formats()
    all_formats = []
    for format_list in formats.values():
        all_formats.extend(format_list)
    return sorted(list(set(all_formats)))