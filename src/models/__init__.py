# src/models/__init__.py
"""
Modèles de données pour MusicPartMate
"""

from .song import Song, create_song_from_folder
from .library import Library, LibraryConfig

__all__ = ['Song', 'Library', 'LibraryConfig', 'create_song_from_folder']