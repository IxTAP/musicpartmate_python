"""
Utilitaires pour la gestion des fichiers
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import mimetypes
import hashlib


def get_file_size_human(file_path: Path) -> str:
    """
    Retourne la taille du fichier dans un format lisible
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        str: Taille formatée (ex: "1.5 MB")
    """
    if not file_path.exists():
        return "0 B"
    
    size = file_path.stat().st_size
    
    # Unités
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def get_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """
    Calcule le hash d'un fichier
    
    Args:
        file_path: Chemin vers le fichier
        algorithm: Algorithme de hash ('md5', 'sha1', 'sha256')
        
    Returns:
        str: Hash du fichier
    """
    if not file_path.exists():
        return ""
    
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def is_file_accessible(file_path: Path) -> bool:
    """
    Vérifie si un fichier est accessible en lecture
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        bool: True si accessible
    """
    try:
        return file_path.exists() and os.access(file_path, os.R_OK)
    except Exception:
        return False


def safe_filename(filename: str, replacement: str = "_") -> str:
    """
    Nettoie un nom de fichier en supprimant les caractères dangereux
    
    Args:
        filename: Nom de fichier original
        replacement: Caractère de remplacement
        
    Returns:
        str: Nom de fichier sécurisé
    """
    # Caractères interdits dans les noms de fichiers
    forbidden_chars = '<>:"/\\|?*'
    
    clean_name = filename
    for char in forbidden_chars:
        clean_name = clean_name.replace(char, replacement)
    
    # Supprimer les espaces en début/fin
    clean_name = clean_name.strip()
    
    # Éviter les noms réservés Windows
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    if clean_name.upper() in reserved_names:
        clean_name = f"{clean_name}_{replacement}"
    
    return clean_name


def create_song_folder_structure(base_path: Path, artist: str, title: str) -> Path:
    """
    Crée la structure de dossier pour une chanson
    
    Structure: base_path/Artist/Song_Title/
    
    Args:
        base_path: Dossier de base
        artist: Nom de l'artiste
        title: Titre de la chanson
        
    Returns:
        Path: Chemin vers le dossier de la chanson
    """
    # Nettoyer les noms
    clean_artist = safe_filename(artist) if artist else "Artiste_Inconnu"
    clean_title = safe_filename(title) if title else "Titre_Inconnu"
    
    # Créer la structure
    song_folder = base_path / clean_artist / clean_title
    song_folder.mkdir(parents=True, exist_ok=True)
    
    # Créer les sous-dossiers
    (song_folder / "documents").mkdir(exist_ok=True)
    (song_folder / "audio").mkdir(exist_ok=True)
    (song_folder / "video").mkdir(exist_ok=True)
    
    return song_folder


def scan_folder_for_media(folder_path: Path, extensions: Dict[str, List[str]]) -> Dict[str, List[Path]]:
    """
    Scanne un dossier à la recherche de fichiers média
    
    Args:
        folder_path: Dossier à scanner
        extensions: Extensions supportées par type {'documents': [...], 'audio': [...], 'video': [...]}
        
    Returns:
        Dict[str, List[Path]]: Fichiers trouvés par type
    """
    result = {
        'documents': [],
        'audio': [],
        'video': [],
        'unknown': []
    }
    
    if not folder_path.exists() or not folder_path.is_dir():
        return result
    
    # Aplatir les extensions pour la recherche
    all_extensions = {}
    for media_type, ext_list in extensions.items():
        for ext in ext_list:
            all_extensions[ext.lower()] = media_type
    
    # Scanner récursivement
    for file_path in folder_path.rglob("*"):
        if file_path.is_file():
            extension = file_path.suffix.lower()
            media_type = all_extensions.get(extension, 'unknown')
            result[media_type].append(file_path)
    
    return result


def copy_file_to_song_folder(source_file: Path, song_folder: Path, media_type: str) -> Optional[Path]:
    """
    Copie un fichier dans le dossier d'une chanson
    
    Args:
        source_file: Fichier source à copier
        song_folder: Dossier de destination de la chanson
        media_type: Type de média ('documents', 'audio', 'video')
        
    Returns:
        Optional[Path]: Chemin du fichier copié ou None si erreur
    """
    if not source_file.exists():
        return None
    
    # Déterminer le dossier de destination
    if media_type == 'documents':
        dest_folder = song_folder / "documents"
    elif media_type == 'audio':
        dest_folder = song_folder / "audio"
    elif media_type == 'video':
        dest_folder = song_folder / "video"
    else:
        dest_folder = song_folder
    
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    # Gérer les doublons de noms
    dest_file = dest_folder / source_file.name
    counter = 1
    
    while dest_file.exists():
        name_parts = source_file.stem, counter, source_file.suffix
        dest_file = dest_folder / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
        counter += 1
    
    try:
        shutil.copy2(source_file, dest_file)
        return dest_file
    except Exception as e:
        print(f"Erreur lors de la copie de {source_file}: {e}")
        return None


def move_file_to_song_folder(source_file: Path, song_folder: Path, media_type: str) -> Optional[Path]:
    """
    Déplace un fichier dans le dossier d'une chanson
    
    Args:
        source_file: Fichier source à déplacer
        song_folder: Dossier de destination de la chanson
        media_type: Type de média ('documents', 'audio', 'video')
        
    Returns:
        Optional[Path]: Chemin du fichier déplacé ou None si erreur
    """
    dest_file = copy_file_to_song_folder(source_file, song_folder, media_type)
    
    if dest_file:
        try:
            source_file.unlink()  # Supprimer le fichier source
            return dest_file
        except Exception as e:
            print(f"Erreur lors de la suppression de {source_file}: {e}")
            # Le fichier a été copié mais pas supprimé
            return dest_file
    
    return None


def get_mime_type(file_path: Path) -> str:
    """
    Retourne le type MIME d'un fichier
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        str: Type MIME
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


def is_image_file(file_path: Path) -> bool:
    """Vérifie si un fichier est une image"""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
    return file_path.suffix.lower() in image_extensions


def is_audio_file(file_path: Path) -> bool:
    """Vérifie si un fichier est un audio"""
    audio_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma'}
    return file_path.suffix.lower() in audio_extensions


def is_video_file(file_path: Path) -> bool:
    """Vérifie si un fichier est une vidéo"""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    return file_path.suffix.lower() in video_extensions


def is_document_file(file_path: Path) -> bool:
    """Vérifie si un fichier est un document"""
    document_extensions = {'.pdf', '.txt', '.doc', '.docx', '.odt', '.rtf'}
    return file_path.suffix.lower() in document_extensions


def cleanup_empty_folders(base_path: Path) -> int:
    """
    Supprime les dossiers vides récursivement
    
    Args:
        base_path: Dossier de base à nettoyer
        
    Returns:
        int: Nombre de dossiers supprimés
    """
    deleted_count = 0
    
    if not base_path.exists() or not base_path.is_dir():
        return 0
    
    # Parcourir de bas en haut pour supprimer les dossiers vides
    for folder_path in sorted(base_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if folder_path.is_dir():
            try:
                folder_path.rmdir()  # Ne fonctionne que si le dossier est vide
                deleted_count += 1
            except OSError:
                # Dossier non vide, on continue
                pass
    
    return deleted_count


def find_duplicate_files(folder_path: Path) -> Dict[str, List[Path]]:
    """
    Trouve les fichiers dupliqués dans un dossier
    
    Args:
        folder_path: Dossier à analyser
        
    Returns:
        Dict[str, List[Path]]: Hash -> Liste des fichiers avec ce hash
    """
    file_hashes = {}
    
    if not folder_path.exists() or not folder_path.is_dir():
        return {}
    
    for file_path in folder_path.rglob("*"):
        if file_path.is_file():
            file_hash = get_file_hash(file_path)
            if file_hash:
                if file_hash not in file_hashes:
                    file_hashes[file_hash] = []
                file_hashes[file_hash].append(file_path)
    
    # Retourner seulement les hash avec plusieurs fichiers
    duplicates = {h: files for h, files in file_hashes.items() if len(files) > 1}
    return duplicates


def validate_file_structure(song_folder: Path) -> Tuple[bool, List[str]]:
    """
    Valide la structure d'un dossier de chanson
    
    Args:
        song_folder: Dossier de la chanson à valider
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_des_erreurs)
    """
    errors = []
    
    if not song_folder.exists():
        errors.append(f"Le dossier {song_folder} n'existe pas")
        return False, errors
    
    if not song_folder.is_dir():
        errors.append(f"{song_folder} n'est pas un dossier")
        return False, errors
    
    # Vérifier la présence des sous-dossiers recommandés
    recommended_folders = ['documents', 'audio', 'video']
    for folder_name in recommended_folders:
        folder_path = song_folder / folder_name
        if not folder_path.exists():
            # Pas une erreur, juste une recommandation
            pass
    
    # Vérifier qu'il y a au moins un fichier média
    has_media = False
    for file_path in song_folder.rglob("*"):
        if file_path.is_file():
            if (is_document_file(file_path) or 
                is_audio_file(file_path) or 
                is_video_file(file_path) or
                is_image_file(file_path)):
                has_media = True
                break
    
    if not has_media:
        errors.append("Aucun fichier média trouvé dans le dossier")
    
    return len(errors) == 0, errors


def get_folder_statistics(folder_path: Path) -> Dict[str, int]:
    """
    Retourne des statistiques sur un dossier
    
    Args:
        folder_path: Dossier à analyser
        
    Returns:
        Dict[str, int]: Statistiques
    """
    stats = {
        'total_files': 0,
        'total_folders': 0,
        'documents': 0,
        'audio': 0,
        'video': 0,
        'images': 0,
        'other': 0,
        'total_size': 0
    }
    
    if not folder_path.exists() or not folder_path.is_dir():
        return stats
    
    for item_path in folder_path.rglob("*"):
        if item_path.is_file():
            stats['total_files'] += 1
            stats['total_size'] += item_path.stat().st_size
            
            if is_document_file(item_path):
                stats['documents'] += 1
            elif is_audio_file(item_path):
                stats['audio'] += 1
            elif is_video_file(item_path):
                stats['video'] += 1
            elif is_image_file(item_path):
                stats['images'] += 1
            else:
                stats['other'] += 1
                
        elif item_path.is_dir():
            stats['total_folders'] += 1
    
    return stats


def create_media_symlinks(source_folder: Path, target_folder: Path) -> Dict[str, int]:
    """
    Crée des liens symboliques vers les fichiers média
    Utile pour organiser sans dupliquer les fichiers
    
    Args:
        source_folder: Dossier source contenant les médias
        target_folder: Dossier cible pour les liens
        
    Returns:
        Dict[str, int]: Nombre de liens créés par type
    """
    links_created = {
        'documents': 0,
        'audio': 0,
        'video': 0,
        'images': 0,
        'errors': 0
    }
    
    if not source_folder.exists():
        return links_created
    
    target_folder.mkdir(parents=True, exist_ok=True)
    
    for file_path in source_folder.rglob("*"):
        if file_path.is_file():
            try:
                # Déterminer le type et le dossier cible
                if is_document_file(file_path):
                    subfolder = target_folder / "documents"
                    links_created['documents'] += 1
                elif is_audio_file(file_path):
                    subfolder = target_folder / "audio"
                    links_created['audio'] += 1
                elif is_video_file(file_path):
                    subfolder = target_folder / "video"
                    links_created['video'] += 1
                elif is_image_file(file_path):
                    subfolder = target_folder / "images"
                    links_created['images'] += 1
                else:
                    continue  # Ignorer les autres types
                
                subfolder.mkdir(exist_ok=True)
                link_path = subfolder / file_path.name
                
                # Éviter les doublons
                counter = 1
                while link_path.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    link_path = subfolder / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Créer le lien symbolique
                link_path.symlink_to(file_path.absolute())
                
            except Exception as e:
                print(f"Erreur lors de la création du lien pour {file_path}: {e}")
                links_created['errors'] += 1
    
    return links_created