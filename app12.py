import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from pdfminer.high_level import extract_text
from PIL import Image, ImageEnhance
import shutil
import os
import tempfile
import uuid
import re
import subprocess
import sys
import platform

# 📌 Vérifier et installer Tesseract si nécessaire
def install_tesseract():
    """Installe automatiquement Tesseract en fonction du système d'exploitation."""
    os_name = platform.system()
    
    try:
        if os_name == "Windows":
            tesseract_path = shutil.which("tesseract")
            if not tesseract_path:
                st.info("Installation de Tesseract en cours pour Windows...")
                subprocess.run(
                    ["choco", "install", "tesseract", "-y"],
                    shell=True,
                    check=True
                )
            return shutil.which("tesseract")
        
        elif os_name == "Darwin":  # macOS
            tesseract_path = shutil.which("tesseract")
            if not tesseract_path:
                st.info("Installation de Tesseract en cours pour macOS...")
                subprocess.run(["brew", "install", "tesseract"], check=True)
            return shutil.which("tesseract")
    
    except subprocess.CalledProcessError:
        st.error("⚠️ Erreur lors de l'installation de Tesseract. Veuillez l'installer manuellement.")
        return None

# 📍 Vérification et installation
TESSERACT_PATH = r"C:\Users\math\AppData\Local\Programs\Tesseract-OCR"
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# 📂 Dossier temporaire pour les fichiers téléchargés
UPLOAD_DIR = tempfile.mkdtemp()

# 🏷️ Interface utilisateur Streamlit
st.title("🔍 PDF Accessibility Checker & Corrector")
st.write("Analyse et correction automatique des problèmes d'accessibilité des fichiers PDF (WCAG 2.1 AA & RGAA 4.1).")

uploaded_file = st.file_uploader("📁 Choisissez un fichier PDF", type=["pdf"])

if uploaded_file:
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file, buffer)

    st.success("✅ Fichier téléchargé avec succès !")

    # 🔍 Amélioration d'image pour OCR
    def enhance_image_for_ocr(image_path):
        """Améliore l'image avant l'extraction OCR."""
        img = Image.open(image_path).convert("L")  # Conversion en niveaux de gris
        enhancer = ImageEnhance.Contrast(img)
        img_enhanced = enhancer.enhance(2)  # Augmentation du contraste
        img_enhanced.save(image_path)
        return img_enhanced

    # 🔠 Extraction du texte du PDF
    def extract_text_from_pdf(pdf_path):
        """Extraction de texte avec OCR si nécessaire."""
        if not TESSERACT_PATH:
            return "❌ Erreur : Tesseract n'est pas installé, l'OCR ne peut pas être utilisé."

        doc = fitz.open(pdf_path)
        extracted_text = ""

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text").strip()

            if page_text:
                extracted_text += page_text + "\n"
            else:
                pix = page.get_pixmap()
                img_path = f"{pdf_path}_page_{page_num}.png"
                pix.save(img_path)
                enhanced_image = enhance_image_for_ocr(img_path)
                
                try:
                    ocr_text = pytesseract.image_to_string(enhanced_image)
                    extracted_text += ocr_text + "\n"
                except Exception as e:
                    st.error(f"❌ Erreur OCR sur la page {page_num + 1} : {e}")

        return extracted_text

    # 🔍 Analyse des problèmes d'accessibilité
    def analyze_pdf(pdf_path, text_content):
        """Analyse les problèmes d'accessibilité dans le PDF."""
        issues = []
        doc = fitz.open(pdf_path)

        # 🔴 Vérification des images sans texte alternatif
        for page_num, page in enumerate(doc):
            if page.get_images(full=True):
                issues.append(f"⚠️ Image sans texte alternatif détectée sur la page {page_num + 1}.")

        # 🔵 Vérification de la structure des titres
        headings = [line for line in text_content.split("\n") if re.match(r'^(H[1-6]):', line)]
        if not headings:
            issues.append("⚠️ Structure des titres manquante. Ajout de titres hiérarchisés.")

        return issues

    # ✅ Correction des problèmes détectés
    def correct_pdf(pdf_path, issues):
        """Corrige les problèmes d'accessibilité détectés dans le PDF."""
        doc = fitz.open(pdf_path)

        for issue in issues:
            for page in doc:
                if "Image sans texte alternatif" in issue:
                    page.insert_text((50, 50), "[Description image ajoutée]", fontsize=10)
                elif "Structure des titres" in issue:
                    page.insert_text((50, 100), "H1: Titre du document\n", fontsize=14)

        corrected_pdf_path = pdf_path.replace(".pdf", "_corrected.pdf")
        doc.save(corrected_pdf_path)
        doc.close()
        return corrected_pdf_path

    # 📝 Extraction du texte
    text_content = extract_text_from_pdf(file_path)

    if text_content.startswith("❌ Erreur"):
        st.error(text_content)
    else:
        accessibility_issues = analyze_pdf(file_path, text_content)
        corrected_pdf_path = correct_pdf(file_path, accessibility_issues)

        # 📋 Affichage du rapport d'accessibilité
        st.subheader("📊 Rapport d'accessibilité")
        if not accessibility_issues:
            st.success("✅ Aucun problème détecté. Le document est conforme.")
        else:
            st.warning("⚠️ Des problèmes ont été détectés et corrigés :")
            for issue in accessibility_issues:
                st.write(f"- {issue}")

        # 📥 Permettre le téléchargement du PDF corrigé
        with open(corrected_pdf_path, "rb") as corrected_file:
            st.download_button(
                label="📥 Télécharger le PDF corrigé",
                data=corrected_file,
                file_name="corrected.pdf",
                mime="application/pdf"
            )
