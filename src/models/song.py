"""
Modèle de données pour une chanson
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json


@dataclass
class Song:
    """
    Représente une chanson avec ses métadonnées et médias associés
    
    Utilise @dataclass pour simplifier la création et la gestion des données
    """
    
    # Métadonnées principales
    title: str = ""
    artist: str = ""
    tempo: str = ""
    style: str = ""
    
    # Chemin de stockage
    path: Optional[Path] = None
    
    # Listes de médias (utilisation de field pour éviter les listes mutables partagées)
    documents: List[Path] = field(default_factory=list)
    audios: List[Path] = field(default_factory=list)
    videos: List[Path] = field(default_factory=list)
    
    # Métadonnées supplémentaires extensibles
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Appelé après l'initialisation pour normaliser les données"""
        # Convertir les chemins en objets Path si nécessaire
        if isinstance(self.path, str):
            self.path = Path(self.path) if self.path else None
        
        # Normaliser les listes de médias
        self.documents = [Path(p) if isinstance(p, str) else p for p in self.documents]
        self.audios = [Path(p) if isinstance(p, str) else p for p in self.audios]
        self.videos = [Path(p) if isinstance(p, str) else p for p in self.videos]
    
    @property
    def display_name(self) -> str:
        """Nom d'affichage de la chanson"""
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        elif self.title:
            return self.title
        elif self.artist:
            return f"{self.artist} - Sans titre"
        else:
            return "Chanson sans titre"
    
    @property
    def has_documents(self) -> bool:
        """Vérifie si la chanson a des documents"""
        return len(self.documents) > 0
    
    @property
    def has_audio(self) -> bool:
        """Vérifie si la chanson a des fichiers audio"""
        return len(self.audios) > 0
    
    @property
    def has_video(self) -> bool:
        """Vérifie si la chanson a des fichiers vidéo"""
        return len(self.videos) > 0
    
    @property
    def primary_document(self) -> Optional[Path]:
        """Retourne le document principal (premier de la liste)"""
        return self.documents[0] if self.documents else None
    
    def add_document(self, file_path: Path) -> None:
        """Ajoute un document à la chanson"""
        if file_path not in self.documents:
            self.documents.append(file_path)
    
    def add_audio(self, file_path: Path) -> None:
        """Ajoute un fichier audio à la chanson"""
        if file_path not in self.audios:
            self.audios.append(file_path)
    
    def add_video(self, file_path: Path) -> None:
        """Ajoute un fichier vidéo à la chanson"""
        if file_path not in self.videos:
            self.videos.append(file_path)
    
    def remove_media(self, file_path: Path) -> bool:
        """
        Supprime un média de toutes les listes
        Retourne True si le fichier a été trouvé et supprimé
        """
        removed = False
        
        if file_path in self.documents:
            self.documents.remove(file_path)
            removed = True
        
        if file_path in self.audios:
            self.audios.remove(file_path)
            removed = True
        
        if file_path in self.videos:
            self.videos.remove(file_path)
            removed = True
        
        return removed
    
    def get_all_media_files(self) -> List[Path]:
        """Retourne tous les fichiers média de la chanson"""
        return self.documents + self.audios + self.videos
    
    def validate(self) -> List[str]:
        """
        Valide la chanson et retourne une liste des erreurs trouvées
        """
        errors = []
        
        # Vérifier qu'il y a au moins un titre ou un artiste
        if not self.title and not self.artist:
            errors.append("La chanson doit avoir au moins un titre ou un artiste")
        
        # Vérifier qu'il y a au moins un média
        if not self.has_documents and not self.has_audio and not self.has_video:
            errors.append("La chanson doit avoir au moins un document, audio ou vidéo")
        
        # Vérifier que les fichiers existent
        for file_path in self.get_all_media_files():
            if not file_path.exists():
                errors.append(f"Fichier introuvable: {file_path}")
        
        return errors
    
    def is_valid(self) -> bool:
        """Retourne True si la chanson est valide"""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la chanson en dictionnaire pour la sauvegarde"""
        return {
            'title': self.title,
            'artist': self.artist,
            'tempo': self.tempo,
            'style': self.style,
            'path': str(self.path) if self.path else None,
            'documents': [str(doc) for doc in self.documents],
            'audios': [str(audio) for audio in self.audios],
            'videos': [str(video) for video in self.videos],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Song':
        """Crée une chanson à partir d'un dictionnaire"""
        song = cls(
            title=data.get('title', ''),
            artist=data.get('artist', ''),
            tempo=data.get('tempo', ''),
            style=data.get('style', ''),
            path=Path(data['path']) if data.get('path') else None,
            documents=[Path(doc) for doc in data.get('documents', [])],
            audios=[Path(audio) for audio in data.get('audios', [])],
            videos=[Path(video) for video in data.get('videos', [])],
            metadata=data.get('metadata', {})
        )
        return song
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Song':
        """Crée une chanson à partir d'une chaîne JSON"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_json(self) -> str:
        """Convertit la chanson en JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def __str__(self) -> str:
        """Représentation string de la chanson"""
        return self.display_name
    
    def __repr__(self) -> str:
        """Représentation détaillée pour le debug"""
        return (f"Song(title='{self.title}', artist='{self.artist}', "
                f"docs={len(self.documents)}, audios={len(self.audios)}, "
                f"videos={len(self.videos)})")


# Fonctions utilitaires pour les chansons
def create_song_from_folder(folder_path: Path, title: str = None, artist: str = None) -> Song:
    """
    Crée une chanson en analysant automatiquement un dossier
    
    Args:
        folder_path: Chemin vers le dossier contenant les médias
        title: Titre optionnel (par défaut: nom du dossier)
        artist: Artiste optionnel
    
    Returns:
        Song: Nouvelle chanson avec les médias trouvés
    """
    if not folder_path.exists() or not folder_path.is_dir():
        raise ValueError(f"Dossier invalide: {folder_path}")
    
    # Extensions supportées
    DOCUMENT_EXTENSIONS = {'.pdf', '.txt', '.doc', '.docx', '.odt', '.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma'}
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    
    # Créer la chanson
    song = Song(
        title=title or folder_path.name,
        artist=artist or "",
        path=folder_path
    )
    
    # Parcourir tous les fichiers du dossier
    for file_path in folder_path.rglob("*"):
        if file_path.is_file():
            extension = file_path.suffix.lower()
            
            if extension in DOCUMENT_EXTENSIONS:
                song.add_document(file_path)
            elif extension in AUDIO_EXTENSIONS:
                song.add_audio(file_path)
            elif extension in VIDEO_EXTENSIONS:
                song.add_video(file_path)
    
    return song