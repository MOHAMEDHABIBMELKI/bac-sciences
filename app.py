import os
import json
import fitz  # PyMuPDF
import re
import platform
import subprocess
from PIL import Image
import io
import time
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Configuration
PDF_PATH = 'assets/bac.pdf'
JSON_PATH = 'programme_structure_ready.json'  # Ligne à modifier
CACHE_FILE = 'exercices_classifies.json'

# Charger la structure du programme
def load_structure():
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement {JSON_PATH}: {e}")
        return {}

structure = load_structure()

# Ouvrir le document PDF
try:
    doc = fitz.open(PDF_PATH)
except Exception as e:
    print(f"Erreur: Impossible d'ouvrir {PDF_PATH}: {e}")
    doc = None

# ... [Insérer ici le code complet de la classe ApplicationBAC du fichier bac_app.py] ...

# Initialiser l'application
bac_app = ApplicationBAC(PDF_PATH, JSON_PATH)

# Routes API
@app.route('/api/themes', methods=['GET'])
def get_themes():
    themes = []
    for partie in ['chimie', 'physique']:
        if partie in structure and 'units' in structure[partie]:
            for unit in structure[partie]['units'].values():
                for theme_key, theme_data in unit['themes'].items():
                    themes.append({
                        'id': theme_key,
                        'name': theme_data['nom'],
                        'subject': partie
                    })
    return jsonify(themes)

@app.route('/api/exercices', methods=['GET'])
def get_exercices():
    theme_id = request.args.get('theme_id')
    exercices = []
    
    if theme_id:
        for partie in ['chimie', 'physique']:
            if partie in bac_app.exercices and theme_id in bac_app.exercices[partie]:
                exercices.extend([
                    {**ex, 'pages': list(range(ex['page_debut'], ex['page_fin'] + 1)}
                    for ex in bac_app.exercices[partie][theme_id] 
                    if ex['type'] == 'exercice'
                ])
    
    return jsonify(exercices)

@app.route('/api/generate_image', methods=['POST'])
def generate_image():
    data = request.json
    pages = data.get('pages', [])
    
    images = []
    for page_num in pages:
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        images.append(Image.open(io.BytesIO(img_bytes)))
    
    # Assembler les images
    max_width = max(img.width for img in images)
    total_height = sum(img.height for img in images)
    stitched = Image.new('RGB', (max_width, total_height), (255, 255, 255))
    y_offset = 0
    for img in images:
        stitched.paste(img, (0, y_offset))
        y_offset += img.height
    
    img_byte_arr = io.BytesIO()
    stitched.save(img_byte_arr, format='PNG', optimize=True)
    img_byte_arr.seek(0)
    
    return send_file(img_byte_arr, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)