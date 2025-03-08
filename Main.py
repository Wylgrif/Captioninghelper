import os
import json
import sys
import xml.etree.ElementTree as ET
import subprocess
import random
import platform

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QListWidget, QTextEdit, QInputDialog,
    QMessageBox, QFileDialog, QProgressBar, QDialog, QLineEdit,
    QComboBox, QMenu, QAction
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QUrl
from PIL import Image

# Constantes de chemin
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_FOLDER_FILE = os.path.join(SCRIPT_DIR, "last_folder.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
LANGUAGE_FILE = os.path.join(SCRIPT_DIR, "language", "languages.xml")


class ImageCaptioningApp(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()

        # Mémorise le dossier d'images
        self.folder_path = folder_path

        # Prépare l'iconographie
        icon_path = os.path.join(SCRIPT_DIR, "icons", "CappAppIcon.ico")
        self.setWindowIcon(QIcon(icon_path))

        # Gère les fichiers (tags, images cachées) et la config
        self.tag_library_file = os.path.join(folder_path, "tag_library.json")
        self.hidden_images_file = os.path.join(folder_path, "hidden_images.json")
        self.save_last_folder(folder_path)
        self.config = self.load_config()

        # Charge la gestion multilingue
        self.load_languages()

        # Pré-initialise d'éventuels attributs
        self.tag_library = set()
        self.hidden_images = set()
        self.image_files = []
        self.current_index = 0

        # Construit l'UI en premier
        self.setup_ui()

        # Sélectionne la langue (ré-étiquette l'UI) - possible APRES setup_ui()
        self.set_language(self.config.get('language', 'English'))

        # Charge les images cachées et la liste d'images
        self.load_hidden_images()
        self.load_image_list()

        # Charge la bibliothèque de tags
        self.load_tag_library()

        # S'il y a des images, on affiche la première
        if self.image_files:
            self.load_image()
            self.update_progress_bar()
        else:
            QMessageBox.critical(self, "Error", "No images found in the specified folder.")


    def setup_ui(self):
        """
        Construit l'interface utilisateur et définit tous les widgets
        """
        try:
            self.setWindowTitle("Image Captioning Application")
            self.setGeometry(100, 100, 800, 600)

            # Zone centrale
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)

            # Conteneur pour l'image
            image_container = QWidget()
            image_layout = QVBoxLayout(image_container)
            image_layout.setAlignment(Qt.AlignCenter)

            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setContextMenuPolicy(Qt.CustomContextMenu)#
            self.image_label.customContextMenuRequested.connect(self.show_context_menu)#
            self.image_label.setObjectName("image_label")
            image_layout.addWidget(self.image_label)

            self.image_name_label = QLabel()
            self.image_name_label.setStyleSheet("font-size: 16px;")
            self.image_name_label.setAlignment(Qt.AlignCenter)
            self.image_name_label.setObjectName("image_name_label")
            image_layout.addWidget(self.image_name_label)

            main_layout.addWidget(image_container)

            # Bloc : Tag library
            tag_library_layout = QHBoxLayout()
            main_layout.addLayout(tag_library_layout)

            tag_library_label = QLabel("Tag Library:")
            tag_library_label.setObjectName("tag_library_label")
            tag_library_label.setStyleSheet("font-size: 12px;")
            tag_library_layout.addWidget(tag_library_label)

            self.tags_listbox = QListWidget()
            self.tags_listbox.setObjectName("tags_listbox")
            self.tags_listbox.setFixedHeight(120)
            tag_library_layout.addWidget(self.tags_listbox)

            # Boutons d'action sur la Tag library
            tag_buttons_layout = QVBoxLayout()
            tag_library_layout.addLayout(tag_buttons_layout)

            add_tag_button = QPushButton("Add Tag")
            add_tag_button.setObjectName("add_tag_button")
            add_tag_button.clicked.connect(self.add_to_library)
            tag_buttons_layout.addWidget(add_tag_button)

            remove_tag_button = QPushButton("Remove Tag")
            remove_tag_button.setObjectName("remove_tag_button")
            remove_tag_button.clicked.connect(self.remove_from_library)
            tag_buttons_layout.addWidget(remove_tag_button)

            convert_to_jpg_button = QPushButton("Convertir tout en JPG")
            convert_to_jpg_button.setObjectName("convert_to_jpg_button")
            convert_to_jpg_button.clicked.connect(lambda: self.convert_to_jpg(self.folder_path))
            tag_buttons_layout.addWidget(convert_to_jpg_button)

            # Label pour les tags d'une image
            image_tags_label = QLabel("Tags Associated with Image:")
            image_tags_label.setObjectName("image_tags_label")
            image_tags_label.setStyleSheet("font-size: 12px;")
            image_tags_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(image_tags_label)

            # Zone de texte pour les tags liés à l'image en cours
            self.image_tags_display = QTextEdit()
            self.image_tags_display.setFixedHeight(60)
            self.image_tags_display.setObjectName("image_tags_display")
            main_layout.addWidget(self.image_tags_display)

            # Bloc de boutons sous l'éditeur
            actions_layout = QHBoxLayout()
            main_layout.addLayout(actions_layout)

            prev_button = QPushButton("Previous Image")
            prev_button.setObjectName("prev_button")
            prev_button.clicked.connect(self.prev_image)
            actions_layout.addWidget(prev_button)

            next_button = QPushButton("Next Image")
            next_button.setObjectName("next_button")
            next_button.clicked.connect(self.next_image)
            actions_layout.addWidget(next_button)

            random_button = QPushButton("Random Image")
            random_button.setObjectName("random_button")
            random_button.clicked.connect(self.random_image)
            actions_layout.addWidget(random_button)

            apply_tag_button = QPushButton("Apply Tag")
            apply_tag_button.setObjectName("apply_tag_button")
            apply_tag_button.clicked.connect(self.apply_tag)
            actions_layout.addWidget(apply_tag_button)

            add_temp_tag_button = QPushButton("Add Tag (Temporary)")
            add_temp_tag_button.setObjectName("add_temp_tag_button")
            add_temp_tag_button.clicked.connect(self.add_temp_tag)
            actions_layout.addWidget(add_temp_tag_button)

            remove_tag_button = QPushButton("Remove Tag")
            remove_tag_button.setObjectName("remove_tag_button")
            remove_tag_button.clicked.connect(self.remove_tag)
            actions_layout.addWidget(remove_tag_button)

            add_tag_to_all_images = QPushButton("Add Tag To All Images")
            add_tag_to_all_images.setObjectName("add_tag_to_all_images")
            add_tag_to_all_images.clicked.connect(self.add_tag_to_all_images)
            actions_layout.addWidget(add_tag_to_all_images)

            hide_image_button = QPushButton("Hide Image")
            hide_image_button.setObjectName("hide_image_button")
            hide_image_button.clicked.connect(self.hide_image)
            actions_layout.addWidget(hide_image_button)

            send_to_ollama_button = QPushButton("Send to Ollama")
            send_to_ollama_button.setObjectName("send_to_ollama_button")
            send_to_ollama_button.clicked.connect(self.send_to_ollama)
            actions_layout.addWidget(send_to_ollama_button)

            # Label de progression
            self.progress_label = QLabel()
            self.progress_label.setStyleSheet("font-size: 12px;")
            self.progress_label.setAlignment(Qt.AlignCenter)
            self.progress_label.setObjectName("progress_label")
            main_layout.addWidget(self.progress_label)

            # Barre de progression
            self.progress_bar = QProgressBar()
            self.progress_bar.setObjectName("progress_bar")
            main_layout.addWidget(self.progress_bar)

            # Bloc du bas
            bottom_layout = QHBoxLayout()
            main_layout.addLayout(bottom_layout)
            bottom_layout.addStretch()

            settings_button = QPushButton()
            settings_button.setObjectName("settings_button")
            settings_button.setToolTip("Settings")
            icon_settings = os.path.join(SCRIPT_DIR, "icons", "settings.png")
            if os.path.exists(icon_settings):
                settings_button.setIcon(QIcon(icon_settings))
            settings_button.setIconSize(QSize(32, 32))
            settings_button.setFixedSize(40, 40)
            settings_button.clicked.connect(self.open_settings)
            bottom_layout.addWidget(settings_button)

        except Exception as e:
            print(f"Error in setup_ui: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred while setting up the UI: {str(e)}")


    def open_settings(self):
        """
        Ouvre la boîte de dialogue des paramètres
        """
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(self.current_language.get("settings_dialog_title", "Settings"))
            layout = QVBoxLayout(dialog)

            # Prompt
            prompt_label = QLabel(self.current_language.get("ollama_prompt_label", "Ollama Prompt:"))
            layout.addWidget(prompt_label)
            prompt_input = QLineEdit(self.config.get("prompt", ""))
            layout.addWidget(prompt_input)

            # Modèle
            model_label = QLabel(self.current_language.get("ollama_model_label", "Ollama Model:"))
            layout.addWidget(model_label)
            model_input = QLineEdit(self.config.get("model", ""))
            layout.addWidget(model_input)

            # Choix de la langue
            language_label = QLabel(self.current_language.get("language_label", "Language:"))
            layout.addWidget(language_label)
            language_combo = QComboBox()
            # Alimente la liste des langues depuis self.languages
            language_combo.addItems(self.languages.keys())
            language_combo.setCurrentText(self.config.get('language', 'English'))
            layout.addWidget(language_combo)

            # Boutons (Sauver / Réinitialiser)
            buttons_layout = QHBoxLayout()
            save_button = QPushButton(self.current_language.get("save_button", "Save"))
            save_button.clicked.connect(lambda: self.save_settings(
                prompt_input.text(),
                model_input.text(),
                language_combo.currentText(),
                dialog
            ))
            buttons_layout.addWidget(save_button)

            reset_button = QPushButton(self.current_language.get("reset_button", "Reset to Default"))
            reset_button.clicked.connect(lambda: self.reset_to_default(prompt_input, model_input, language_combo))
            buttons_layout.addWidget(reset_button)

            layout.addLayout(buttons_layout)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while opening settings: {str(e)}")
            print(f"Error in open_settings: {str(e)}")

    # Définir la méthode au niveau de la classe, et non imbriquée dans open_settings
    def show_context_menu(self, position):
        menu = QMenu()
        
        copy_image_text = self.current_language.get("context_copy_image", "Copier l'image")
        copy_image_action = QAction(copy_image_text, self)
        copy_image_action.triggered.connect(self.copy_image)
        menu.addAction(copy_image_action)

        copy_path_text = self.current_language.get("context_copy_path", "Copier le chemin d'accès")
        copy_path_action = QAction(copy_path_text, self)
        copy_path_action.triggered.connect(lambda: self.copy_to_clipboard(self.image_path))
        menu.addAction(copy_path_action)

        open_location_text = self.current_language.get("context_open_file_location", "Ouvrir l'emplacement du fichier")
        open_location_action = QAction(open_location_text, self)
        open_location_action.triggered.connect(self.open_file_location)
        menu.addAction(open_location_action)

        open_app_text = self.current_language.get("context_open_with_default_app", "Ouvrir avec l'application par défaut")
        open_image_action = QAction(open_app_text, self)
        open_image_action.triggered.connect(self.open_image_with_default_app)
        menu.addAction(open_image_action)

        menu.exec_(self.image_label.mapToGlobal(position))



    # ======================
    #  FONCTIONS DE L'UI
    # ======================

    def load_image_list(self):
        """
        Charge la liste des images en excluant les images cachées
        """
        files = os.listdir(self.folder_path)
        self.image_files = [
            f for f in files
            if os.path.isfile(os.path.join(self.folder_path, f))
            and f.lower().endswith(('png', 'jpg', 'jpeg'))
            and f not in self.hidden_images
        ]

    def load_image(self):
        if not self.image_files:
            return
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        self.image_path = image_path  # Stocker le chemin dans l'attribut
        image = Image.open(image_path)
        image.thumbnail((600, 400))
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)
        self.image_name_label.setText(os.path.basename(image_path))
        self.load_tags()

    def load_tags(self):
        """
        Charge les tags d'une image .txt
        """
        image_name = os.path.splitext(self.image_files[self.current_index])[0]
        tags_file = os.path.join(self.folder_path, f"{image_name}.txt")

        tags = []
        if os.path.exists(tags_file):
            with open(tags_file, "r", encoding="utf-8") as f:
                tags = f.read().strip().split(",")

        self.image_tags_display.clear()
        if tags:
            self.image_tags_display.setText(", ".join(tags))

    def save_tags(self):
        """
        Sauvegarde les tags liés à l'image courante
        """
        if not self.image_files:
            return
        # Ne pas sauvegarder si l'image est cachée
        if self.image_files[self.current_index] in self.hidden_images:
            return

        image_name = os.path.splitext(self.image_files[self.current_index])[0]
        tags_file = os.path.join(self.folder_path, f"{image_name}.txt")

        tags_text = self.image_tags_display.toPlainText().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        with open(tags_file, "w", encoding="utf-8") as f:
            f.write(", ".join(tags))
        self.update_progress_bar()


    def update_progress_bar(self):
        """
        Met à jour la barre de progression en comptant les .txt vs images
        """
        all_files = os.listdir(self.folder_path)
        txt_files = len([f for f in all_files if f.endswith(".txt")])
        total_images = len(self.image_files) + len(self.hidden_images)

        if total_images > 0:
            progress = (txt_files / total_images) * 100
        else:
            progress = 0

        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(f"Progress: {txt_files} / {total_images} images captioned")


    # ======================
    #  FONCTIONS DE TAG
    # ======================

    def add_to_library(self):
        new_tag, ok = QInputDialog.getText(self, "Add Tag", "Enter a new tag:")
        if ok and new_tag and new_tag not in self.tag_library:
            self.tag_library.add(new_tag)
            self.update_tag_library()
            self.save_tag_library()

    def remove_from_library(self):
        selected_tag = self.tags_listbox.currentItem()
        if selected_tag and selected_tag.text() in self.tag_library:
            self.tag_library.remove(selected_tag.text())
            self.update_tag_library()
            self.save_tag_library()

    def save_tag_library(self):
        with open(self.tag_library_file, "w", encoding="utf-8") as f:
            json.dump(sorted(list(self.tag_library)), f, ensure_ascii=False, indent=4)
        QMessageBox.information(self, "Success", "Tag library automatically saved in the folder.")

    def load_tag_library(self):
        if os.path.exists(self.tag_library_file):
            with open(self.tag_library_file, "r", encoding="utf-8") as f:
                self.tag_library = set(json.load(f))
        self.update_tag_library()

    def update_tag_library(self):
        self.tags_listbox.clear()
        for tag in sorted(self.tag_library):
            self.tags_listbox.addItem(tag)

    def apply_tag(self):
        selected_tag = self.tags_listbox.currentItem()
        if not selected_tag:
            QMessageBox.warning(self, "Error", "Please select a tag.")
            return

        tags_text = self.image_tags_display.toPlainText().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        if selected_tag.text() not in tags:
            tags.append(selected_tag.text())

        self.image_tags_display.setText(", ".join(tags))
        self.save_tags()

    def add_temp_tag(self):
        new_tag, ok = QInputDialog.getText(self, "Add Tag", "Enter a temporary tag:")
        if ok:
            self.add_tag_to_caption(new_tag)

    def add_tag_to_caption(self, new_tag):
        if not new_tag:
            return
        tags_text = self.image_tags_display.toPlainText().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        if new_tag not in tags:
            tags.append(new_tag)

        self.image_tags_display.setText(", ".join(tags))
        self.save_tags()

    def remove_tag(self):
        tags_text = self.image_tags_display.toPlainText().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        if tags:
            tag_to_remove, ok = QInputDialog.getText(self, "Remove Tag", "Enter the tag to remove:")
            if ok and tag_to_remove and tag_to_remove in tags:
                tags.remove(tag_to_remove)

            self.image_tags_display.setText(", ".join(tags))
            self.save_tags()

    def add_tag_to_all_images(self):
        # Récupère le tag sélectionné dans la liste
        selected_tag = self.tags_listbox.currentItem()
        if not selected_tag:
            error_title = self.current_language.get("error_title", "Error")
            error_msg = self.current_language.get("select_tag_error", "Please select a tag.")
            QMessageBox.warning(self, error_title, error_msg)
            return

        tag_text = selected_tag.text()
        applied_count = 0

        # Itère sur toutes les images dans self.image_files
        for image_file in self.image_files:
            image_name = os.path.splitext(image_file)[0]
            tags_file = os.path.join(self.folder_path, f"{image_name}.txt")
            
            # Charge les tags existants pour cette image
            if os.path.exists(tags_file):
                with open(tags_file, "r", encoding="utf-8") as f:
                    file_tags = [t.strip() for t in f.read().strip().split(",") if t.strip()]
            else:
                file_tags = []

            # Si le tag n'est pas déjà présent, l'ajouter
            if tag_text not in file_tags:
                file_tags.append(tag_text)
                with open(tags_file, "w", encoding="utf-8") as f:
                    f.write(", ".join(file_tags))
                applied_count += 1

        # Met à jour la barre de progression après modifications
        self.update_progress_bar()
        
        # Affiche un message de succès (vous pouvez paramétrer ce message dans votre fichier de langues)
        success_title = self.current_language.get("success_title", "Success")
        success_msg_template = self.current_language.get("add_tag_all_success", "Tag '{tag}' has been applied to {count} images.")
        success_msg = success_msg_template.format(tag=tag_text, count=applied_count)
        QMessageBox.information(self, success_title, success_msg)


    # ======================
    #  FONCTIONS DE NAVIGATION
    # ======================

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image()

    def random_image(self):
        if not self.image_files:
            return
        self.current_index = random.randint(0, len(self.image_files) - 1)
        self.load_image()

    # ======================
    #  FONCTIONS HIDE
    # ======================

    def hide_image(self):
        if not self.image_files:
            return
        current_image = self.image_files[self.current_index]
        if current_image not in self.hidden_images:
            self.hidden_images.add(current_image)
            self.save_hidden_images()
            QMessageBox.information(self, "Success", f"The image {current_image} has been hidden.")
            # Après le masquage, on passe à l'image suivante
            self.load_image_list()
            if self.current_index >= len(self.image_files):
                self.current_index = 0
            if self.image_files:
                self.load_image()
            else:
                QMessageBox.information(self, "Info", "No more images to show.")
        else:
            QMessageBox.information(self, "Info", "Image already hidden.")

    def save_hidden_images(self):
        with open(self.hidden_images_file, "w", encoding="utf-8") as f:
            json.dump(list(self.hidden_images), f, ensure_ascii=False, indent=4)

    def load_hidden_images(self):
        if os.path.exists(self.hidden_images_file):
            with open(self.hidden_images_file, "r", encoding="utf-8") as f:
                self.hidden_images = set(json.load(f))

    # ======================
    #  FONCTIONS OLLAMA
    # ======================

    def send_to_ollama(self):
        """
        Envoie l'image courante à Ollama pour analyse / génération de tags
        """
        if not self.image_files:
            return

        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])

        command = ["ollama", "run", self.config["model"], image_path, self.config["prompt"]]

        try:
            if platform.system() == "Windows":
                # Sous Windows, pour ne pas ouvrir de console
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Sous Linux/Mac, rediriger stderr vers /dev/null
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    stderr=subprocess.DEVNULL
                )

            if result.returncode == 0:
                output = result.stdout.strip()
                self.add_tag_to_caption(output)
            else:
                error_message = result.stderr.strip()
                QMessageBox.critical(self, "Error", f"Ollama returned an error: {error_message}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


    # ======================
    #  FONCTIONS SETTINGS
    # ======================

    def save_settings(self, new_prompt, new_model, new_language, dialog):
        """
        Sauvegarde les paramètres entrés dans la dialog
        """
        self.config["prompt"] = new_prompt
        self.config["model"] = new_model
        self.config["language"] = new_language
        self.save_config()
        self.set_language(new_language)
        dialog.accept()

    def reset_to_default(self, prompt_input, model_input, language_combo):
        """
        Réinitialise les paramètres aux valeurs par défaut
        """
        default_prompt = ("Describe this image as a training prompt, using short, "
                          "precise terms separated by commas. You'll answer only "
                          "with these descriptive terms.")
        default_model = "llava"
        default_language = "English"

        prompt_input.setText(default_prompt)
        model_input.setText(default_model)
        language_combo.setCurrentText(default_language)

        self.config["prompt"] = default_prompt
        self.config["model"] = default_model
        self.config["language"] = default_language
        self.save_config()
        self.set_language(default_language)
        QMessageBox.information(self, "Reset", "Settings have been reset to default.")


    # ======================
    #  FONCTIONS FICHIERS / CONFIG
    # ======================

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        # Valeurs par défaut
        default_config = {
            "prompt": ("Describe this image as a training prompt, using short, "
                       "precise terms separated by commas. You'll answer only "
                       "with these descriptive terms."),
            "model": "llava"
        }

        for key, value in default_config.items():
            if key not in config:
                config[key] = value

        # Sauvegarde la config potentiellement mise à jour
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

        return config

    def convert_to_jpg(self, input_folder):
        if not os.path.exists(input_folder):
            QMessageBox.warning(self, "Error", f"Le dossier {input_folder} n'existe pas.")
            return

        supported_formats = ('.png', '.webp', '.jpeg', '.gif', '.bmp', '.tiff')
        files = os.listdir(input_folder)
        converted_count = 0

        for file in files:
            if file.lower().endswith(supported_formats):
                original_path = os.path.join(input_folder, file)
                try:
                    with Image.open(original_path) as img:
                        rgb_img = img.convert('RGB')
                        base_name = os.path.splitext(file)[0]
                        jpg_name = base_name + '.jpg'
                        jpg_path = os.path.join(input_folder, jpg_name)

                        counter = 1
                        # S'assure de ne pas écraser un .jpg existant
                        while os.path.exists(jpg_path):
                            jpg_name = f"{base_name}_{counter}.jpg"
                            jpg_path = os.path.join(input_folder, jpg_name)
                            counter += 1

                        rgb_img.save(jpg_path, 'JPEG')
                        os.remove(original_path)
                        converted_count += 1
                except Exception as e:
                    print(f"Erreur lors de la conversion de {file}: {str(e)}")

        QMessageBox.information(self, "Success", f"{converted_count} images ont été converties en JPG avec succès !")


    def save_last_folder(self, folder_path):
        """
        Sauvegarde le dernier dossier utilisé
        """
        with open(LAST_FOLDER_FILE, 'w', encoding='utf-8') as f:
            json.dump({"last_folder": folder_path}, f)


    def save_config(self):
        """
        Sauvegarde la config (prompt, model, language...) dans le fichier config.json
        """
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def copy_image(self):
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        # Copy the image to the clipboard
        pixmap = QPixmap(self.image_path)
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)

    def copy_to_clipboard(self, text):
        # Copy text to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def open_file_location(self):
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        folder = os.path.dirname(image_path)
        if platform.system() == 'Windows':
            os.startfile(folder)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', folder])
        else:  # Linux
            subprocess.call(['xdg-open', folder])

    def open_image_with_default_app(self):
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        # Open the image with the default application
        os.startfile(self.image_path)

    def load_languages(self):
        """
        Charge le fichier languages.xml dans self.languages
        """
        self.languages = {}
        if os.path.exists(LANGUAGE_FILE):
            tree = ET.parse(LANGUAGE_FILE)
            root = tree.getroot()
            for lang in root.findall('language'):
                lang_name = lang.get('name')
                self.languages[lang_name] = {}
                for string in lang.findall('string'):
                    self.languages[lang_name][string.get('name')] = string.text
        else:
            print("Warning: No languages.xml found")

    def set_language(self, lang_name):
        """
        Sélectionne la langue et rafraîchit l'UI
        """
        if lang_name in self.languages:
            self.current_language = self.languages[lang_name]
        else:
            self.current_language = self.languages.get('English', {})
        self.retranslate_ui()

    def retranslate_ui(self):
        """
        Met à jour l'affichage des textes en fonction de la langue courante
        """
        # Titre de la fenêtre
        title = self.current_language.get('window_title', "Image Captioning Application")
        self.setWindowTitle(title)

        # Mise à jour du label principal "Tag Library"
        tag_label = self.findChild(QLabel, "tag_library_label")
        if tag_label:
            tag_label.setText(self.current_language.get('tag_library_label', "Tag Library:"))

        # Mise à jour du texte de la zone "image_tags_display" — attention, ici on ne veut pas écraser le contenu
        # s'il s'agit vraiment du texte de l'utilisateur. Généralement, on n'écrase pas l'éditeur en place,
        # sauf si on veut juste changer le label. Si le label est distinct, on fait autrement.
        # Ici on va juste modifier la variable s'il n'y a rien dedans, sinon on laisse l'utilisateur.
        # Néanmoins, pour respecter la logique initiale:
        image_tags_label_widget = self.findChild(QLabel, "image_tags_label")
        if image_tags_label_widget:
            image_tags_label_widget.setText(self.current_language.get('image_tags_label', "Tags Associated with Image:"))

        # Boutons
        add_tag_btn = self.findChild(QPushButton, "add_tag_button")
        if add_tag_btn:
            add_tag_btn.setText(self.current_language.get('add_tag_button', "Add Tag"))

        remove_tag_btn = self.findChild(QPushButton, "remove_tag_button")
        if remove_tag_btn:
            remove_tag_btn.setText(self.current_language.get('remove_tag_button', "Remove Tag"))

        convert_jpg_btn = self.findChild(QPushButton, "convert_to_jpg_button")
        if convert_jpg_btn:
            convert_jpg_btn.setText(self.current_language.get('convert_to_jpg_button', "Convert All to JPG"))

        settings_btn = self.findChild(QPushButton, "settings_button")
        if settings_btn:
            settings_btn.setToolTip(self.current_language.get('settings_button_tooltip', "Settings"))

        progress_label = self.findChild(QLabel, "progress_label")
        if progress_label:
            # Indiquer juste un label, ex. "Progress:" ou le texte complet
            # Pour avoir un label dynamique, on peut paramétrer autrement.
            progress_label.setText(self.current_language.get('progress_label', "Progress:"))

        # Autres boutons de navigation
        prev_btn = self.findChild(QPushButton, "prev_button")
        if prev_btn:
            prev_btn.setText(self.current_language.get('prev_button', "Previous Image"))

        next_btn = self.findChild(QPushButton, "next_button")
        if next_btn:
            next_btn.setText(self.current_language.get('next_button', "Next Image"))

        random_btn = self.findChild(QPushButton, "random_button")
        if random_btn:
            random_btn.setText(self.current_language.get('random_button', "Random Image"))

        apply_btn = self.findChild(QPushButton, "apply_tag_button")
        if apply_btn:
            apply_btn.setText(self.current_language.get('apply_tag_button', "Apply Tag"))

        add_temp_btn = self.findChild(QPushButton, "add_temp_tag_button")
        if add_temp_btn:
            add_temp_btn.setText(self.current_language.get('add_temp_tag_button', "Add Tag (Temporary)"))

        remove_tag_btn2 = self.findChild(QPushButton, "remove_tag_button")
        if remove_tag_btn2:
            remove_tag_btn2.setText(self.current_language.get('remove_tag_button', "Remove Tag"))

        add_tag_all_btn = self.findChild(QPushButton, "add_tag_to_all_images")
        if add_tag_all_btn:
            add_tag_all_btn.setText(self.current_language.get("add_tag_to_all_images", "Add Tag To All Images"))


        hide_image_btn = self.findChild(QPushButton, "hide_image_button")
        if hide_image_btn:
            hide_image_btn.setText(self.current_language.get('hide_image_button', "Hide Image"))

        send_ollama_btn = self.findChild(QPushButton, "send_to_ollama_button")
        if send_ollama_btn:
            send_ollama_btn.setText(self.current_language.get('send_to_ollama_button', "Send to Ollama"))


def main():
    app = QApplication(sys.argv)

    # Application icon
    app_icon = QIcon(os.path.join(SCRIPT_DIR, "icons", "CappAppIcon.ico"))
    app.setWindowIcon(app_icon)

    # Charge le dernier dossier utilisé
    def load_last_folder():
        if os.path.exists(LAST_FOLDER_FILE):
            with open(LAST_FOLDER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("last_folder", "")
        return ""

    last_folder = load_last_folder()
    folder_path = QFileDialog.getExistingDirectory(None, "Select the folder containing images", last_folder)

    if folder_path:
        window = ImageCaptioningApp(folder_path)
        window.show()
        sys.exit(app.exec_())
    else:
        print("No folder was selected.")


if __name__ == "__main__":
    main()
