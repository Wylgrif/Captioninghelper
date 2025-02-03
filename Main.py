import os
import json
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QListWidget, QTextEdit, QInputDialog, QMessageBox, QFileDialog, QProgressBar
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PIL import Image
import subprocess
import random
import platform

# Ajoutez ces constantes au début du fichier, juste après les imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_FOLDER_FILE = os.path.join(SCRIPT_DIR, "last_folder.json")

class ImageCaptioningApp(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.tag_library = set()
        self.hidden_images = set()

        self.tag_library_file = os.path.join(folder_path, "tag_library.json")
        self.hidden_images_file = os.path.join(folder_path, "hidden_images.json")

        self.save_last_folder(folder_path)


        # Load hidden images before loading the image list
        self.load_hidden_images()

        # Load only non-hidden images
        self.image_files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
            and f.lower().endswith(('png', 'jpg', 'jpeg'))
            and f not in self.hidden_images  # Exclude hidden images
        ]

        self.current_index = 0

        self.setup_ui()

        self.load_tag_library()

        if self.image_files:
            self.load_image()
            self.update_progress_bar()
        else:
            QMessageBox.critical(self, "Error", "No images found in the specified folder.")

    def setup_ui(self):
        self.setWindowTitle("Image Captioning Application")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.setAlignment(Qt.AlignCenter)  # Centrer le contenu

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)  # Centrer l'image
        image_layout.addWidget(self.image_label)

        self.image_name_label = QLabel()
        self.image_name_label.setStyleSheet("font-size: 16px;")
        self.image_name_label.setAlignment(Qt.AlignCenter)  # Centrer le nom de l'image
        image_layout.addWidget(self.image_name_label)

        main_layout.addWidget(image_container)

        tag_library_layout = QHBoxLayout()
        main_layout.addLayout(tag_library_layout)

        tag_library_label = QLabel("Tag Library:")
        tag_library_label.setStyleSheet("font-size: 12px;")
        tag_library_layout.addWidget(tag_library_label)

        self.tags_listbox = QListWidget()
        self.tags_listbox.setFixedHeight(120)
        tag_library_layout.addWidget(self.tags_listbox)

        tag_buttons_layout = QVBoxLayout()
        tag_library_layout.addLayout(tag_buttons_layout)

        add_tag_button = QPushButton("Add Tag")
        add_tag_button.clicked.connect(self.add_to_library)
        tag_buttons_layout.addWidget(add_tag_button)

        remove_tag_button = QPushButton("Remove Tag")
        remove_tag_button.clicked.connect(self.remove_from_library)
        tag_buttons_layout.addWidget(remove_tag_button)

        image_tags_label = QLabel("Tags Associated with Image:")
        image_tags_label.setStyleSheet("font-size: 12px;")
        main_layout.addWidget(image_tags_label)

        self.image_tags_display = QTextEdit()
        self.image_tags_display.setFixedHeight(60)
        main_layout.addWidget(self.image_tags_display)

        actions_layout = QHBoxLayout()
        main_layout.addLayout(actions_layout)

        prev_button = QPushButton("Previous Image")
        prev_button.clicked.connect(self.prev_image)
        actions_layout.addWidget(prev_button)

        next_button = QPushButton("Next Image")
        next_button.clicked.connect(self.next_image)
        actions_layout.addWidget(next_button)

        random_button = QPushButton("Random Image")
        random_button.clicked.connect(self.random_image)
        actions_layout.addWidget(random_button)

        apply_tag_button = QPushButton("Apply Tag")
        apply_tag_button.clicked.connect(self.apply_tag)
        actions_layout.addWidget(apply_tag_button)

        add_temp_tag_button = QPushButton("Add Tag (Temporary)")
        add_temp_tag_button.clicked.connect(self.add_temp_tag)
        actions_layout.addWidget(add_temp_tag_button)

        remove_tag_button = QPushButton("Remove Tag")
        remove_tag_button.clicked.connect(self.remove_tag)
        actions_layout.addWidget(remove_tag_button)

        hide_image_button = QPushButton("Hide Image")
        hide_image_button.clicked.connect(self.hide_image)
        actions_layout.addWidget(hide_image_button)

        send_to_ollama_button = QPushButton("Send to Ollama")
        send_to_ollama_button.clicked.connect(self.send_to_ollama)
        actions_layout.addWidget(send_to_ollama_button)

        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 12px;")
        main_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

    def load_image(self):
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        image = Image.open(image_path)
        image.thumbnail((600, 400))
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_label.setPixmap(pixmap)
        self.image_name_label.setText(os.path.basename(image_path))

        self.load_tags()

    def load_tags(self):
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
        # Don't save tags for hidden images
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
        file_list = os.listdir(self.folder_path)
        txt_files = len([
            f for f in file_list
            if f.endswith(".txt")
        ])
        total_images = len(self.image_files) + len(self.hidden_images)

        progress = (txt_files / total_images) if total_images > 0 else 0
        self.progress_bar.setValue(int(progress * 100))

        self.progress_label.setText(f"Progress: {txt_files} / {total_images} images captioned")

    def add_to_library(self):
        new_tag, ok = QInputDialog.getText(self, "Add Tag", "Enter a new tag:")
        if ok and new_tag and new_tag not in self.tag_library:
            self.tag_library.add(new_tag)
            self.update_tag_library()

    def remove_from_library(self):
        selected_tag = self.tags_listbox.currentItem()
        if selected_tag and selected_tag.text() in self.tag_library:
            self.tag_library.remove(selected_tag.text())
            self.update_tag_library()

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
        if new_tag:
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

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image()

    def hide_image(self):
        current_image = self.image_files[self.current_index]
        if current_image not in self.hidden_images:
            self.hidden_images.add(current_image)
            self.save_hidden_images()
            QMessageBox.information(self, "Success", f"The image {current_image} has been hidden.")
            self.next_image()

    def save_hidden_images(self):
        with open(self.hidden_images_file, "w", encoding="utf-8") as f:
            json.dump(list(self.hidden_images), f, ensure_ascii=False, indent=4)

    def load_hidden_images(self):
        if os.path.exists(self.hidden_images_file):
            with open(self.hidden_images_file, "r", encoding="utf-8") as f:
                self.hidden_images = set(json.load(f))

    def random_image(self):
        self.current_index = random.randint(0, len(self.image_files) - 1)
        self.load_image()

    def send_to_ollama(self):
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
    
        # Construct the command to send to Ollama
        command = ["ollama", "run", "llava", image_path, " Describe this image as a training prompt, using short, precise terms separated by commas. You'll answer only with these descriptive terms."]
    
        try:
            # Run the command and capture the output
            if platform.system() == "Windows":
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", stderr=subprocess.DEVNULL)
        
            # Check if the command was successful
            if result.returncode == 0:
                # Extract the output from the result
                output = result.stdout.strip()
            
                # Add the output as tags to the image
                self.add_tag_to_caption(output)
            else:
                # Handle errors if the command failed
                error_message = result.stderr.strip()
                QMessageBox.critical(self, "Error", f"Ollama returned an error: {error_message}")
    
        except Exception as e:
            # Handle any unexpected errors
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def save_last_folder(self, folder_path):
        with open(LAST_FOLDER_FILE, 'w') as f:
            json.dump({"last_folder": folder_path}, f)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Fonction pour charger le dernier dossier utilisé
    def load_last_folder():
        if os.path.exists(LAST_FOLDER_FILE):
            with open(LAST_FOLDER_FILE, 'r') as f:
                data = json.load(f)
                return data.get("last_folder", "")
        return ""

    # Charger le dernier dossier utilisé
    last_folder = load_last_folder()

    # Utiliser le dernier dossier comme point de départ pour la boîte de dialogue
    folder_path = QFileDialog.getExistingDirectory(None, "Select the folder containing images", last_folder)

    if folder_path:
        window = ImageCaptioningApp(folder_path)
        window.show()
        sys.exit(app.exec_())
    else:
        print("No folder was selected.")
