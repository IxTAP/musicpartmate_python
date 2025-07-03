# 🎵 MusicPartMate

Un gestionnaire de partitions musicales moderne avec support multimédia complet.

## 📋 Fonctionnalités

### 📄 Lecture universelle de documents
- **PDF** : Affichage page par page avec zoom
- **Documents texte** : TXT, DOC, DOCX, ODT
- **Images** : PNG, JPG, JPEG, GIF, BMP
- Navigation intuitive et contrôles de zoom

### 🎵 Lecteur multimédia intégré
- **Audio** : MP3, WAV, FLAC, OGG, M4A, AAC
- **Vidéo** : MP4, AVI, MOV, MKV, WMV
- Contrôles complets (play/pause, position, volume, vitesse)
- Support des liens YouTube

### 📚 Gestion de bibliothèque
- Organisation par artiste et titre
- Métadonnées extensibles (tempo, style, notes personnelles)
- Validation automatique des données
- Sauvegarde automatique avec backups

### 🔍 Recherche avancée
- Recherche par titre, artiste, style
- Filtrage en temps réel
- Résultats organisés et faciles à naviguer

### 📁 Import/Export
- Import automatique depuis dossiers
- Détection intelligente des types de médias
- Export en JSON ou CSV
- Structure de dossiers flexible

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation des dépendances

```bash
# Cloner ou télécharger le projet
cd musicpartmate

# Installer les dépendances
pip install -r requirements.txt
```

### Dépendances principales
- **PyQt6** : Interface graphique moderne
- **PyMuPDF** : Lecture de fichiers PDF
- **python-docx** : Support des fichiers Word
- **Pillow** : Traitement d'images

## 🎯 Utilisation

### Démarrage
```bash
python main.py
```

### Première utilisation

1. **Créer une nouvelle chanson** : Cliquez sur "Nouveau" dans la barre d'outils
2. **Remplir les informations** : Titre, artiste, tempo, style
3. **Ajouter des médias** : Glissez-déposez ou utilisez "Ajouter des fichiers"
4. **Sauvegarder** : La chanson est automatiquement ajoutée à la bibliothèque

### Import en masse
1. **Importer un dossier** : Menu Fichier > Importer
2. **Sélectionner le dossier** contenant vos chansons
3. **Validation automatique** : L'application détecte et importe les médias

### Navigation
- **Clic sur une chanson** : Charge le premier document
- **Clic sur un média** : Charge le document/audio/vidéo spécifique
- **Recherche** : Utilisez la barre de recherche en haut

## 📁 Structure du projet

```
musicpartmate/
├── main.py                 # Point d'entrée
├── requirements.txt        # Dépendances
├── README.md              # Cette documentation
├── config.json            # Configuration (créé automatiquement)
│
├── src/                   # Code source
│   ├── models/            # Modèles de données
│   │   ├── song.py        # Classe Song
│   │   └── library.py     # Gestionnaire de bibliothèque
│   │
│   ├── ui/                # Interface utilisateur
│   │   ├── main_window.py      # Fenêtre principale
│   │   ├── document_viewer.py  # Visionneuse de documents
│   │   ├── media_player.py     # Lecteur multimédia
│   │   └── song_dialog.py      # Dialog d'édition
│   │
│   └── utils/             # Utilitaires
│       ├── config.py           # Configuration
│       └── file_utils.py       # Gestion des fichiers
│
├── data/                  # Données utilisateur
│   ├── library.json       # Bibliothèque
│   └── backups/           # Sauvegardes automatiques
│
└── tests/                 # Tests (à développer)
```

## 🔧 Configuration

Le fichier `config.json` est créé automatiquement au premier lancement. Vous pouvez modifier :

```json
{
  "window_width": 1200,
  "window_height": 800,
  "auto_backup": true,
  "backup_count": 5,
  "theme": "default"
}
```

## 📝 Format de données

### Structure d'une chanson
```json
{
  "title": "Ma Chanson",
  "artist": "Mon Artiste",
  "tempo": "120 BPM",
  "style": "Rock",
  "documents": ["partition.pdf", "accords.txt"],
  "audios": ["original.mp3", "backing.wav"],
  "videos": ["live.mp4"],
  "metadata": {
    "notes": "Notes personnelles",
    "difficulte": "Intermédiaire",
    "tonalite": "Do majeur"
  }
}
```

## 🎨 Personnalisation

### Formats supportés
Vous pouvez étendre les formats supportés en modifiant `src/utils/config.py` :

```python
document_formats: list = ['.pdf', '.txt', '.doc', '.docx', '.odt']
audio_formats: list = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
video_formats: list = ['.mp4', '.avi', '.mov', '.mkv']
```

### Thèmes
Le support des thèmes est préparé pour les futures versions (dark mode, etc.)

## 🔍 Recherche et filtres

- **Recherche globale** : Cherche dans titre, artiste et style
- **Filtres spécifiques** : Par titre, artiste ou style uniquement
- **Recherche en temps réel** : Résultats instantanés lors de la frappe

## 💾 Sauvegarde et backup

- **Sauvegarde automatique** : À chaque modification
- **Backups rotatifs** : Conservation des 5 dernières versions
- **Export** : JSON pour la compatibilité, CSV pour l'analyse

## 🔧 Dépannage

### Problèmes courants

**L'application ne démarre pas :**
```bash
# Vérifier Python et les dépendances
python --version  # Doit être 3.8+
pip list | grep PyQt6
```

**Fichiers PDF non supportés :**
```bash
# Réinstaller PyMuPDF
pip uninstall PyMuPDF
pip install PyMuPDF
```

**Problèmes audio/vidéo :**
- Vérifiez que les codecs sont installés sur votre système
- Certains formats peuvent nécessiter des codecs supplémentaires

### Logs et debugging
Les erreurs sont affichées dans la console. Pour plus de détails :
```bash
python main.py 2>&1 | tee debug.log
```

## 🚀 Fonctionnalités futures

### Version 1.1 (planifiée)
- [ ] Synchronisation cloud (Google Drive, Dropbox, pCloud)
- [ ] Playlists et collections
- [ ] Export vers formats musicaux (MusicXML)
- [ ] Thème sombre

### Version 1.2 (prévue)
- [ ] Support tablatures (GP5, GPX)
- [ ] Métronome intégré
- [ ] Annotations sur les partitions
- [ ] Mode plein écran pour les performances

### Long terme
- [ ] Application mobile (Qt for Mobile)
- [ ] Synchronisation multi-appareils
- [ ] Collaboration en ligne
- [ ] IA pour la reconnaissance de partitions

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment participer :

1. **Fork** le projet
2. **Créer une branche** pour votre fonctionnalité
3. **Commiter** vos changements
4. **Pousser** vers la branche
5. **Créer une Pull Request**

### Guidelines de développement
- Code en anglais, commentaires en français acceptés
- Suivre PEP 8 pour le style Python
- Ajouter des tests pour les nouvelles fonctionnalités
- Documenter les API publiques

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- **PyQt6** pour l'interface graphique moderne
- **PyMuPDF** pour le support PDF excellent
- **FFmpeg** pour les capacités multimédia
- La communauté Python pour l'écosystème fantastique

## 📞 Support

- **Issues GitHub** : Pour les bugs et demandes de fonctionnalités
- **Documentation** : Ce README et les docstrings dans le code
- **Community** : Discussions dans les issues GitHub

---

**Bon voyage musical avec MusicPartMate ! 🎵**