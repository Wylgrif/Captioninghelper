import os
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog  # Importation correcte
from PIL import Image, ImageTk

class ImageCaptioningApp:
    def __init__(self, root, folder_path):
        self.root = root
        self.folder_path = folder_path
        self.image_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(('png', 'jpg', 'jpeg'))]
        self.current_index = 0
        self.tag_library = set()

        # Initialiser l'interface utilisateur
        self.setup_ui()

        if self.image_files:
            self.load_image()
        else:
            messagebox.showerror("Erreur", "Aucune image trouvée dans le dossier spécifié.")

    def setup_ui(self):
        self.root.title("Application de Captionning d'Images")

        # Affichage de l'image
        self.image_label = tk.Label(self.root)
        self.image_label.pack()

        # Nom de l'image affichée
        self.image_name_label = tk.Label(self.root, text="", font=("Arial", 16))
        self.image_name_label.pack()

        # Cadre pour la bibliothèque de tags
        self.tag_library_frame = tk.Frame(self.root)
        self.tag_library_frame.pack(pady=10)

        tk.Label(self.tag_library_frame, text="Bibliothèque de Tags :", font=("Arial", 12)).pack()

        self.tags_listbox = tk.Listbox(self.tag_library_frame, selectmode=tk.SINGLE, height=8, width=30)
        self.tags_listbox.pack(side=tk.LEFT, padx=5)

        buttons_frame = tk.Frame(self.tag_library_frame)
        buttons_frame.pack(side=tk.LEFT, padx=5)

        tk.Button(buttons_frame, text="Ajouter un Tag", command=self.add_to_library).pack()
        tk.Button(buttons_frame, text="Supprimer un Tag", command=self.remove_from_library).pack()

        # Tags associés à l'image
        self.image_tags_frame = tk.Frame(self.root)
        self.image_tags_frame.pack(pady=10)

        self.image_tags_label = tk.Label(self.image_tags_frame, text="Tags Associés à l'Image :", font=("Arial", 12))
        self.image_tags_label.pack()

        self.image_tags_display = tk.Text(self.image_tags_frame, height=3, width=50)
        self.image_tags_display.pack()

        # Navigation et actions
        actions_frame = tk.Frame(self.root)
        actions_frame.pack(pady=10)

        tk.Button(actions_frame, text="Image Précédente", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Image Suivante", command=self.next_image).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Appliquer Tag", command=self.apply_tag).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Ajouter Tag (Temporaire)", command=self.add_temp_tag).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Retirer Tag", command=self.remove_tag).pack(side=tk.LEFT, padx=5)

    def load_image(self):
        # Charger et afficher l'image courante
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        image = Image.open(image_path)
        image.thumbnail((600, 400))
        photo = ImageTk.PhotoImage(image)

        self.image_label.configure(image=photo)
        self.image_label.image = photo
        self.image_name_label.config(text=os.path.basename(image_path))

        # Charger les tags associés à l'image
        self.load_tags()

    def load_tags(self):
        # Charger les tags depuis le fichier texte associé
        image_name = os.path.splitext(self.image_files[self.current_index])[0]
        tags_file = os.path.join(self.folder_path, f"{image_name}.txt")

        tags = []
        if os.path.exists(tags_file):
            with open(tags_file, "r", encoding="utf-8") as f:
                tags = f.read().strip().split(",")

        self.image_tags_display.delete(1.0, tk.END)
        if tags:
            self.image_tags_display.insert(tk.END, ", ".join(tags))

    def save_tags(self):
        # Sauvegarder les tags associés à l'image dans un fichier texte
        image_name = os.path.splitext(self.image_files[self.current_index])[0]
        tags_file = os.path.join(self.folder_path, f"{image_name}.txt")

        tags_text = self.image_tags_display.get(1.0, tk.END).strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        with open(tags_file, "w", encoding="utf-8") as f:
            f.write(", ".join(tags))

    def add_to_library(self):
        # Ajouter un tag à la bibliothèque
        new_tag = simpledialog.askstring("Ajouter un Tag", "Entrez un nouveau tag :")
        if new_tag and new_tag not in self.tag_library:
            self.tag_library.add(new_tag)
            self.update_tag_library()

    def remove_from_library(self):
        # Supprimer un tag de la bibliothèque
        selected_tag = self.tags_listbox.get(tk.ACTIVE)
        if selected_tag and selected_tag in self.tag_library:
            self.tag_library.remove(selected_tag)
            self.update_tag_library()

    def apply_tag(self):
        # Appliquer un tag de la bibliothèque à l'image
        selected_tag = self.tags_listbox.get(tk.ACTIVE)
        if not selected_tag:
            messagebox.showerror("Erreur", "Veuillez sélectionner un tag.")
            return

        tags_text = self.image_tags_display.get(1.0, tk.END).strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        if selected_tag not in tags:
            tags.append(selected_tag)

        self.image_tags_display.delete(1.0, tk.END)
        self.image_tags_display.insert(tk.END, ", ".join(tags))
        self.save_tags()

    def add_temp_tag(self):
        # Ajouter un tag temporaire à l'image
        new_tag = simpledialog.askstring("Ajouter un Tag", "Entrez un tag temporaire :")
        if new_tag:
            tags_text = self.image_tags_display.get(1.0, tk.END).strip()
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

            if new_tag not in tags:
                tags.append(new_tag)

            self.image_tags_display.delete(1.0, tk.END)
            self.image_tags_display.insert(tk.END, ", ".join(tags))
            self.save_tags()

    def remove_tag(self):
        # Retirer un tag de l'image
        tag_to_remove = simpledialog.askstring("Retirer un Tag", "Entrez le tag à retirer :")
        if tag_to_remove:
            tags_text = self.image_tags_display.get(1.0, tk.END).strip()
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

            if tag_to_remove in tags:
                tags.remove(tag_to_remove)

            self.image_tags_display.delete(1.0, tk.END)
            self.image_tags_display.insert(tk.END, ", ".join(tags))
            self.save_tags()

    def update_tag_library(self):
        # Mettre à jour l'affichage de la bibliothèque de tags
        self.tags_listbox.delete(0, tk.END)
        for tag in sorted(self.tag_library):
            self.tags_listbox.insert(tk.END, tag)

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image()


if __name__ == "__main__":
    # Spécifiez le dossier contenant les images
    folder_path = filedialog.askdirectory(title="Sélectionnez le dossier contenant les images")
    if folder_path:
        root = tk.Tk()
        app = ImageCaptioningApp(root, folder_path)
        root.mainloop()
    else:
        print("Aucun dossier n'a été sélectionné.")
