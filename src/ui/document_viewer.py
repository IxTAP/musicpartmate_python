"""
Widget pour afficher les documents (PDF, TXT, images, etc.) - Version PySide6 améliorée
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QTextEdit, 
    QHBoxLayout, QPushButton, QSpinBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QFont, QPainter, QPen, QTextDocument
from pathlib import Path
from typing import Optional, List
import fitz  # PyMuPDF pour les PDF
import tempfile
import base64
import io


class DocumentLoadWorker(QThread):
    """Worker thread pour charger les documents en arrière-plan"""
    
    document_loaded = Signal(list)  # Liste des pages/contenu chargées
    progress_updated = Signal(int)  # Progression du chargement
    error_occurred = Signal(str)    # Erreur lors du chargement
    
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
        self.should_stop = False
    
    def stop(self):
        """Arrête le chargement"""
        self.should_stop = True
    
    def run(self):
        """Charge le document en arrière-plan"""
        try:
            suffix = self.file_path.suffix.lower()
            
            if suffix == '.pdf':
                self.load_pdf()
            elif suffix in ['.txt', '.md']:
                self.load_text()
            elif suffix == '.docx':
                self.load_docx()
            elif suffix == '.odt':
                self.load_odt()
            elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']:
                self.load_image()
            else:
                self.error_occurred.emit(f"Format non supporté: {suffix}")
                
        except Exception as e:
            self.error_occurred.emit(f"Erreur lors du chargement: {str(e)}")
    
    def load_pdf(self):
        """Charge un fichier PDF"""
        doc = fitz.open(str(self.file_path))
        pages = []
        
        total_pages = len(doc)
        for page_num in range(total_pages):
            if self.should_stop:
                break
                
            page = doc.load_page(page_num)
            
            # Convertir en image avec une résolution raisonnable
            matrix = fitz.Matrix(1.5, 1.5)  # Zoom 150%
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.tobytes("ppm")
            
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            
            pages.append({
                'type': 'image',
                'content': pixmap,
                'page_number': page_num + 1
            })
            
            # Mettre à jour la progression
            progress = int((page_num + 1) / total_pages * 100)
            self.progress_updated.emit(progress)
        
        doc.close()
        
        if not self.should_stop:
            self.document_loaded.emit(pages)
    
    def load_text(self):
        """Charge un fichier texte"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Essayer avec d'autres encodages
            try:
                with open(self.file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception:
                try:
                    with open(self.file_path, 'r', encoding='cp1252') as f:
                        content = f.read()
                except Exception:
                    # Dernier recours
                    with open(self.file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='replace')
        
        pages = [{
            'type': 'text',
            'content': content,
            'page_number': 1
        }]
        
        self.progress_updated.emit(100)
        self.document_loaded.emit(pages)
    
    def load_docx(self):
        """Charge un fichier Word avec support des images"""
        try:
            # Méthode 1: Essayer mammoth pour un meilleur rendu HTML
            try:
                import mammoth
                
                with open(self.file_path, 'rb') as docx_file:
                    result = mammoth.convert_to_html(docx_file)
                    html_content = result.value
                    
                    # Convertir en HTML enrichi
                    pages = [{
                        'type': 'html',
                        'content': html_content,
                        'page_number': 1
                    }]
                    
                    self.progress_updated.emit(100)
                    self.document_loaded.emit(pages)
                    return
                    
            except ImportError:
                print("📝 Mammoth non disponible, utilisation de python-docx")
            
            # Méthode 2: python-docx standard
            from docx import Document
            doc = Document(str(self.file_path))
            
            # Extraire le contenu avec les images
            content_parts = []
            images = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content_parts.append(paragraph.text)
                
                # Chercher les images dans le paragraphe
                for run in paragraph.runs:
                    for inline_shape in run.element.xpath('.//a:blip'):
                        try:
                            # Extraire l'image
                            image_id = inline_shape.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                            if image_id:
                                image_part = doc.part.related_parts[image_id]
                                image_data = image_part.blob
                                images.append(image_data)
                                content_parts.append(f"[Image {len(images)}]")
                        except Exception as e:
                            print(f"Erreur extraction image: {e}")
            
            content = "\n".join(content_parts)
            
            pages = [{
                'type': 'text',
                'content': content,
                'page_number': 1,
                'images': images  # Stocker les images pour affichage ultérieur
            }]
            
            self.progress_updated.emit(100)
            self.document_loaded.emit(pages)
            
        except ImportError:
            self.error_occurred.emit("Module python-docx non installé")
        except Exception as e:
            self.error_occurred.emit(f"Erreur lors de la lecture du fichier Word: {str(e)}")
    
    def load_odt(self):
        """Charge un fichier ODT (OpenDocument Text)"""
        try:
            # Méthode 1: Utiliser odfpy
            try:
                from odf.opendocument import load
                from odf.text import P
                from odf.element import Text
                
                doc = load(str(self.file_path))
                content_parts = []
                
                # Extraire tous les paragraphes
                paragraphs = doc.getElementsByType(P)
                for paragraph in paragraphs:
                    text_content = ""
                    for node in paragraph.childNodes:
                        if node.nodeType == node.TEXT_NODE:
                            text_content += str(node.data)
                        elif hasattr(node, 'childNodes'):
                            for child in node.childNodes:
                                if child.nodeType == child.TEXT_NODE:
                                    text_content += str(child.data)
                    
                    if text_content.strip():
                        content_parts.append(text_content.strip())
                
                content = "\n".join(content_parts)
                
                pages = [{
                    'type': 'text',
                    'content': content,
                    'page_number': 1
                }]
                
                self.progress_updated.emit(100)
                self.document_loaded.emit(pages)
                return
                
            except ImportError:
                print("📝 odfpy non disponible, tentative méthode alternative")
            
            # Méthode 2: Extraction XML manuelle
            import zipfile
            import xml.etree.ElementTree as ET
            
            content_parts = []
            
            with zipfile.ZipFile(str(self.file_path), 'r') as odt_zip:
                # Lire le contenu principal
                try:
                    content_xml = odt_zip.read('content.xml')
                    root = ET.fromstring(content_xml)
                    
                    # Définir les namespaces ODT
                    namespaces = {
                        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
                        'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
                    }
                    
                    # Extraire les paragraphes
                    for para in root.findall('.//text:p', namespaces):
                        para_text = ''.join(para.itertext())
                        if para_text.strip():
                            content_parts.append(para_text.strip())
                    
                    # Extraire les titres
                    for heading in root.findall('.//text:h', namespaces):
                        heading_text = ''.join(heading.itertext())
                        if heading_text.strip():
                            content_parts.append(f"# {heading_text.strip()}")
                    
                except Exception as e:
                    print(f"Erreur parsing XML ODT: {e}")
                    # Fallback: extraction basique
                    content_parts.append("Fichier ODT détecté mais contenu non extractible")
                    content_parts.append("Veuillez installer odfpy pour un meilleur support:")
                    content_parts.append("pip install odfpy")
            
            content = "\n".join(content_parts) if content_parts else "Contenu ODT non extractible"
            
            pages = [{
                'type': 'text',
                'content': content,
                'page_number': 1
            }]
            
            self.progress_updated.emit(100)
            self.document_loaded.emit(pages)
            
        except Exception as e:
            self.error_occurred.emit(f"Erreur lors de la lecture du fichier ODT: {str(e)}")
    
    def load_image(self):
        """Charge une image"""
        pixmap = QPixmap(str(self.file_path))
        
        if pixmap.isNull():
            self.error_occurred.emit("Impossible de charger l'image")
            return
        
        pages = [{
            'type': 'image',
            'content': pixmap,
            'page_number': 1
        }]
        
        self.progress_updated.emit(100)
        self.document_loaded.emit(pages)


class DocumentViewer(QWidget):
    """Widget pour afficher les documents"""
    
    def __init__(self):
        super().__init__()
        self.current_document = None
        self.pages = []
        self.current_page = 0
        self.zoom_level = 1.0
        self.worker = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Barre d'outils en haut
        self.create_toolbar(layout)
        
        # Barre de progression (cachée par défaut)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Zone de contenu avec scroll
        self.scroll_area = QScrollArea()
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self.scroll_area.setWidget(self.content_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.scroll_area)
        
        # Message par défaut
        self.show_welcome_message()
    
    def create_toolbar(self, parent_layout):
        """Crée la barre d'outils"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # Navigation des pages
        self.prev_button = QPushButton("◄")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self.previous_page)
        toolbar_layout.addWidget(self.prev_button)
        
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setValue(1)
        self.page_spinbox.setEnabled(False)
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        toolbar_layout.addWidget(self.page_spinbox)
        
        self.page_label = QLabel("de 1")
        toolbar_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton("►")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_page)
        toolbar_layout.addWidget(self.next_button)
        
        toolbar_layout.addWidget(QFrame())  # Séparateur
        
        # Contrôles de zoom
        self.zoom_out_button = QPushButton("🔍-")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(self.zoom_out_button)
        
        self.zoom_label = QLabel("100%")
        toolbar_layout.addWidget(self.zoom_label)
        
        self.zoom_in_button = QPushButton("🔍+")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(self.zoom_in_button)
        
        self.fit_button = QPushButton("Ajuster")
        self.fit_button.clicked.connect(self.fit_to_window)
        toolbar_layout.addWidget(self.fit_button)
        
        toolbar_layout.addStretch()  # Pousser vers la gauche
        
        parent_layout.addWidget(toolbar_frame)
    
    def show_welcome_message(self):
        """Affiche un message de bienvenue"""
        self.clear_content()
        
        welcome_label = QLabel("📄 Aucun document sélectionné")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #666;
                padding: 50px;
            }
        """)
        
        self.content_layout.addWidget(welcome_label)
    
    def clear_content(self):
        """Vide le contenu actuel"""
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
    
    def load_document(self, file_path: Path):
        """
        Charge et affiche un document
        
        Args:
            file_path: Chemin vers le document à charger
        """
        if not file_path.exists():
            self.show_error(f"Fichier non trouvé: {file_path}")
            return
        
        # Arrêter le chargement précédent si en cours
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        # Réinitialiser l'état
        self.current_document = file_path
        self.pages = []
        self.current_page = 0
        self.zoom_level = 1.0
        
        # Afficher la barre de progression
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        # Démarrer le chargement en arrière-plan
        self.worker = DocumentLoadWorker(file_path)
        self.worker.document_loaded.connect(self.on_document_loaded)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.start()
    
    def on_document_loaded(self, pages: List[dict]):
        """Appelé quand le document est chargé"""
        self.pages = pages
        self.progress_bar.hide()
        
        if pages:
            self.current_page = 0
            self.update_navigation()
            self.display_current_page()
        else:
            self.show_error("Aucun contenu trouvé dans le document")
    
    def update_navigation(self):
        """Met à jour les contrôles de navigation"""
        total_pages = len(self.pages)
        
        if total_pages > 0:
            self.page_spinbox.setMaximum(total_pages)
            self.page_spinbox.setValue(self.current_page + 1)
            self.page_spinbox.setEnabled(True)
            
            self.page_label.setText(f"de {total_pages}")
            
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(self.current_page < total_pages - 1)
        else:
            self.page_spinbox.setEnabled(False)
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
    
    def display_current_page(self):
        """Affiche la page actuelle"""
        if not self.pages or self.current_page >= len(self.pages):
            return
        
        self.clear_content()
        
        page_data = self.pages[self.current_page]
        page_type = page_data['type']
        content = page_data['content']
        
        if page_type == 'image':
            self.display_image(content)
        elif page_type == 'text':
            self.display_text(content, page_data.get('images', []))
        elif page_type == 'html':
            self.display_html(content)
    
    def display_image(self, pixmap: QPixmap):
        """Affiche une image"""
        label = QLabel()
        
        # Appliquer le zoom
        if self.zoom_level != 1.0:
            size = pixmap.size()
            new_size = size * self.zoom_level
            pixmap = pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, 
                                 Qt.TransformationMode.SmoothTransformation)
        
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(label)
        
        # Mettre à jour l'affichage du zoom
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def display_text(self, text: str, images: List = None):
        """Affiche du texte avec support des images intégrées"""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # Adapter la police au zoom
        font = text_edit.font()
        font.setPointSize(int(font.pointSize() * self.zoom_level))
        text_edit.setFont(font)
        
        # Si le texte contient des références d'images et qu'on a des images
        if images and "[Image" in text:
            # Créer un document HTML avec les images
            html_content = self.create_html_with_images(text, images)
            text_edit.setHtml(html_content)
        else:
            text_edit.setPlainText(text)
        
        self.content_layout.addWidget(text_edit)
        
        # Mettre à jour l'affichage du zoom
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def display_html(self, html_content: str):
        """Affiche du contenu HTML (pour DOCX avec mammoth)"""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # Adapter la police au zoom
        font = text_edit.font()
        font.setPointSize(int(font.pointSize() * self.zoom_level))
        text_edit.setFont(font)
        
        # Afficher le HTML
        text_edit.setHtml(html_content)
        
        self.content_layout.addWidget(text_edit)
        
        # Mettre à jour l'affichage du zoom
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def create_html_with_images(self, text: str, images: List) -> str:
        """Crée du HTML avec les images intégrées"""
        html_parts = ['<html><body style="font-family: Arial, sans-serif;">']
        
        # Traiter le texte ligne par ligne
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith('[Image ') and line.strip().endswith(']'):
                # Extraire le numéro d'image
                try:
                    import re
                    match = re.search(r'\[Image (\d+)\]', line)
                    if match:
                        image_num = int(match.group(1)) - 1  # Index 0-based
                        if 0 <= image_num < len(images):
                            # Convertir l'image en base64 pour l'intégrer
                            image_data = images[image_num]
                            import base64
                            b64_image = base64.b64encode(image_data).decode()
                            
                            # Déterminer le type MIME (supposer JPEG par défaut)
                            mime_type = "image/jpeg"
                            if image_data.startswith(b'\x89PNG'):
                                mime_type = "image/png"
                            elif image_data.startswith(b'GIF'):
                                mime_type = "image/gif"
                            
                            html_parts.append(f'<img src="data:{mime_type};base64,{b64_image}" style="max-width: 100%; height: auto;" />')
                        else:
                            html_parts.append(f'<p><em>{line}</em></p>')
                    else:
                        html_parts.append(f'<p>{line}</p>')
                except:
                    html_parts.append(f'<p>{line}</p>')
            else:
                if line.strip():
                    # Traitement basique du markdown
                    if line.startswith('# '):
                        html_parts.append(f'<h1>{line[2:]}</h1>')
                    elif line.startswith('## '):
                        html_parts.append(f'<h2>{line[3:]}</h2>')
                    elif line.startswith('### '):
                        html_parts.append(f'<h3>{line[4:]}</h3>')
                    else:
                        html_parts.append(f'<p>{line}</p>')
                else:
                    html_parts.append('<br/>')
        
        html_parts.append('</body></html>')
        return ''.join(html_parts)
    
    def show_error(self, message: str):
        """Affiche un message d'erreur"""
        self.progress_bar.hide()
        self.clear_content()
        
        error_label = QLabel(f"❌ {message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                color: red;
                font-size: 14px;
                padding: 30px;
            }
        """)
        
        self.content_layout.addWidget(error_label)
    
    def previous_page(self):
        """Page précédente"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_navigation()
            self.display_current_page()
    
    def next_page(self):
        """Page suivante"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.update_navigation()
            self.display_current_page()
    
    def go_to_page(self, page_number: int):
        """Va à une page spécifique"""
        if 1 <= page_number <= len(self.pages):
            self.current_page = page_number - 1
            self.update_navigation()
            self.display_current_page()
    
    def zoom_in(self):
        """Zoom avant"""
        self.zoom_level = min(self.zoom_level * 1.25, 5.0)
        self.display_current_page()
    
    def zoom_out(self):
        """Zoom arrière"""
        self.zoom_level = max(self.zoom_level / 1.25, 0.25)
        self.display_current_page()
    
    def fit_to_window(self):
        """Ajuste à la fenêtre"""
        self.zoom_level = 1.0
        self.display_current_page()
    
    def closeEvent(self, event):
        """Nettoyage lors de la fermeture"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().closeEvent(event)