import os
import json
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from PIL import Image, ImageTk
import subprocess
import random

class ImageCaptioningApp:
    def __init__(self, root, folder_path):
        self.root = root
        self.folder_path = folder_path
        self.tag_library = set()
        self.hidden_images = set()

        self.tag_library_file = os.path.join(folder_path, "tag_library.json")
        self.hidden_images_file = os.path.join(folder_path, "hidden_images.json")

        # Charger les images masquées avant de charger la liste des images
        self.load_hidden_images()

        # Charger uniquement les images non masquées
        self.image_files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
            and f.lower().endswith(('png', 'jpg', 'jpeg'))
            and f not in self.hidden_images  # Exclure les images masquées
        ]

        self.current_index = 0

        self.setup_ui()

        self.load_tag_library()

        if self.image_files:
            self.load_image()
            self.update_progress_bar()
        else:
            messagebox.showerror("Erreur", "Aucune image trouvée dans le dossier spécifié.")

    def setup_ui(self):
        self.root.title("Application de Captionning d'Images")

        self.image_label = tk.Label(self.root)
        self.image_label.pack()

        self.image_name_label = tk.Label(self.root, text="", font=("Arial", 16))
        self.image_name_label.pack()

        self.tag_library_frame = tk.Frame(self.root)
        self.tag_library_frame.pack(pady=10)

        tk.Label(self.tag_library_frame, text="Bibliothèque de Tags :", font=("Arial", 12)).pack()

        self.tags_listbox = tk.Listbox(self.tag_library_frame, selectmode=tk.SINGLE, height=8, width=30)
        self.tags_listbox.pack(side=tk.LEFT, padx=5)

        buttons_frame = tk.Frame(self.tag_library_frame)
        buttons_frame.pack(side=tk.LEFT, padx=5)

        tk.Button(buttons_frame, text="Ajouter un Tag", command=self.add_to_library).pack()
        tk.Button(buttons_frame, text="Supprimer un Tag", command=self.remove_from_library).pack()
        

        self.image_tags_frame = tk.Frame(self.root)
        self.image_tags_frame.pack(pady=10)

        self.image_tags_label = tk.Label(self.image_tags_frame, text="Tags Associés à l'Image :", font=("Arial", 12))
        self.image_tags_label.pack()

        self.image_tags_display = tk.Text(self.image_tags_frame, height=3, width=50)
        self.image_tags_display.pack()

        actions_frame = tk.Frame(self.root)
        actions_frame.pack(pady=10)

        tk.Button(actions_frame, text="Image Précédente", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Image Suivante", command=self.next_image).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Image Aléatoire", command=self.random_image).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Appliquer Tag", command=self.apply_tag).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Ajouter Tag (Temporaire)", command=self.add_temp_tag).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Retirer Tag", command=self.remove_tag).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Masquer l'image", command=self.hide_image).pack(side=tk.LEFT, padx=5)
        tk.Button(actions_frame, text="Envoyer à ollama", command=self.send_to_ollama).pack(side=tk.LEFT, padx=5)

        self.progress_label = tk.Label(self.root, text="", font=("Arial", 12))
        self.progress_label.pack(pady=5)

        self.progress_bar = tk.Canvas(self.root, height=20, width=300, bg="lightgrey")
        self.progress_bar.pack()
        self.progress_fill = None

    def load_image(self):
        image_path = os.path.join(self.folder_path, self.image_files[self.current_index])
        image = Image.open(image_path)
        image.thumbnail((600, 400))
        photo = ImageTk.PhotoImage(image)

        self.image_label.configure(image=photo)
        self.image_label.image = photo
        self.image_name_label.config(text=os.path.basename(image_path))

        self.load_tags()

    def load_tags(self):
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
        # Ne pas sauvegarder les tags pour les images masquées
        if self.image_files[self.current_index] in self.hidden_images:
            return

        image_name = os.path.splitext(self.image_files[self.current_index])[0]
        tags_file = os.path.join(self.folder_path, f"{image_name}.txt")

        tags_text = self.image_tags_display.get(1.0, tk.END).strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        with open(tags_file, "w", encoding="utf-8") as f:
            f.write(", ".join(tags))
        self.update_progress_bar()

    def update_progress_bar(self):
        file_list = os.listdir(self.folder_path)
        txt_files = len([
            f for f in file_list
            if f.endswith(".txt")
            # and os.path.splitext(f)[0] + ".jpg" not in self.hidden_images  Exclure les images masquées
        ])
        total_images = len(self.image_files)+len(self.hidden_images)

        progress = (txt_files / total_images) if total_images > 0 else 0
        fill_width = int(300 * progress)

        if self.progress_fill:
            self.progress_bar.delete(self.progress_fill)
        self.progress_fill = self.progress_bar.create_rectangle(0, 0, fill_width, 20, fill="green")

        self.progress_label.config(text=f"Progression : {txt_files} / {total_images} images captionnées")

    def add_to_library(self):
        new_tag = simpledialog.askstring("Ajouter un Tag", "Entrez un nouveau tag :")
        if new_tag and new_tag not in self.tag_library:
            self.tag_library.add(new_tag)
            self.update_tag_library()

    def remove_from_library(self):
        selected_tag = self.tags_listbox.get(tk.ACTIVE)
        if selected_tag and selected_tag in self.tag_library:
            self.tag_library.remove(selected_tag)
            self.update_tag_library()

    def save_tag_library(self):
        with open(self.tag_library_file, "w", encoding="utf-8") as f:
            json.dump(sorted(list(self.tag_library)), f, ensure_ascii=False, indent=4)
        messagebox.showinfo("Succès", "Bibliothèque de tags sauvegardée automatiquement dans le dossier.")

    def load_tag_library(self):
        if os.path.exists(self.tag_library_file):
            with open(self.tag_library_file, "r", encoding="utf-8") as f:
                self.tag_library = set(json.load(f))
            self.update_tag_library()

    def update_tag_library(self):
        self.tags_listbox.delete(0, tk.END)
        for tag in sorted(self.tag_library):
            self.tags_listbox.insert(tk.END, tag)

    def apply_tag(self):
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
        new_tag = simpledialog.askstring("Ajouter un Tag", "Entrez un tag temporaire :")
        self.add_tag_to_caption(new_tag)
        
        
    def add_tag_to_caption(self, new_tag):
        if new_tag:
            tags_text = self.image_tags_display.get(1.0, tk.END).strip()
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

            if new_tag not in tags:
                tags.append(new_tag)

            self.image_tags_display.delete(1.0, tk.END)
            self.image_tags_display.insert(tk.END, ", ".join(tags))
            self.save_tags()

    def remove_tag(self):
        tags_text = self.image_tags_display.get(1.0, tk.END).strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        if tags:
            tag_to_remove = simpledialog.askstring("Retirer un Tag", "Entrez le tag à retirer :")
            if tag_to_remove and tag_to_remove in tags:
                tags.remove(tag_to_remove)

            self.image_tags_display.delete(1.0, tk.END)
            self.image_tags_display.insert(tk.END, ", ".join(tags))
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
            messagebox.showinfo("Succès", f"L'image {current_image} a été masquée.")
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
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        
        # Check if the command was successful
            if result.returncode == 0:
                # Extract the output from the result
                output = result.stdout.strip()
            
            # Add the output as tags to the image
                self.add_tag_to_caption(output)
            else:
                # Handle errors if the command failed
                error_message = result.stderr.strip()
                messagebox.showerror("Erreur", f"Ollama a renvoyé une erreur : {error_message}")
    
        except Exception as e:
        # Handle any unexpected errors
            messagebox.showerror("Erreur", f"Une erreur s'est produite : {str(e)}")

if __name__ == "__main__":
    folder_path = filedialog.askdirectory(title="Sélectionnez le dossier contenant les images")
    if folder_path:
        root = tk.Tk()
        app = ImageCaptioningApp(root, folder_path)
        root.mainloop()
    else:
        print("Aucun dossier n'a été sélectionné.")
