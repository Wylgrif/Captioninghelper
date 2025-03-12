from PIL import Image
import os
import re
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QFileDialog
from PyQt5.QtCore import Qt

class MetadataApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Extracteur de Prompt")
        self.setGeometry(300, 300, 400, 150)
        
        self.btn = QPushButton("Sélectionner un dossier", self)
        self.btn.setGeometry(50, 30, 300, 30)
        self.btn.clicked.connect(self.browse_folder)
        
        self.status_label = QLabel("Statut : Prêt", self)
        self.status_label.setGeometry(50, 70, 300, 30)
        self.status_label.setAlignment(Qt.AlignCenter)
    
    def remove_after_negprompt(self, text):
        return text.split("Negative prompt:")[0]
    
    def remove_brackets(self, text):
        return re.sub('<.*?>', '', text)
    
    def vraiprompt(self, metadata):
        prompt = self.remove_brackets(self.remove_after_negprompt(metadata))
        return prompt.strip()
    
    def process_folder(self, folder_path):
        png_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
        
        for idx, png_file in enumerate(png_files):
            png_path = os.path.join(folder_path, png_file)
            txt_name = os.path.splitext(png_file)[0] + '.txt'
            txt_path = os.path.join(folder_path, txt_name)
            
            try:
                with Image.open(png_path) as img:
                    if 'parameters' in img.info:
                        prompt = img.info['parameters']
                        clean_prompt = self.vraiprompt(prompt)
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(clean_prompt)
            except Exception as e:
                print(f"Erreur avec {png_file}: {str(e)}")
            
            # Mise à jour de la progression
            self.status_label.setText(f"Traitement : {idx+1}/{len(png_files)}")
            QApplication.processEvents()
        
        self.status_label.setText("Terminé ! Fichiers TXT générés.")
    
    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier")
        if folder_path:
            self.status_label.setText("Traitement en cours...")
            self.process_folder(folder_path)

if __name__ == '__main__':
    app = QApplication([])
    window = MetadataApp()
    window.show()
    app.exec_()