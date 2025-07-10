"""
Fenêtre principale de l'application MusicPartMate (PySide6)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QToolBar, QMenuBar, QStatusBar,
    QMessageBox, QFileDialog, QInputDialog, QProgressDialog,
    QLabel, QLineEdit, QPushButton, QComboBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QAction, QIcon, QKeySequence
from pathlib import Path
from typing import Optional, List
import json
import time

from ..models.song import Song, create_song_from_folder
from ..models.library import Library, LibraryConfig
from ..utils.config import config_manager, get_supported_formats
from ..utils.file_utils import scan_folder_for_media, get_folder_statistics
from .document_viewer import DocumentViewer
from .media_player import MediaPlayer
from .song_dialog import SongDialog


class ImportWorker(QThread):
    """Worker thread pour l'import de chansons en arrière-plan"""
    
    progress_updated = Signal(int, str)  # Progression, message
    song_imported = Signal(object)       # Chanson importée
    import_finished = Signal(int, int)   # Succès, erreurs
    
    def __init__(self, folder_paths: List[Path]):
        super().__init__()
        self.folder_paths = folder_paths
        self.should_stop = False
    
    def stop(self):
        """Arrête l'import"""
        self.should_stop = True
    
    def run(self):
        """Effectue l'import en arrière-plan"""
        success_count = 0
        error_count = 0
        total_folders = len(self.folder_paths)
        
        for i, folder_path in enumerate(self.folder_paths):
            if self.should_stop:
                break
            
            try:
                # Mettre à jour la progression
                self.progress_updated.emit(
                    int((i / total_folders) * 100),
                    f"Import: {folder_path.name}"
                )
                
                # Créer la chanson depuis le dossier
                song = create_song_from_folder(folder_path)
                
                if song.is_valid():
                    self.song_imported.emit(song)
                    success_count += 1
                else:
                    error_count += 1
                
                # Petite pause pour éviter de bloquer l'interface
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Erreur lors de l'import de {folder_path}: {e}")
                error_count += 1
        
        self.import_finished.emit(success_count, error_count)


class LibraryTreeWidget(QTreeWidget):
    """Widget arbre personnalisé pour la bibliothèque"""
    
    song_selected = Signal(object)          # Chanson sélectionnée
    media_selected = Signal(str, object)    # Type de média, fichier
    
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Bibliothèque"])
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self.on_item_clicked)
        
        # Menu contextuel
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Gère les clics sur les éléments"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(data, Song):
            # Chanson sélectionnée
            self.song_selected.emit(data)
        elif isinstance(data, tuple) and len(data) == 2:
            # Média spécifique sélectionné
            media_type, file_path = data
            self.media_selected.emit(media_type, file_path)
    
    def show_context_menu(self, position):
        """Affiche le menu contextuel"""
        item = self.itemAt(position)
        if not item:
            return
        
        # TODO: Implémenter le menu contextuel
        pass
    
    def load_library(self, library: Library):
        """Charge la bibliothèque dans l'arbre"""
        self.clear()
        
        # Grouper par artiste
        artists_items = {}
        
        for song in library.get_songs_sorted('artist'):
            artist = song.artist or "Artiste inconnu"
            
            # Créer l'élément artiste si nécessaire
            if artist not in artists_items:
                artist_item = QTreeWidgetItem([f"🎤 {artist}"])
                artist_item.setExpanded(True)
                self.addTopLevelItem(artist_item)
                artists_items[artist] = artist_item
            
            # Ajouter la chanson
            song_item = QTreeWidgetItem([f"🎵 {song.title}"])
            song_item.setData(0, Qt.ItemDataRole.UserRole, song)
            artists_items[artist].addChild(song_item)
            
            # Ajouter les médias
            if song.documents:
                docs_item = QTreeWidgetItem(["📄 Documents"])
                for doc in song.documents:
                    doc_item = QTreeWidgetItem([doc.name])
                    doc_item.setData(0, Qt.ItemDataRole.UserRole, ("document", doc))
                    docs_item.addChild(doc_item)
                song_item.addChild(docs_item)
            
            if song.audios:
                audio_item = QTreeWidgetItem(["🎵 Audio"])
                for audio in song.audios:
                    audio_child = QTreeWidgetItem([audio.name])
                    audio_child.setData(0, Qt.ItemDataRole.UserRole, ("audio", audio))
                    audio_item.addChild(audio_child)
                song_item.addChild(audio_item)
            
            if song.videos:
                video_item = QTreeWidgetItem(["🎬 Vidéos"])
                for video in song.videos:
                    video_child = QTreeWidgetItem([video.name])
                    video_child.setData(0, Qt.ItemDataRole.UserRole, ("video", video))
                    video_item.addChild(video_child)
                song_item.addChild(video_item)
            
            # Métadonnées
            if song.tempo or song.style or song.metadata:
                meta_item = QTreeWidgetItem(["⚙️ Métadonnées"])
                
                if song.tempo:
                    meta_child = QTreeWidgetItem([f"Tempo: {song.tempo}"])
                    meta_item.addChild(meta_child)
                
                if song.style:
                    meta_child = QTreeWidgetItem([f"Style: {song.style}"])
                    meta_item.addChild(meta_child)
                
                for key, value in song.metadata.items():
                    if key != 'notes':  # Les notes ne s'affichent pas ici
                        meta_child = QTreeWidgetItem([f"{key}: {value}"])
                        meta_item.addChild(meta_child)
                
                song_item.addChild(meta_item)


class SearchWidget(QWidget):
    """Widget de recherche"""
    
    search_requested = Signal(str, str)  # Requête, filtre
    search_cleared = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface de recherche"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Marges réduites
        
        # Champ de recherche
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Rechercher...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_edit)
        
        # Filtre
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Tout", "Titre", "Artiste", "Style"
        ])
        self.filter_combo.currentTextChanged.connect(self.on_search_changed)
        layout.addWidget(self.filter_combo)
        
        # Bouton effacer
        self.clear_button = QPushButton("❌")
        self.clear_button.setMaximumWidth(30)
        self.clear_button.clicked.connect(self.clear_search)
        layout.addWidget(self.clear_button)
        
        # IMPORTANT: Limiter la hauteur du widget
        self.setMaximumHeight(40)  # Hauteur fixe
        self.setMinimumHeight(40)  # Hauteur minimum
    
    def on_search_changed(self):
        """Appelé quand la recherche change"""
        query = self.search_edit.text().strip()
        filter_type = self.filter_combo.currentText().lower()
        
        if query:
            self.search_requested.emit(query, filter_type)
        else:
            self.search_cleared.emit()
    
    def clear_search(self):
        """Efface la recherche"""
        self.search_edit.clear()
        self.search_cleared.emit()


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""
    
    def __init__(self):
        super().__init__()
        
        # Initialiser les composants
        self.library = Library(LibraryConfig(
            library_path=config_manager.get_library_path()
        ))
        self.current_song = None
        self.import_worker = None
        
        # Configurer l'interface
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_status_bar()
        self.setup_connections()
        
        # Charger la bibliothèque
        self.load_library()
        
        # Configurer la fenêtre
        self.setWindowTitle("MusicPartMate")
        config = config_manager.config
        #self.setGeometry(100, 100, config.window_width, config.window_height)
        self.showMaximized()
    
    def setup_ui(self):
        """Configure l'interface utilisateur principale"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)  # Espacement réduit entre les widgets
        
        # Barre de recherche avec taille fixe
        self.search_widget = SearchWidget()
        main_layout.addWidget(self.search_widget)
        
        # Splitter principal (prend tout l'espace restant)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter, 1)  # stretch=1 pour prendre l'espace restant
        
        # Panel gauche - Bibliothèque
        left_panel = self.create_library_panel()
        main_splitter.addWidget(left_panel)
        
        # Panel droit - Contenu
        right_panel = self.create_content_panel()
        main_splitter.addWidget(right_panel)
        
        # PROPORTIONS MODIFIÉES : Panel gauche plus large pour la zone vidéo
        config = config_manager.config
        left_width = 500  # AUGMENTÉ de 400 à 500 pour la zone vidéo
        right_width = config.window_width - left_width
        main_splitter.setSizes([left_width, right_width])
    
    def create_library_panel(self):
        """Crée le panel de la bibliothèque avec lecteur média intégré - ZONE VIDÉO AGRANDIE"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Titre
        title_label = QLabel("📚 Bibliothèque")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title_label)
        
        # Splitter vertical pour séparer arbre et lecteur
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(left_splitter)
        
        # Arbre des chansons (partie haute) - RÉDUITE
        self.library_tree = LibraryTreeWidget()
        left_splitter.addWidget(self.library_tree)
        
        # Lecteur média (partie basse) avec titre - AGRANDIE
        media_frame = QFrame()
        media_layout = QVBoxLayout(media_frame)
        media_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        media_layout.setContentsMargins(0, 5, 0, 0)
        
        # Titre du lecteur
        media_title_label = QLabel("🎵🎬 Lecteur Audio/Vidéo")
        media_title_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        media_layout.addWidget(media_title_label)
        
        # Le lecteur lui-même - VOTRE CODE ORIGINAL GARDÉ
        self.media_player = MediaPlayer()
        
        # MODIFICATION IHM : Forcer une hauteur plus grande pour la zone vidéo
        self.media_player.setMinimumHeight(300)  # Plus haut que l'original
        self.media_player.setMaximumHeight(450)  # Zone vidéo plus grande
        
        media_layout.addWidget(self.media_player)
        
        left_splitter.addWidget(media_frame)
        
        # Stocker la référence au splitter pour les ajustements de layout
        self.left_splitter = left_splitter
        
        # NOUVELLES PROPORTIONS : Plus d'espace pour le lecteur vidéo
        # library_height = 300   # RÉDUIT de 400 à 300 (bibliothèque plus compacte)
        # player_height = 400    # AUGMENTÉ de 300 à 400 (zone vidéo plus grande)
        
        # left_splitter.setSizes([library_height, player_height])

        self.adjust_layout_for_video()
        
        return widget
    
    def create_content_panel(self):
        """Crée le panel de contenu (seulement le viewer de documents)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Titre de la zone document
        doc_title_label = QLabel("📄 Zone Document")
        doc_title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(doc_title_label)
        
        # Viewer de documents (prend tout l'espace)
        self.document_viewer = DocumentViewer()
        layout.addWidget(self.document_viewer)
        
        return widget
    
    def setup_menu_bar(self):
        """Configure la barre de menu"""
        menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = menubar.addMenu("&Fichier")
        
        new_action = QAction("&Nouvelle chanson", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_song)
        file_menu.addAction(new_action)
        
        import_action = QAction("&Importer...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self.import_songs)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("&Exporter bibliothèque...", self)
        export_action.triggered.connect(self.export_library)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Quitter", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Édition
        edit_menu = menubar.addMenu("&Édition")
        
        self.edit_song_action = QAction("&Éditer chanson", self)
        self.edit_song_action.setShortcut(QKeySequence("F2"))
        self.edit_song_action.setEnabled(False)
        self.edit_song_action.triggered.connect(self.edit_current_song)
        edit_menu.addAction(self.edit_song_action)
        
        self.delete_song_action = QAction("&Supprimer chanson", self)
        self.delete_song_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_song_action.setEnabled(False)
        self.delete_song_action.triggered.connect(self.delete_current_song)
        edit_menu.addAction(self.delete_song_action)
        
        # Menu Affichage
        view_menu = menubar.addMenu("&Affichage")
        
        refresh_action = QAction("&Actualiser", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self.load_library)
        view_menu.addAction(refresh_action)
        
        # Menu Aide
        help_menu = menubar.addMenu("&Aide")
        
        stats_action = QAction("&Statistiques", self)
        stats_action.triggered.connect(self.show_statistics)
        help_menu.addAction(stats_action)
        
        about_action = QAction("À &propos", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Configure la barre d'outils"""
        toolbar = self.addToolBar("Principal")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        
        # Actions principales
        new_action = QAction("🆕\nNouveau", self)
        new_action.triggered.connect(self.new_song)
        toolbar.addAction(new_action)
        
        self.edit_action = QAction("✏️\nÉditer", self)
        self.edit_action.setEnabled(False)
        self.edit_action.triggered.connect(self.edit_current_song)
        toolbar.addAction(self.edit_action)
        
        self.delete_action = QAction("🗑️\nSupprimer", self)
        self.delete_action.setEnabled(False)
        self.delete_action.triggered.connect(self.delete_current_song)
        toolbar.addAction(self.delete_action)
        
        toolbar.addSeparator()
        
        import_action = QAction("📁\nImporter", self)
        import_action.triggered.connect(self.import_songs)
        toolbar.addAction(import_action)
        
        export_action = QAction("💾\nExporter", self)
        export_action.triggered.connect(self.export_library)
        toolbar.addAction(export_action)
    
    def setup_status_bar(self):
        """Configure la barre de statut"""
        self.status_bar = self.statusBar()
        
        # Label principal
        self.status_label = QLabel("Prêt")
        self.status_bar.addWidget(self.status_label)
        
        # Séparateur
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        # Compteur de chansons
        self.song_count_label = QLabel("0 chansons")
        self.status_bar.addPermanentWidget(self.song_count_label)
    
    def setup_connections(self):
        """Configure les connexions de signaux"""
        # Bibliothèque
        self.library.add_observer(self.on_library_changed)
        
        # Arbre de la bibliothèque
        self.library_tree.song_selected.connect(self.on_song_selected)
        self.library_tree.media_selected.connect(self.on_media_selected)
        
        # Recherche
        self.search_widget.search_requested.connect(self.on_search_requested)
        self.search_widget.search_cleared.connect(self.load_library)
        
        # Lecteur média
        self.media_player.media_loaded.connect(self.on_media_loaded)
        
        # Connexions pour les ajustements de layout vidéo
        if hasattr(self.media_player, 'playback_started'):
            self.media_player.playback_started.connect(self.on_playback_started)
        if hasattr(self.media_player, 'playback_stopped'):
            self.media_player.playback_stopped.connect(self.on_playback_stopped)
    
    def on_playback_started(self):
        """Appelé quand la lecture démarre - ajuste le layout si vidéo"""
        if hasattr(self.media_player, 'is_video') and self.media_player.is_video:
            self.adjust_layout_for_video()
    
    def on_playback_stopped(self):
        """Appelé quand la lecture s'arrête - remet le layout audio"""
        self.adjust_layout_for_audio()
    
    def adjust_layout_for_video(self):
        """Ajuste le layout pour l'affichage vidéo"""
        if hasattr(self, 'left_splitter'):
            # Plus d'espace pour le lecteur vidéo
            config = config_manager.config
            video_library_height = max(150, config.library_height - 200)  # Réduire biblio
            video_player_height = config.player_height + 200              # Agrandir lecteur
            
            self.left_splitter.setSizes([video_library_height, video_player_height])
            print(f"📐 Layout vidéo: biblio={video_library_height}, lecteur={video_player_height}")
    
    def adjust_layout_for_audio(self):
        self.adjust_layout_for_video()
        """Ajuste le layout pour l'audio seulement"""
        # if hasattr(self, 'left_splitter'):
        #     # Revenir aux proportions normales
        #     config = config_manager.config
        #     self.left_splitter.setSizes([config.library_height, config.player_height])
        #     print(f"📐 Layout audio: biblio={config.library_height}, lecteur={config.player_height}")
    
    def load_library(self):
        """Charge la bibliothèque dans l'interface"""
        self.library_tree.load_library(self.library)
        self.update_status()
    
    def update_status(self):
        """Met à jour la barre de statut"""
        count = self.library.song_count
        self.song_count_label.setText(f"{count} chanson{'s' if count != 1 else ''}")
        
        if count == 0:
            self.status_label.setText("Bibliothèque vide - Ajoutez des chansons")
        else:
            self.status_label.setText("Prêt")
    
    def on_library_changed(self, event_type: str, song: Song = None):
        """Appelé quand la bibliothèque change"""
        self.load_library()
        
        if event_type == "song_added":
            self.status_label.setText(f"Chanson '{song.title}' ajoutée")
        elif event_type == "song_updated":
            self.status_label.setText(f"Chanson '{song.title}' mise à jour")
        elif event_type == "song_removed":
            self.status_label.setText(f"Chanson '{song.title}' supprimée")
    
    def on_song_selected(self, song: Song):
        """Appelé quand une chanson est sélectionnée"""
        self.current_song = song
        
        # Activer les actions sur la chanson
        self.edit_song_action.setEnabled(True)
        self.delete_song_action.setEnabled(True)
        self.edit_action.setEnabled(True)
        self.delete_action.setEnabled(True)
        
        # Charger le premier document s'il existe
        if song.primary_document:
            self.document_viewer.load_document(song.primary_document)
        
        # Mettre à jour le statut
        self.status_label.setText(f"Chanson sélectionnée: {song.display_name}")
    
    def on_media_selected(self, media_type: str, file_path: Path):
        """Appelé quand un média spécifique est sélectionné"""
        if media_type == "document":
            self.document_viewer.load_document(file_path)
        elif media_type in ["audio", "video"]:
            self.media_player.load_media(file_path)
            
            # Ajuster le layout en fonction du type de média
            if media_type == "video":
                # Délai pour laisser le temps au lecteur de se configurer
                QTimer.singleShot(500, self.adjust_layout_for_video)
            else:
                self.adjust_layout_for_audio()
        
        self.status_label.setText(f"Média chargé: {file_path.name}")
    
    def on_search_requested(self, query: str, filter_type: str):
        """Appelé quand une recherche est demandée"""
        if filter_type == "tout":
            search_fields = ['title', 'artist', 'style']
        elif filter_type == "titre":
            search_fields = ['title']
        elif filter_type == "artiste":
            search_fields = ['artist']
        elif filter_type == "style":
            search_fields = ['style']
        else:
            search_fields = ['title', 'artist', 'style']
        
        # Effectuer la recherche
        results = self.library.search_songs(query, search_fields)
        
        # Afficher les résultats
        self.library_tree.clear()
        
        if results:
            # Créer un groupe "Résultats de recherche"
            results_item = QTreeWidgetItem([f"🔍 Résultats ({len(results)})"])
            results_item.setExpanded(True)
            self.library_tree.addTopLevelItem(results_item)
            
            for song in results:
                song_item = QTreeWidgetItem([f"🎵 {song.display_name}"])
                song_item.setData(0, Qt.ItemDataRole.UserRole, song)
                results_item.addChild(song_item)
            
            self.status_label.setText(f"{len(results)} résultat(s) trouvé(s) pour '{query}'")
        else:
            no_results_item = QTreeWidgetItem([f"❌ Aucun résultat pour '{query}'"])
            self.library_tree.addTopLevelItem(no_results_item)
            self.status_label.setText(f"Aucun résultat pour '{query}'")
    
    def on_media_loaded(self, filename: str):
        """Appelé quand un média est chargé dans le lecteur"""
        self.status_label.setText(f"Lecture: {filename}")
    
    def new_song(self):
        """Crée une nouvelle chanson"""
        dialog = SongDialog(parent=self)
        if dialog.exec() == QMessageBox.DialogCode.Accepted:
            if self.library.add_song(dialog.song):
                self.status_label.setText(f"Nouvelle chanson '{dialog.song.title}' créée")
            else:
                QMessageBox.warning(
                    self, 
                    "Erreur", 
                    "Impossible d'ajouter la chanson. Vérifiez qu'elle n'existe pas déjà."
                )
    
    def edit_current_song(self):
        """Édite la chanson actuelle"""
        if not self.current_song:
            QMessageBox.warning(self, "Attention", "Aucune chanson sélectionnée")
            return
        
        dialog = SongDialog(self.current_song, parent=self)
        if dialog.exec() == QMessageBox.DialogCode.Accepted:
            self.library.update_song(self.current_song)
            self.status_label.setText(f"Chanson '{self.current_song.title}' mise à jour")
    
    def delete_current_song(self):
        """Supprime la chanson actuelle"""
        if not self.current_song:
            QMessageBox.warning(self, "Attention", "Aucune chanson sélectionnée")
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirmation", 
            f"Supprimer définitivement la chanson '{self.current_song.display_name}' ?\n\n"
            f"Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            song_name = self.current_song.display_name
            self.library.remove_song(self.current_song)
            self.current_song = None
            
            # Désactiver les actions
            self.edit_song_action.setEnabled(False)
            self.delete_song_action.setEnabled(False)
            self.edit_action.setEnabled(False)
            self.delete_action.setEnabled(False)
            
            # Vider les viewers
            self.document_viewer.show_welcome_message()
            self.media_player.clear_media()
            
            self.status_label.setText(f"Chanson '{song_name}' supprimée")
    
    def import_songs(self):
        """Importe des chansons depuis des dossiers"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Sélectionner le dossier contenant les chansons"
        )
        
        if not folder:
            return
        
        base_folder = Path(folder)
        
        # Chercher tous les sous-dossiers qui pourraient être des chansons
        potential_song_folders = []
        
        # Option 1: Le dossier sélectionné contient directement des médias
        formats = get_supported_formats()
        media_files = scan_folder_for_media(base_folder, formats)
        total_media = sum(len(files) for files in media_files.values())
        
        if total_media > 0:
            potential_song_folders.append(base_folder)
        
        # Option 2: Les sous-dossiers contiennent des médias
        for subfolder in base_folder.iterdir():
            if subfolder.is_dir():
                media_files = scan_folder_for_media(subfolder, formats)
                total_media = sum(len(files) for files in media_files.values())
                if total_media > 0:
                    potential_song_folders.append(subfolder)
        
        if not potential_song_folders:
            QMessageBox.information(
                self,
                "Aucune chanson trouvée",
                "Aucun fichier média supporté n'a été trouvé dans ce dossier."
            )
            return
        
        # Confirmer l'import
        reply = QMessageBox.question(
            self,
            "Confirmer l'import",
            f"Trouvé {len(potential_song_folders)} dossier(s) contenant des médias.\n"
            f"Voulez-vous les importer en tant que chansons ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Démarrer l'import en arrière-plan
        self.start_import(potential_song_folders)
    
    def start_import(self, folder_paths: List[Path]):
        """Démarre l'import en arrière-plan"""
        # Créer la boîte de progression
        self.progress_dialog = QProgressDialog(
            "Import en cours...", 
            "Annuler", 
            0, 100, 
            self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()
        
        # Démarrer le worker
        self.import_worker = ImportWorker(folder_paths)
        self.import_worker.progress_updated.connect(self.on_import_progress)
        self.import_worker.song_imported.connect(self.on_song_imported)
        self.import_worker.import_finished.connect(self.on_import_finished)
        
        # Connecter l'annulation
        self.progress_dialog.canceled.connect(self.import_worker.stop)
        
        self.import_worker.start()
    
    def on_import_progress(self, value: int, message: str):
        """Met à jour la progression de l'import"""
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(message)
    
    def on_song_imported(self, song: Song):
        """Appelé quand une chanson est importée"""
        self.library.add_song(song)
    
    def on_import_finished(self, success_count: int, error_count: int):
        """Appelé quand l'import est terminé"""
        self.progress_dialog.hide()
        
        message = f"Import terminé:\n"
        message += f"• {success_count} chanson(s) importée(s)\n"
        if error_count > 0:
            message += f"• {error_count} erreur(s)"
        
        QMessageBox.information(self, "Import terminé", message)
        self.status_label.setText(f"Import: {success_count} chansons ajoutées")
    
    def export_library(self):
        """Exporte la bibliothèque"""
        if self.library.song_count == 0:
            QMessageBox.information(
                self,
                "Bibliothèque vide",
                "Il n'y a aucune chanson à exporter."
            )
            return
        
        # Choisir le format
        formats = ["JSON (*.json)", "CSV (*.csv)"]
        format_choice, ok = QInputDialog.getItem(
            self,
            "Format d'export",
            "Choisissez le format d'export:",
            formats,
            0,
            False
        )
        
        if not ok:
            return
        
        # Déterminer l'extension
        if "JSON" in format_choice:
            ext = "json"
            filter_str = "Fichiers JSON (*.json)"
        else:
            ext = "csv"
            filter_str = "Fichiers CSV (*.csv)"
        
        # Choisir le fichier de destination
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la bibliothèque",
            f"bibliotheque_musicpartmate.{ext}",
            filter_str
        )
        
        if not filename:
            return
        
        # Effectuer l'export
        export_path = Path(filename)
        success = self.library.export_library(export_path, ext)
        
        if success:
            QMessageBox.information(
                self,
                "Export réussi",
                f"Bibliothèque exportée vers:\n{export_path}"
            )
            self.status_label.setText(f"Bibliothèque exportée: {export_path.name}")
        else:
            QMessageBox.critical(
                self,
                "Erreur d'export",
                "Une erreur s'est produite lors de l'export."
            )
    
    def show_statistics(self):
        """Affiche les statistiques de la bibliothèque"""
        stats = self.library.get_statistics()
        
        message = "📊 Statistiques de la bibliothèque\n\n"
        message += f"Chansons: {stats['total_songs']}\n"
        message += f"Artistes: {stats['total_artists']}\n"
        message += f"Styles: {stats['total_styles']}\n\n"
        message += f"Avec documents: {stats['songs_with_documents']}\n"
        message += f"Avec audio: {stats['songs_with_audio']}\n"
        message += f"Avec vidéo: {stats['songs_with_video']}\n"
        
        if stats['most_common_style']:
            message += f"\nStyle le plus fréquent: {stats['most_common_style']}\n"
        
        if stats['most_prolific_artist']:
            message += f"Artiste le plus prolifique: {stats['most_prolific_artist']}"
        
        QMessageBox.information(self, "Statistiques", message)
    
    def show_about(self):
        """Affiche les informations sur l'application"""
        message = """
        <h2>🎵 MusicPartMate</h2>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Description:</b> Gestionnaire de partitions musicales</p>
        
        <h3>Fonctionnalités:</h3>
        <ul>
        <li>📄 Lecture de documents (PDF, TXT, DOC, images)</li>
        <li>🎵 Lecture audio et vidéo</li>
        <li>📚 Gestion de bibliothèque</li>
        <li>🔍 Recherche avancée</li>
        <li>📁 Import/Export</li>
        </ul>
        
        <p><b>Formats supportés:</b></p>
        <ul>
        <li>Documents: PDF, TXT, DOC, DOCX, ODT, PNG, JPG</li>
        <li>Audio: MP3, WAV, FLAC, OGG, M4A</li>
        <li>Vidéo: MP4, AVI, MOV, MKV</li>
        </ul>
        """
        
        QMessageBox.about(self, "À propos de MusicPartMate", message)
    
    def closeEvent(self, event):
        """Gère la fermeture de l'application"""
        # Arrêter les workers en cours
        if self.import_worker and self.import_worker.isRunning():
            self.import_worker.stop()
            self.import_worker.wait()
        
        # Sauvegarder la configuration
        config_manager.save_config()
        
        event.accept()
    
    def keyPressEvent(self, event):
        """Gère les raccourcis clavier globaux"""
        if event.key() == Qt.Key.Key_F5:
            self.load_library()
        elif event.key() == Qt.Key.Key_Delete and self.current_song:
            self.delete_current_song()
        elif event.key() == Qt.Key.Key_F2 and self.current_song:
            self.edit_current_song()
        else:
            super().keyPressEvent(event)