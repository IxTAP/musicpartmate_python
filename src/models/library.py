"""
Gestionnaire de la bibliothèque musicale
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
import shutil
from datetime import datetime

from .song import Song


@dataclass
class LibraryConfig:
    """Configuration de la bibliothèque"""
    library_path: Path
    auto_backup: bool = True
    backup_count: int = 5
    cloud_sync: bool = False
    cloud_provider: str = ""  # "pcloud", "gdrive", "dropbox"


class Library:
    """
    Gestionnaire de la bibliothèque musicale
    
    Gère la persistance, la recherche et l'organisation des chansons
    """
    
    def __init__(self, config: LibraryConfig = None):
        """
        Initialise la bibliothèque
        
        Args:
            config: Configuration de la bibliothèque
        """
        if config is None:
            config = LibraryConfig(library_path=Path("data/library.json"))
        
        self.config = config
        self.songs: List[Song] = []
        self._observers: List[Callable] = []  # Observateurs pour les changements
        
        # Créer le dossier de données si nécessaire
        self.config.library_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Charger la bibliothèque
        self.load_library()
    
    def add_observer(self, callback: Callable) -> None:
        """Ajoute un observateur qui sera notifié des changements"""
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback: Callable) -> None:
        """Supprime un observateur"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, event_type: str, song: Song = None) -> None:
        """Notifie tous les observateurs d'un changement"""
        for callback in self._observers:
            try:
                callback(event_type, song)
            except Exception as e:
                print(f"Erreur dans l'observateur: {e}")
    
    @property
    def song_count(self) -> int:
        """Nombre de chansons dans la bibliothèque"""
        return len(self.songs)
    
    @property
    def artists(self) -> List[str]:
        """Liste unique des artistes"""
        artists = {song.artist for song in self.songs if song.artist}
        return sorted(list(artists))
    
    @property
    def styles(self) -> List[str]:
        """Liste unique des styles"""
        styles = {song.style for song in self.songs if song.style}
        return sorted(list(styles))
    
    def add_song(self, song: Song) -> bool:
        """
        Ajoute une chanson à la bibliothèque
        
        Args:
            song: Chanson à ajouter
            
        Returns:
            bool: True si ajouté avec succès
        """
        # Valider la chanson
        if not song.is_valid():
            return False
        
        # Vérifier les doublons
        if self.find_duplicate(song):
            return False
        
        self.songs.append(song)
        self.save_library()
        self._notify_observers("song_added", song)
        return True
    
    def remove_song(self, song: Song) -> bool:
        """
        Supprime une chanson de la bibliothèque
        
        Args:
            song: Chanson à supprimer
            
        Returns:
            bool: True si supprimé avec succès
        """
        if song in self.songs:
            self.songs.remove(song)
            self.save_library()
            self._notify_observers("song_removed", song)
            return True
        return False
    
    def update_song(self, song: Song) -> bool:
        """
        Met à jour une chanson existante
        
        Args:
            song: Chanson à mettre à jour
            
        Returns:
            bool: True si mis à jour avec succès
        """
        if song in self.songs and song.is_valid():
            self.save_library()
            self._notify_observers("song_updated", song)
            return True
        return False
    
    def find_song_by_id(self, song_id: str) -> Optional[Song]:
        """Trouve une chanson par son ID unique"""
        # Pour l'instant, on utilise le titre + artiste comme ID
        for song in self.songs:
            if f"{song.artist}#{song.title}" == song_id:
                return song
        return None
    
    def find_duplicate(self, song: Song) -> Optional[Song]:
        """
        Cherche un doublon potentiel
        
        Args:
            song: Chanson à vérifier
            
        Returns:
            Song: Chanson similaire trouvée ou None
        """
        for existing_song in self.songs:
            if (existing_song.title.lower() == song.title.lower() and 
                existing_song.artist.lower() == song.artist.lower()):
                return existing_song
        return None
    
    def search_songs(self, query: str, search_in: List[str] = None) -> List[Song]:
        """
        Recherche des chansons
        
        Args:
            query: Texte à rechercher
            search_in: Liste des champs où chercher ['title', 'artist', 'style']
            
        Returns:
            List[Song]: Chansons correspondantes
        """
        if search_in is None:
            search_in = ['title', 'artist', 'style']
        
        query = query.lower()
        results = []
        
        for song in self.songs:
            # Recherche dans les champs spécifiés
            match_found = False
            
            if 'title' in search_in and query in song.title.lower():
                match_found = True
            elif 'artist' in search_in and query in song.artist.lower():
                match_found = True
            elif 'style' in search_in and query in song.style.lower():
                match_found = True
            
            if match_found:
                results.append(song)
        
        return results
    
    def filter_by_artist(self, artist: str) -> List[Song]:
        """Filtre les chansons par artiste"""
        return [song for song in self.songs if song.artist.lower() == artist.lower()]
    
    def filter_by_style(self, style: str) -> List[Song]:
        """Filtre les chansons par style"""
        return [song for song in self.songs if song.style.lower() == style.lower()]
    
    def get_songs_sorted(self, sort_by: str = 'title', reverse: bool = False) -> List[Song]:
        """
        Retourne les chansons triées
        
        Args:
            sort_by: Champ de tri ('title', 'artist', 'style')
            reverse: Tri inversé
            
        Returns:
            List[Song]: Chansons triées
        """
        if sort_by == 'title':
            return sorted(self.songs, key=lambda s: s.title.lower(), reverse=reverse)
        elif sort_by == 'artist':
            return sorted(self.songs, key=lambda s: s.artist.lower(), reverse=reverse)
        elif sort_by == 'style':
            return sorted(self.songs, key=lambda s: s.style.lower(), reverse=reverse)
        else:
            return self.songs.copy()
    
    def save_library(self) -> bool:
        """
        Sauvegarde la bibliothèque sur disque
        
        Returns:
            bool: True si sauvegarde réussie
        """
        try:
            # Backup automatique si configuré
            if self.config.auto_backup and self.config.library_path.exists():
                self._create_backup()
            
            # Préparer les données
            data = {
                'version': '1.0',
                'created_date': datetime.now().isoformat(),
                'song_count': len(self.songs),
                'config': {
                    'auto_backup': self.config.auto_backup,
                    'backup_count': self.config.backup_count,
                    'cloud_sync': self.config.cloud_sync,
                    'cloud_provider': self.config.cloud_provider
                },
                'songs': [song.to_dict() for song in self.songs]
            }
            
            # Sauvegarder
            with open(self.config.library_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {e}")
            return False
    
    def load_library(self) -> bool:
        """
        Charge la bibliothèque depuis le disque
        
        Returns:
            bool: True si chargement réussi
        """
        if not self.config.library_path.exists():
            # Créer une bibliothèque vide
            self.songs = []
            return True
        
        try:
            with open(self.config.library_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Charger les chansons
            self.songs = []
            for song_data in data.get('songs', []):
                try:
                    song = Song.from_dict(song_data)
                    self.songs.append(song)
                except Exception as e:
                    print(f"Erreur lors du chargement d'une chanson: {e}")
            
            # Charger la configuration si présente
            if 'config' in data:
                config_data = data['config']
                self.config.auto_backup = config_data.get('auto_backup', True)
                self.config.backup_count = config_data.get('backup_count', 5)
                self.config.cloud_sync = config_data.get('cloud_sync', False)
                self.config.cloud_provider = config_data.get('cloud_provider', '')
            
            print(f"Bibliothèque chargée: {len(self.songs)} chansons")
            return True
            
        except Exception as e:
            print(f"Erreur lors du chargement de la bibliothèque: {e}")
            self.songs = []
            return False
    
    def _create_backup(self) -> None:
        """Crée une sauvegarde de la bibliothèque"""
        backup_dir = self.config.library_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Nom du backup avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"library_backup_{timestamp}.json"
        backup_path = backup_dir / backup_name
        
        # Copier le fichier
        shutil.copy2(self.config.library_path, backup_path)
        
        # Nettoyer les anciens backups
        self._cleanup_old_backups(backup_dir)
    
    def _cleanup_old_backups(self, backup_dir: Path) -> None:
        """Supprime les anciens backups en gardant seulement backup_count fichiers"""
        backup_files = list(backup_dir.glob("library_backup_*.json"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Supprimer les fichiers en excès
        for old_backup in backup_files[self.config.backup_count:]:
            try:
                old_backup.unlink()
            except Exception as e:
                print(f"Erreur lors de la suppression du backup {old_backup}: {e}")
    
    def export_library(self, export_path: Path, format_type: str = 'json') -> bool:
        """
        Exporte la bibliothèque dans différents formats
        
        Args:
            export_path: Chemin d'export
            format_type: Format ('json', 'csv')
            
        Returns:
            bool: True si export réussi
        """
        try:
            if format_type == 'json':
                return self._export_json(export_path)
            elif format_type == 'csv':
                return self._export_csv(export_path)
            else:
                return False
        except Exception as e:
            print(f"Erreur lors de l'export: {e}")
            return False
    
    def _export_json(self, export_path: Path) -> bool:
        """Exporte en JSON"""
        data = {
            'exported_date': datetime.now().isoformat(),
            'song_count': len(self.songs),
            'songs': [song.to_dict() for song in self.songs]
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def _export_csv(self, export_path: Path) -> bool:
        """Exporte en CSV"""
        import csv
        
        with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['title', 'artist', 'tempo', 'style', 'documents', 'audios', 'videos']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for song in self.songs:
                writer.writerow({
                    'title': song.title,
                    'artist': song.artist,
                    'tempo': song.tempo,
                    'style': song.style,
                    'documents': ';'.join([str(d) for d in song.documents]),
                    'audios': ';'.join([str(a) for a in song.audios]),
                    'videos': ';'.join([str(v) for v in song.videos])
                })
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la bibliothèque"""
        return {
            'total_songs': len(self.songs),
            'total_artists': len(self.artists),
            'total_styles': len(self.styles),
            'songs_with_documents': len([s for s in self.songs if s.has_documents]),
            'songs_with_audio': len([s for s in self.songs if s.has_audio]),
            'songs_with_video': len([s for s in self.songs if s.has_video]),
            'most_common_style': self._get_most_common_style(),
            'most_prolific_artist': self._get_most_prolific_artist()
        }
    
    def _get_most_common_style(self) -> str:
        """Retourne le style le plus fréquent"""
        style_counts = {}
        for song in self.songs:
            if song.style:
                style_counts[song.style] = style_counts.get(song.style, 0) + 1
        
        if style_counts:
            return max(style_counts, key=style_counts.get)
        return ""
    
    def _get_most_prolific_artist(self) -> str:
        """Retourne l'artiste avec le plus de chansons"""
        artist_counts = {}
        for song in self.songs:
            if song.artist:
                artist_counts[song.artist] = artist_counts.get(song.artist, 0) + 1
        
        if artist_counts:
            return max(artist_counts, key=artist_counts.get)
        return ""