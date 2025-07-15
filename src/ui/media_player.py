"""
Widget pour la lecture de médias audio et vidéo avec fallback - Version nettoyée
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, 
    QLabel, QFrame, QComboBox, QStyle, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from pathlib import Path
from typing import Optional
import webbrowser
import subprocess
import os
import sys

# Import conditionnel du multimédia
MULTIMEDIA_AVAILABLE = False
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
    print("✅ Backend multimédia Qt disponible")
except ImportError as e:
    print(f"⚠️ Backend multimédia Qt non disponible: {e}")
    print("📽️ Le lecteur utilisera des applications externes")


class MediaPlayer(QWidget):
    """
    Widget pour la lecture de médias audio et vidéo
    Utilise le backend Qt si disponible, sinon fallback vers applications externes
    """
    
    # Signaux émis par le lecteur
    media_loaded = Signal(str)
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    position_changed = Signal(int)
    external_player_opened = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_media = None
        self.is_video = False
        self.youtube_url = None
        
        if MULTIMEDIA_AVAILABLE:
            self.setup_full_player()
        else:
            self.setup_fallback_player()
    
    def setup_full_player(self):
        """Configure le lecteur multimédia complet"""
        try:
            # Initialiser les composants multimédia
            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
            
            # Widget vidéo avec configuration spéciale
            self.video_widget = QVideoWidget()
            self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            
            # Configuration pour améliorer la compatibilité vidéo
            try:
                self.video_widget.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen, False)
                self.video_widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            except:
                pass  # Certaines versions peuvent ne pas supporter ces attributs
            
            self.setup_full_ui()
            self.setup_connections()
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation du lecteur: {e}")
            # Basculer vers fallback
            global MULTIMEDIA_AVAILABLE
            MULTIMEDIA_AVAILABLE = False
            self.setup_fallback_player()
    
    def setup_fallback_player(self):
        """Configure le lecteur de fallback"""
        layout = QVBoxLayout(self)
        
        # Message d'information
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        
        warning_label = QLabel("⚠️ Backend multimédia Qt non disponible")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        info_layout.addWidget(warning_label)
        
        help_label = QLabel("Les médias s'ouvriront dans des applications externes")
        help_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(help_label)
        
        layout.addWidget(info_frame)
        
        # Informations sur le média
        self.info_label = QLabel("🎵 Aucun média chargé")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        layout.addWidget(self.info_label)
        
        # Contrôles
        controls_layout = QHBoxLayout()
        
        self.play_button = QPushButton("🎵 Ouvrir avec lecteur externe")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.open_external)
        controls_layout.addWidget(self.play_button)
        
        layout.addLayout(controls_layout)
    
    def setup_full_ui(self):
        """Configure l'interface complète du lecteur"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Informations sur le média (toujours en haut)
        self.info_label = QLabel("🎵 Aucun média chargé")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        # Contrôles principaux (TOUJOURS VISIBLES)
        controls_layout = QHBoxLayout()
        
        # Boutons de contrôle
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_pause)
        controls_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)
        controls_layout.addWidget(self.stop_button)
        
        # Slider de position
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setEnabled(False)
        self.position_slider.sliderMoved.connect(self.set_position)
        controls_layout.addWidget(self.position_slider)
        
        # Temps
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMinimumWidth(80)
        controls_layout.addWidget(self.time_label)
        
        layout.addLayout(controls_layout)
        
        # Contrôles secondaires (TOUJOURS VISIBLES)
        secondary_controls = QHBoxLayout()
        
        # Volume
        secondary_controls.addWidget(QLabel("🔊"))
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        secondary_controls.addWidget(self.volume_slider)
        
        # Bouton externe (fallback)
        self.external_button = QPushButton("📱 Externe")
        self.external_button.hide()
        self.external_button.clicked.connect(self.open_external)
        secondary_controls.addWidget(self.external_button)
        
        # Bouton pour forcer l'affichage vidéo
        self.force_video_button = QPushButton("🎬 Forcer")
        self.force_video_button.hide()
        self.force_video_button.clicked.connect(self.force_video_display)
        secondary_controls.addWidget(self.force_video_button)
        
        secondary_controls.addStretch()
        
        # Bouton YouTube
        self.youtube_button = QPushButton("🌐 YouTube")
        self.youtube_button.hide()
        self.youtube_button.clicked.connect(self.open_youtube_url)
        secondary_controls.addWidget(self.youtube_button)
        
        layout.addLayout(secondary_controls)
        
        # Zone vidéo EN BAS (pour ne pas masquer les contrôles)
        self.video_frame = QFrame()
        self.video_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.video_frame.setMinimumHeight(250)  # Hauteur minimum
        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(2, 2, 2, 2)
        
        # Message pour la zone vidéo
        self.video_placeholder = QLabel("📺 Zone vidéo")
        self.video_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_placeholder.setStyleSheet("color: #999; font-size: 11px;")
        video_layout.addWidget(self.video_placeholder)
        
        if hasattr(self, 'video_widget'):
            video_layout.addWidget(self.video_widget)
            self.video_widget.hide()  # Masqué au départ
        
        #self.video_frame.hide()
        layout.addWidget(self.video_frame)
        
        # Hauteur fixe pour éviter l'expansion incontrôlée
        self.setMinimumHeight(120)
        self.setMaximumHeight(300)  # Limite raisonnable
    
    def setup_connections(self):
        """Configure les connexions de signaux pour le lecteur complet"""
        if not MULTIMEDIA_AVAILABLE or not hasattr(self, 'media_player'):
            return
        
        try:
            # Signaux du lecteur
            self.media_player.positionChanged.connect(self.on_position_changed)
            self.media_player.durationChanged.connect(self.on_duration_changed)
            self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
            self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
            self.media_player.errorOccurred.connect(self.on_error_occurred)
            
            # Timer pour la mise à jour de l'interface
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_ui)
            self.update_timer.start(100)
            
        except Exception as e:
            print(f"Erreur lors de la configuration des connexions: {e}")
    
    def load_media(self, file_path: Path):
        """Charge un média (FONCTION PRINCIPALE UNIQUE)"""
        if not MULTIMEDIA_AVAILABLE:
            self.load_media_fallback(file_path)
            return
        
        if not file_path.exists():
            self.show_error(f"Fichier non trouvé: {file_path}")
            return
        
        try:
            # Déterminer le type de média
            suffix = file_path.suffix.lower()
            
            self.current_media = file_path
            self.youtube_url = None
            self.youtube_button.hide()
            
            # Configurer pour vidéo ou audio
            if suffix in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']:
                self.is_video = True
                self.setup_video_display()
            else:
                self.is_video = False
                #self.hide_video_display()
            
            # Charger le média
            media_url = QUrl.fromLocalFile(str(file_path.absolute()))
            self.media_player.setSource(media_url)
            
            # Mettre à jour l'interface
            self.info_label.setText(f"📁 {file_path.name}")
            self.enable_controls(True)
            self.external_button.show()  # Toujours montrer l'option externe
            
            if self.is_video:
                self.force_video_button.show()
            
            # Émettre le signal
            self.media_loaded.emit(file_path.name)
            
        except Exception as e:
            self.show_error(f"Erreur lors du chargement: {e}")
            self.external_button.show()
    
    def load_media_fallback(self, file_path: Path):
        """Charge un média en mode fallback"""
        self.current_media = file_path
        self.info_label.setText(f"📁 {file_path.name}")
        self.play_button.setEnabled(True)
        self.play_button.setText(f"🎵 Ouvrir {file_path.name}")
        self.media_loaded.emit(file_path.name)
    
    def setup_video_display(self):
        """Configure l'affichage vidéo"""
        if not hasattr(self, 'video_widget'):
            return
        
        try:
            # Connecter le widget vidéo au lecteur
            self.media_player.setVideoOutput(self.video_widget)
            
            # Afficher la zone vidéo
            self.video_frame.show()
            self.video_placeholder.hide()
            self.video_widget.show()
            
            # Hauteur modérée pour ne pas masquer les contrôles
            #self.setMaximumHeight(280)  # Plus conservateur
            
            # Signaler au parent de réajuster
            #self.request_video_layout_adjustment()
            
            print("🎬 Affichage vidéo configuré")
            
        except Exception as e:
            print(f"❌ Erreur configuration vidéo: {e}")
            self.show_video_error()
    
    def hide_video_display(self):
        """Masque l'affichage vidéo"""
        if hasattr(self, 'video_frame'):
            self.video_frame.hide()
        
        if hasattr(self, 'media_player'):
            self.media_player.setVideoOutput(None)
        
        # Revenir à la taille compacte
        #self.setMaximumHeight(150)
        
        # Signaler au parent de réajuster
        #self.request_audio_layout_adjustment()
    
    def request_video_layout_adjustment(self):
        """Demande au parent de réajuster pour la vidéo"""
        # Délai pour laisser le temps au widget de se redimensionner
        # QTimer.singleShot(100, self._do_video_layout_adjustment)
    
    def _do_video_layout_adjustment(self):
        """Effectue l'ajustement de layout pour la vidéo"""
        parent = self.parent()
        while parent and not isinstance(parent, QSplitter):
            parent = parent.parent()
        
        if parent and isinstance(parent, QSplitter):
            current_sizes = parent.sizes()
            if len(current_sizes) == 2:
                total = sum(current_sizes)
                # 50% pour l'arbre, 50% pour le lecteur vidéo
                new_library_size = total // 2
                new_player_size = total // 2
                parent.setSizes([new_library_size, new_player_size])
                print("📐 Proportions ajustées pour la vidéo")
    
    def request_audio_layout_adjustment(self):
        """Demande au parent de réajuster pour l'audio"""
        QTimer.singleShot(100, self._do_audio_layout_adjustment)
    
    def _do_audio_layout_adjustment(self):
        """Effectue l'ajustement de layout pour l'audio"""
        parent = self.parent()
        while parent and not isinstance(parent, QSplitter):
            parent = parent.parent()
        
        if parent and isinstance(parent, QSplitter):
            current_sizes = parent.sizes()
            if len(current_sizes) == 2:
                total = sum(current_sizes)
                # 75% pour l'arbre, 25% pour le lecteur audio
                new_library_size = int(total * 0.75)
                new_player_size = int(total * 0.25)
                parent.setSizes([new_library_size, new_player_size])
                print("📐 Proportions ajustées pour l'audio")
    
    def force_video_display(self):
        """Force la réinitialisation de l'affichage vidéo"""
        if not hasattr(self, 'video_widget') or not self.is_video:
            return
        
        try:
            # Réinitialiser la sortie vidéo
            self.media_player.setVideoOutput(None)
            QTimer.singleShot(100, lambda: self.media_player.setVideoOutput(self.video_widget))
            
            # Forcer le repaint
            self.video_widget.update()
            self.video_widget.repaint()
            
            self.show_info("🔄 Affichage vidéo réinitialisé")
            
        except Exception as e:
            self.show_error(f"Erreur lors de la réinitialisation: {e}")
    
    def show_video_error(self):
        """Affiche une erreur spécifique à la vidéo"""
        self.video_placeholder.setText(
            "❌ Problème d'affichage vidéo\n"
            "💡 Essayez:\n"
            "• Bouton 'Forcer vidéo'\n"
            "• Bouton 'Ouvrir externe'\n"
            "• Installer K-Lite Codec Pack"
        )
        self.video_placeholder.setStyleSheet("color: red; font-size: 10px;")
        self.video_placeholder.show()
    
    def open_external(self):
        """Ouvre le média avec l'application externe"""
        if not self.current_media:
            return
        
        try:
            if sys.platform.startswith('win'):
                os.startfile(str(self.current_media))
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', str(self.current_media)])
            else:
                subprocess.run(['xdg-open', str(self.current_media)])
            
            self.external_player_opened.emit(str(self.current_media))
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'ouvrir le fichier:\n{e}")
    
    def play_pause(self):
        """Bascule entre lecture et pause"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
            else:
                self.media_player.play()
        else:
            self.open_external()
    
    def stop(self):
        """Arrête la lecture"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            self.media_player.stop()
    
    def set_position(self, position: int):
        """Change la position de lecture"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            self.media_player.setPosition(position)
    
    def set_volume(self, volume: int):
        """Change le volume"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'audio_output'):
            self.audio_output.setVolume(volume / 100.0)
    
    def clear_media(self):
        """Vide le lecteur"""
        if hasattr(self, 'media_player'):
            self.media_player.stop()
            self.media_player.setSource(QUrl())
        
        self.current_media = None
        self.youtube_url = None
        self.is_video = False
        
        if hasattr(self, 'video_frame'):
            self.video_frame.hide()
        if hasattr(self, 'youtube_button'):
            self.youtube_button.hide()
        if hasattr(self, 'external_button'):
            self.external_button.hide()
        if hasattr(self, 'force_video_button'):
            self.force_video_button.hide()
        
        self.enable_controls(False)
        
        if hasattr(self, 'info_label'):
            self.info_label.setText("🎵 Aucun média chargé")
            self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        
        self.setMaximumHeight(150)
    
    def enable_controls(self, enabled: bool):
        """Active ou désactive les contrôles"""
        if hasattr(self, 'play_button'):
            self.play_button.setEnabled(enabled)
        if hasattr(self, 'stop_button'):
            self.stop_button.setEnabled(enabled)
        if hasattr(self, 'position_slider'):
            self.position_slider.setEnabled(enabled)
        if hasattr(self, 'volume_slider'):
            self.volume_slider.setEnabled(enabled)
    
    def show_error(self, message: str):
        """Affiche un message d'erreur"""
        if hasattr(self, 'info_label'):
            self.info_label.setText(f"❌ {message}")
            self.info_label.setStyleSheet("color: red; font-size: 12px;")
            QTimer.singleShot(3000, self.reset_info_label)
    
    def show_info(self, message: str):
        """Affiche un message d'information temporaire"""
        if not hasattr(self, 'info_label'):
            return
            
        original_text = self.info_label.text()
        original_style = self.info_label.styleSheet()
        
        self.info_label.setText(f"ℹ️ {message}")
        self.info_label.setStyleSheet("color: blue; font-size: 12px;")
        
        # Restaurer après 2 secondes
        QTimer.singleShot(2000, lambda: [
            self.info_label.setText(original_text),
            self.info_label.setStyleSheet(original_style)
        ])
    
    def reset_info_label(self):
        """Remet le label d'info à l'état normal"""
        if not hasattr(self, 'info_label'):
            return
        
        if self.current_media:
            self.info_label.setText(f"📁 {self.current_media.name}")
        else:
            self.info_label.setText("🎵 Aucun média chargé")
        
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
    
    # Gestion des événements du lecteur Qt
    def on_position_changed(self, position: int):
        """Appelé quand la position change"""
        if hasattr(self, 'position_slider') and not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        self.position_changed.emit(position)
    
    def on_duration_changed(self, duration: int):
        """Appelé quand la durée change"""
        if hasattr(self, 'position_slider'):
            self.position_slider.setRange(0, duration)
    
    def on_playback_state_changed(self, state):
        """Appelé quand l'état de lecture change"""
        if not hasattr(self, 'play_button'):
            return
        
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.playback_started.emit()
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            if state == QMediaPlayer.PlaybackState.PausedState:
                self.playback_paused.emit()
            else:
                self.playback_stopped.emit()
    
    def on_media_status_changed(self, status):
        """Appelé quand le statut du média change"""
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.show_error("Format de média non supporté")
            if hasattr(self, 'external_button'):
                self.external_button.show()
        elif status == QMediaPlayer.MediaStatus.LoadedMedia:
            if self.is_video:
                # S'assurer que la vidéo est configurée
                QTimer.singleShot(500, self.check_video_display)
    
    def check_video_display(self):
        """Vérifie si la vidéo s'affiche correctement"""
        if self.is_video and hasattr(self, 'video_widget'):
            # Si pas d'image après 2 secondes de lecture, proposer des solutions
            QTimer.singleShot(2000, self.check_video_rendering)
    
    def check_video_rendering(self):
        """Vérifie le rendu vidéo et propose des solutions si problème"""
        if (self.is_video and 
            hasattr(self, 'media_player') and 
            self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState):
            
            # Proposer des solutions si la vidéo ne s'affiche pas
            self.show_info("Si pas d'image: utilisez 'Forcer vidéo' ou 'Ouvrir externe'")
    
    def on_error_occurred(self, error):
        """Appelé en cas d'erreur"""
        self.show_error("Erreur de lecture - essayez le lecteur externe")
        if hasattr(self, 'external_button'):
            self.external_button.show()
    
    def update_ui(self):
        """Met à jour l'interface utilisateur"""
        if not MULTIMEDIA_AVAILABLE or not hasattr(self, 'media_player'):
            return
        
        try:
            position = self.media_player.position()
            duration = self.media_player.duration()
            
            current_time = self.format_time(position)
            total_time = self.format_time(duration)
            
            if hasattr(self, 'time_label'):
                self.time_label.setText(f"{current_time} / {total_time}")
        except:
            pass
    
    def format_time(self, ms: int) -> str:
        """Formate le temps en mm:ss"""
        if ms < 0:
            return "00:00"
        
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        
        return f"{minutes:02d}:{seconds:02d}"
    
    # Fonctions YouTube
    def load_youtube_url(self, url: str, title: str = ""):
        """Charge une URL YouTube"""
        self.current_media = None
        self.youtube_url = url
        self.is_video = False
        
        if hasattr(self, 'video_frame'):
            self.video_frame.hide()
        if hasattr(self, 'youtube_button'):
            self.youtube_button.show()
        
        display_title = title or "Vidéo YouTube"
        if hasattr(self, 'info_label'):
            self.info_label.setText(f"🌐 {display_title}")
        
        self.enable_controls(False)
        self.media_loaded.emit(display_title)
    
    def open_youtube_url(self):
        """Ouvre l'URL YouTube dans le navigateur"""
        if self.youtube_url:
            webbrowser.open(self.youtube_url)
            self.external_player_opened.emit(self.youtube_url)
    
    # Méthodes pour la compatibilité
    def get_current_position(self) -> int:
        """Retourne la position actuelle en millisecondes"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            return self.media_player.position()
        return 0
    
    def get_duration(self) -> int:
        """Retourne la durée totale en millisecondes"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            return self.media_player.duration()
        return 0
    
    def is_playing(self) -> bool:
        """Retourne True si en cours de lecture"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            return self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        return False
    
    def is_paused(self) -> bool:
        """Retourne True si en pause"""
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
            return self.media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState
        return False