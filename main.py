#!/usr/bin/env python3
"""
MusicPartMate - Gestionnaire de partitions musicales
Point d'entrée principal de l'application (PySide6)
"""

import sys
import os
from pathlib import Path

# Configurer les variables d'environnement Qt AVANT tout import Qt
os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'
os.environ['QT_DEBUG_PLUGINS'] = '0'  # Mettre à 1 pour debug
os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.debug=false'

# Variables spécifiques pour améliorer le support vidéo
os.environ['QT_OPENGL'] = 'software'  # Force le rendu software pour éviter les problèmes GPU
os.environ['QT_ANGLE_PLATFORM'] = 'd3d11'  # Utilise DirectX 11 sur Windows
os.environ['QT_QUICK_BACKEND'] = 'software'  # Rendu software pour Qt Quick

# Trouver le chemin des plugins Qt
try:
    import PySide6
    pyside_path = Path(PySide6.__file__).parent
    
    # Essayer différents chemins pour les plugins
    plugin_paths = [
        pyside_path / 'Qt6' / 'plugins',
        pyside_path / 'plugins'
    ]
    
    for plugin_path in plugin_paths:
        if plugin_path.exists():
            os.environ['QT_PLUGIN_PATH'] = str(plugin_path)
            print(f"🔌 Plugins Qt trouvés: {plugin_path}")
            break
    else:
        print("⚠️ Dossier plugins Qt non trouvé")

except ImportError:
    print("⚠️ PySide6 non trouvé")

# Ajouter le dossier src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """Point d'entrée principal de l'application"""
    
    # Configuration de l'application
    app = QApplication(sys.argv)
    app.setApplicationName("MusicPartMate")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MusicPartMate")
    
    # Style optionnel
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTreeWidget {
            background-color: white;
            border: 1px solid #ddd;
        }
        QToolBar {
            background-color: #e9e9e9;
            border: none;
        }
    """)
    
    # Créer et afficher la fenêtre principale
    try:
        window = MainWindow()
        window.show()
        
        # Message d'information sur le multimédia
        print("🎵 MusicPartMate démarré")
        print("💡 Si les médias ne se lisent pas, ils s'ouvriront dans des applications externes")
        
        # Démarrer la boucle d'événements
        return app.exec()
        
    except Exception as e:
        print(f"Erreur lors du démarrage de l'application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())