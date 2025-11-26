import os

# Nom du fichier de sortie
OUTPUT_FILE = "TOUT_MON_PROJET.txt"

# Dossiers à ignorer (IMPORTANT pour ne pas aspirer venv ou git)
IGNORE_DIRS = {'.git', 'venv', 'env', '__pycache__', '.idea', '.vscode', 'node_modules'}
# Extensions de fichiers à inclure
INCLUDE_EXTS = {'.py', '.js', '.html', '.css', '.md', '.json', '.txt'}

def pack_project():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # On parcourt tout le dossier
        for root, dirs, files in os.walk('.'):
            # On retire les dossiers ignorés de la liste de parcours
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in INCLUDE_EXTS and file != "prepare_for_gemini.py" and file != OUTPUT_FILE:
                    file_path = os.path.join(root, file)
                    
                    # On écrit un séparateur clair pour l'IA
                    outfile.write(f"\n{'='*50}\n")
                    outfile.write(f"FICHIER: {file_path}\n")
                    outfile.write(f"{'='*50}\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"Error reading file: {e}")
                    
                    outfile.write("\n") # Saut de ligne entre fichiers

    print(f"✅ Terminé ! Le fichier '{OUTPUT_FILE}' est prêt à être envoyé à Gemini.")

if __name__ == "__main__":
    pack_project()