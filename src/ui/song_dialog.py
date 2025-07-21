"""
Dialog pour créer et éditer les chansons (PySide6)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QTextEdit, QListWidget, QListWidgetItem, QSplitter,
    QGroupBox, QFileDialog, QMessageBox, QLabel, QFrame, QTabWidget,
    QWidget, QScrollArea, QGridLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path
from typing import Optional, List
import json

from ..models.song import Song
from ..utils.config import config_manager, get_supported_formats
from ..utils.file_utils import scan_folder_for_media, get_file_size_human

class LinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un lien")
        self.setModal(True)
        self.resize(400, 150)
        
        # Layout principal
        layout = QVBoxLayout()
        
        # Champ pour le titre
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Titre:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Entrez le titre du lien")
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # Champ pour l'URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Boutons OK/Annuler
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Focus sur le champ titre au démarrage
        self.title_input.setFocus()
    
    def get_link_data(self):
        """Retourne les données saisies sous forme de dictionnaire"""
        return {
            'title': self.title_input.text().strip(),
            'url': self.url_input.text().strip()
        }

class MediaListWidget(QListWidget):
    """Widget personnalisé pour afficher la liste des médias"""
    
    files_dropped = Signal(list)  # Signal émis quand des fichiers sont déposés
    
    def __init__(self, media_type: str):
        super().__init__()
        self.media_type = media_type
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        
        # Style
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 5px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        # Message par défaut
        self.update_placeholder()
    
    def update_placeholder(self):
        """Met à jour le message de placeholder"""
        if self.count() == 0:
            placeholder_text = {
                'documents': "📄 Glissez des documents ici\n(PDF, DOC, TXT, images...)",
                'audio': "🎵 Glissez des fichiers audio ici\n(MP3, WAV, FLAC...)",
                'video': "🎬 Glissez des vidéos ici\n(MP4, AVI, MOV...)",
                'link': "Glissez des liens ici\n(Youtube...)"
            }
            
            placeholder = QListWidgetItem(placeholder_text.get(self.media_type, "Glissez des fichiers ici"))
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)  # Non sélectionnable
            placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.addItem(placeholder)
    
    def add_file(self, file_path: Path):
        """Ajoute un fichier à la liste"""
        # Supprimer le placeholder s'il existe
        if self.count() == 1:
            item = self.item(0)
            if not item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.clear()
        
        # Créer l'élément
        file_size = get_file_size_human(file_path)
        item_text = f"{file_path.name}\n{file_size}"
        
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        
        # Icône selon le type
        if self.media_type == 'documents':
            item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
        elif self.media_type == 'audio':
            item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaVolume))
        else:  # video
            item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
        
        self.addItem(item)

    def add_link(self, file_path: str):
        """Ajoute un fichier à la liste"""
        # Supprimer le placeholder s'il existe
        if self.count() == 1:
            item = self.item(0)
            if not item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.clear()
        
        # Créer l'élément
        item_text = f"{file_path}"
        
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        
        # Icône selon le type
        item.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
        
        self.addItem(item)

    def remove_selected(self):
        """Supprime les éléments sélectionnés"""
        for item in self.selectedItems():
            row = self.row(item)
            self.takeItem(row)
        
        self.update_placeholder()
    
    def get_links(self) -> List[str]:
        links = []
        for i in range(self.count()):
            item = self.item(i)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path:  # Ignorer le placeholder
                links.append(file_path)
        return links

    def get_files(self) -> List[Path]:
        """Retourne la liste des fichiers"""
        files = []
        for i in range(self.count()):
            item = self.item(i)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path:  # Ignorer le placeholder
                files.append(file_path)
        return files
    
    def clear_files(self):
        """Vide la liste"""
        self.clear()
        self.update_placeholder()
    
    def dragEnterEvent(self, event):
        """Gère l'entrée du drag"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Gère le drop des fichiers"""
        urls = event.mimeData().urls()
        files = []
        
        for url in urls:
            if url.isLocalFile():
                file_path = Path(url.toLocalFile())
                if file_path.is_file():
                    files.append(file_path)
        
        if files:
            self.files_dropped.emit(files)
        
        event.acceptProposedAction()


class SongDialog(QDialog):
    """Dialog pour créer/éditer une chanson"""
    
    def __init__(self, song: Optional[Song] = None, parent=None):
        super().__init__(parent)
        self.song = song or Song()
        self.is_editing = song is not None
        
        self.setup_ui()
        self.load_song_data()
        
        # Connecter les signaux
        self.setup_connections()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        title = "Éditer la chanson" if self.is_editing else "Nouvelle chanson"
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Onglets
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Onglet Informations
        self.create_info_tab()
        
        # Onglet Médias
        self.create_media_tab()
        
        # Onglet Métadonnées
        self.create_metadata_tab()
        
        # Boutons
        self.create_buttons(layout)
    
    def create_info_tab(self):
        """Crée l'onglet des informations de base"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Formulaire principal
        form_layout = QFormLayout()
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Titre de la chanson")
        form_layout.addRow("Titre *:", self.title_edit)
        
        self.artist_edit = QLineEdit()
        self.artist_edit.setPlaceholderText("Nom de l'artiste")
        form_layout.addRow("Artiste *:", self.artist_edit)
        
        self.tempo_edit = QLineEdit()
        self.tempo_edit.setPlaceholderText("ex: 120 BPM")
        form_layout.addRow("Tempo:", self.tempo_edit)
        
        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("ex: Rock, Jazz, Classique...")
        form_layout.addRow("Style:", self.style_edit)
        
        layout.addLayout(form_layout)
        
        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes personnelles sur cette chanson...")
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)
        
        layout.addWidget(notes_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📝 Informations")
    
    def create_media_tab(self):
        """Crée l'onglet de gestion des médias"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        self.add_files_button = QPushButton("📁 Ajouter des fichiers")
        self.add_files_button.clicked.connect(self.add_files)
        buttons_layout.addWidget(self.add_files_button)

        self.add_links_button = QPushButton("📁 Ajouter des liens")
        self.add_links_button.clicked.connect(self.open_link_dialog)
        buttons_layout.addWidget(self.add_links_button)
        
        self.import_folder_button = QPushButton("📂 Importer un dossier")
        self.import_folder_button.clicked.connect(self.import_folder)
        buttons_layout.addWidget(self.import_folder_button)
        
        buttons_layout.addStretch()
        
        self.remove_selected_button = QPushButton("🗑️ Supprimer sélection")
        self.remove_selected_button.clicked.connect(self.remove_selected_media)
        buttons_layout.addWidget(self.remove_selected_button)
        
        layout.addLayout(buttons_layout)
        
        # Splitter pour les trois types de médias
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Documents
        docs_group = QGroupBox("Documents")
        docs_layout = QVBoxLayout(docs_group)
        self.documents_list = MediaListWidget('documents')
        self.documents_list.files_dropped.connect(self.on_documents_dropped)
        docs_layout.addWidget(self.documents_list)
        splitter.addWidget(docs_group)
        
        # Audio
        audio_group = QGroupBox("Audio")
        audio_layout = QVBoxLayout(audio_group)
        self.audio_list = MediaListWidget('audio')
        self.audio_list.files_dropped.connect(self.on_audio_dropped)
        audio_layout.addWidget(self.audio_list)
        splitter.addWidget(audio_group)
        
        # Vidéo
        video_group = QGroupBox("Vidéo")
        video_layout = QVBoxLayout(video_group)
        self.video_list = MediaListWidget('video')
        self.video_list.files_dropped.connect(self.on_video_dropped)
        video_layout.addWidget(self.video_list)
        splitter.addWidget(video_group)

        # Liens
        link_group = QGroupBox("Lien")
        link_layout = QVBoxLayout(link_group)
        self.link_list = MediaListWidget('link')
        self.link_list.files_dropped.connect(self.on_video_dropped)
        link_layout.addWidget(self.link_list)
        splitter.addWidget(link_group)
        
        # Répartition égale
        splitter.setSizes([250, 250, 250, 250])
        
        self.tab_widget.addTab(tab, "🎵 Médias")
    
    def create_metadata_tab(self):
        """Crée l'onglet des métadonnées avancées"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Zone de scroll pour les métadonnées
        scroll = QScrollArea()
        scroll_widget = QWidget()
        self.metadata_layout = QGridLayout(scroll_widget)
        
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Boutons pour gérer les métadonnées
        meta_buttons = QHBoxLayout()
        
        self.add_metadata_button = QPushButton("➕ Ajouter métadonnée")
        self.add_metadata_button.clicked.connect(self.add_metadata_field)
        meta_buttons.addWidget(self.add_metadata_button)
        
        meta_buttons.addStretch()
        
        layout.addLayout(meta_buttons)
        
        # Charger les métadonnées existantes
        self.metadata_fields = {}
        
        self.tab_widget.addTab(tab, "⚙️ Métadonnées")
    
    def create_buttons(self, parent_layout):
        """Crée les boutons de validation"""
        buttons_frame = QFrame()
        buttons_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        buttons_layout = QHBoxLayout(buttons_frame)
        
        # Validation (sera mis à jour après)
        self.validation_label = QLabel()
        buttons_layout.addWidget(self.validation_label)
        
        buttons_layout.addStretch()
        
        # Boutons d'action
        self.save_button = QPushButton("💾 Sauvegarder")
        self.save_button.clicked.connect(self.save_song)
        buttons_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("❌ Annuler")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        parent_layout.addWidget(buttons_frame)
        
        # Maintenant on peut valider le formulaire
        self.update_validation_status()
    
    def setup_connections(self):
        """Configure les connexions de signaux"""
        # Validation en temps réel
        self.title_edit.textChanged.connect(self.update_validation_status)
        self.artist_edit.textChanged.connect(self.update_validation_status)
    
    def load_song_data(self):
        """Charge les données de la chanson dans le formulaire"""
        if not self.song:
            return
        
        # Informations de base
        self.title_edit.setText(self.song.title)
        self.artist_edit.setText(self.song.artist)
        self.tempo_edit.setText(self.song.tempo)
        self.style_edit.setText(self.song.style)
        
        # Notes
        notes = self.song.metadata.get('notes', '')
        self.notes_edit.setPlainText(notes)
        
        # Médias
        for doc in self.song.documents:
            self.documents_list.add_file(doc)
        
        for audio in self.song.audios:
            self.audio_list.add_file(audio)
        
        for video in self.song.videos:
            self.video_list.add_file(video)

        for link in self.song.links:
            self.link_list.add_link(link)
        
        # Métadonnées
        for key, value in self.song.metadata.items():
            if key != 'notes':  # Les notes sont gérées séparément
                # S'assurer que key et value sont des chaînes
                key_str = str(key) if key is not None else ""
                value_str = str(value) if value is not None else ""
                self.add_metadata_field(key_str, value_str)
    
    def validate_form(self):
        """Valide le formulaire et met à jour l'interface"""
        is_valid = True
        
        # Vérifier les champs obligatoires
        if not self.title_edit.text().strip() and not self.artist_edit.text().strip():
            is_valid = False
        
        # Vérifier qu'il y a au moins un média
        has_media = (len(self.documents_list.get_files()) > 0 or
                    len(self.audio_list.get_files()) > 0 or
                    len(self.video_list.get_files()) > 0 or
                    len(self.link_list.get_links()) > 0)
        
        if not has_media:
            is_valid = False
        
        # Activer/désactiver le bouton de sauvegarde
        self.save_button.setEnabled(is_valid)
        
        return is_valid
    
    def update_validation_status(self):
        """Met à jour le statut de validation"""
        if not hasattr(self, 'validation_label'):
            return
            
        if self.validate_form():
            self.validation_label.setText("✅ Prêt à sauvegarder")
            self.validation_label.setStyleSheet("color: green;")
        else:
            self.validation_label.setText("⚠️ Titre/Artiste et au moins un média requis")
            self.validation_label.setStyleSheet("color: orange;")
    
    def open_link_dialog(self):
        """Ouvre la fenêtre contextuelle pour ajouter un lien"""
        dialog = LinkDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            link_data = dialog.get_link_data()
            
            # Vérification basique
            if link_data['title'] and link_data['url']:
                # Ajouter le lien à la liste
                self.link_list.add_link(link_data['url'])
                self.validate_form()
                self.update_validation_status()
                print(f"Lien ajouté: {link_data['title']} -> {link_data['url']}")
            else:
                print("Erreur: Titre et URL sont requis")

    def add_files(self):
        """Ouvre un dialog pour ajouter des fichiers"""
        formats = get_supported_formats()
        all_formats = []
        for format_list in formats.values():
            all_formats.extend(format_list)
        
        filter_str = "Tous les médias supportés (" + " ".join([f"*{ext}" for ext in all_formats]) + ")"
        filter_str += ";;Documents (" + " ".join([f"*{ext}" for ext in formats['documents']]) + ")"
        filter_str += ";;Audio (" + " ".join([f"*{ext}" for ext in formats['audio']]) + ")"
        filter_str += ";;Vidéo (" + " ".join([f"*{ext}" for ext in formats['video']]) + ")"
        filter_str += ";;Tous les fichiers (*)"
        
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Ajouter des fichiers",
            "",
            filter_str
        )
        
        if files:
            self.process_files([Path(f) for f in files])
            self.update_validation_status()  # Mettre à jour après ajout
    
    def import_folder(self):
        """Importe tous les médias d'un dossier"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Sélectionner un dossier à importer"
        )
        
        if folder:
            folder_path = Path(folder)
            formats = get_supported_formats()
            media_files = scan_folder_for_media(folder_path, formats)
            
            # Ajouter les fichiers trouvés
            for doc in media_files['documents']:
                self.documents_list.add_file(doc)
            
            for audio in media_files['audio']:
                self.audio_list.add_file(audio)
            
            for video in media_files['video']:
                self.video_list.add_file(video)
            
            # Afficher un résumé
            total_files = len(media_files['documents']) + len(media_files['audio']) + len(media_files['video'])
            if total_files > 0:
                QMessageBox.information(
                    self,
                    "Import terminé",
                    f"Importé {total_files} fichiers:\n"
                    f"• {len(media_files['documents'])} documents\n"
                    f"• {len(media_files['audio'])} audios\n"
                    f"• {len(media_files['video'])} vidéos"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Aucun fichier",
                    "Aucun fichier média supporté trouvé dans ce dossier."
                )
            
            self.validate_form()
            self.update_validation_status()  # Mettre à jour l'affichage
    
    def process_files(self, files: List[Path]):
        """Traite une liste de fichiers et les ajoute aux bonnes listes"""
        for file_path in files:
            media_type = config_manager.is_supported_media(file_path)
            
            if media_type == 'document':
                self.documents_list.add_file(file_path)
            elif media_type == 'audio':
                self.audio_list.add_file(file_path)
            elif media_type == 'video':
                self.video_list.add_file(file_path)
        
        self.validate_form()
        self.update_validation_status()  # Mettre à jour l'affichage
    
    def on_documents_dropped(self, files: List[Path]):
        """Gère les fichiers déposés sur la liste des documents"""
        for file_path in files:
            if config_manager.is_supported_document(file_path):
                self.documents_list.add_file(file_path)
        self.validate_form()
        self.update_validation_status()  # Mettre à jour l'affichage
    
    def on_audio_dropped(self, files: List[Path]):
        """Gère les fichiers déposés sur la liste audio"""
        for file_path in files:
            if config_manager.is_supported_audio(file_path):
                self.audio_list.add_file(file_path)
        self.validate_form()
        self.update_validation_status()  # Mettre à jour l'affichage
    
    def on_video_dropped(self, files: List[Path]):
        """Gère les fichiers déposés sur la liste vidéo"""
        for file_path in files:
            if config_manager.is_supported_video(file_path):
                self.video_list.add_file(file_path)
        self.validate_form()
        self.update_validation_status()  # Mettre à jour l'affichage
    
    def remove_selected_media(self):
        """Supprime les médias sélectionnés"""
        # Trouver quelle liste a des éléments sélectionnés
        if self.documents_list.selectedItems():
            self.documents_list.remove_selected()
        elif self.audio_list.selectedItems():
            self.audio_list.remove_selected()
        elif self.video_list.selectedItems():
            self.video_list.remove_selected()
        
        self.validate_form()
        self.update_validation_status()  # Mettre à jour l'affichage
    
    def add_metadata_field(self, key: str = "", value: str = ""):
        """Ajoute un champ de métadonnées"""
        row = self.metadata_layout.rowCount()
        
        # S'assurer que key et value sont des chaînes
        key = str(key) if key is not None else ""
        value = str(value) if value is not None else ""
        
        # Champ clé
        key_edit = QLineEdit()
        key_edit.setText(key)
        key_edit.setPlaceholderText("Nom de la métadonnée")
        
        # Champ valeur
        value_edit = QLineEdit()
        value_edit.setText(value)
        value_edit.setPlaceholderText("Valeur")
        
        # Bouton de suppression
        remove_button = QPushButton("🗑️")
        remove_button.setMaximumWidth(30)
        remove_button.clicked.connect(lambda: self.remove_metadata_field(row))
        
        # Ajouter à la grille
        self.metadata_layout.addWidget(key_edit, row, 0)
        self.metadata_layout.addWidget(value_edit, row, 1)
        self.metadata_layout.addWidget(remove_button, row, 2)
        
        # Stocker les références
        self.metadata_fields[row] = (key_edit, value_edit, remove_button)
    
    def remove_metadata_field(self, row: int):
        """Supprime un champ de métadonnées"""
        if row in self.metadata_fields:
            key_edit, value_edit, remove_button = self.metadata_fields[row]
            
            # Supprimer les widgets
            key_edit.setParent(None)
            value_edit.setParent(None)
            remove_button.setParent(None)
            
            # Supprimer de la liste
            del self.metadata_fields[row]
    
    def collect_metadata(self) -> dict:
        """Collecte toutes les métadonnées du formulaire"""
        metadata = {}
        
        # Notes
        notes = self.notes_edit.toPlainText().strip()
        if notes:
            metadata['notes'] = notes
        
        # Métadonnées personnalisées
        for key_edit, value_edit, _ in self.metadata_fields.values():
            key = key_edit.text().strip()
            value = value_edit.text().strip()
            
            if key and value:
                metadata[key] = value
        
        return metadata
    
    def save_song(self):
        """Sauvegarde les données de la chanson"""
        if not self.validate_form():
            QMessageBox.warning(
                self,
                "Formulaire invalide",
                "Veuillez remplir tous les champs obligatoires et ajouter au moins un média."
            )
            return
        
        # Mettre à jour les données de base
        self.song.title = self.title_edit.text().strip()
        self.song.artist = self.artist_edit.text().strip()
        self.song.tempo = self.tempo_edit.text().strip()
        self.song.style = self.style_edit.text().strip()
        
        # Mettre à jour les listes de médias
        self.song.documents = self.documents_list.get_files()
        self.song.audios = self.audio_list.get_files()
        self.song.videos = self.video_list.get_files()
        self.song.links = self.link_list.get_links()
        
        # Mettre à jour les métadonnées
        self.song.metadata = self.collect_metadata()
        
        # Validation finale
        validation_errors = self.song.validate()
        if validation_errors:
            QMessageBox.warning(
                self,
                "Erreur de validation",
                "Erreurs détectées:\n" + "\n".join(validation_errors)
            )
            return
        
        # Confirmer la sauvegarde
        self.accept()
    
    def keyPressEvent(self, event):
        """Gère les raccourcis clavier"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self.save_button.isEnabled():
                self.save_song()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)