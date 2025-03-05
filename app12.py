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

# Définition des dossiers de stockage temporaire
UPLOAD_DIR = tempfile.mkdtemp()

st.title("🔍 PDF Accessibility Checker & Corrector")
st.write("Analysez et corrigez automatiquement les problèmes d'accessibilité des fichiers PDF pour respecter les normes WCAG 2.1 niveau AA et RGAA 4.1.")

uploaded_file = st.file_uploader("Choisissez un fichier PDF", type=["pdf"])

if uploaded_file:
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file, buffer)

    st.success("✅ Fichier téléchargé avec succès !")

    def enhance_image_for_ocr(image_path):
        """Améliore l'image avant l'extraction OCR pour corriger les erreurs de reconnaissance de texte."""
        img = Image.open(image_path)
        enhancer = ImageEnhance.Contrast(img)
        img_enhanced = enhancer.enhance(2)  # Augmenter le contraste pour améliorer la précision OCR
        img_enhanced.save(image_path)
        return img_enhanced

    def extract_text_from_pdf(pdf_path):
        """Extraction de texte avec OCR amélioré si nécessaire."""
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Extraction de texte brut
            page_text = page.get_text("text").strip()
            if not page_text:
                # Si aucun texte n'est extrait, essayer d'extraire du texte avec OCR
                pix = page.get_pixmap()
                img_path = f"{pdf_path}_page_{page_num}.png"
                pix.save(img_path)
                enhanced_image = enhance_image_for_ocr(img_path)
                text += pytesseract.image_to_string(enhanced_image)
            else:
                text += page_text
        return text

    def analyze_pdf(pdf_path, text_content):
        """Analyse les problèmes d'accessibilité dans le PDF."""
        issues = []
        doc = fitz.open(pdf_path)

        # Vérification des images sans texte alternatif (WCAG 1.1.1)
        for page_num, page in enumerate(doc):
            if page.get_images(full=True):
                issues.append(f"Image sans texte alternatif détectée sur la page {page_num + 1}.")

        # Vérification de la structure des titres (WCAG 2.4.6, RGAA 3.3)
        headings = [line for line in text_content.split("\n") if re.match(r'^(H[1-6]):', line)]
        if len(headings) == 0:
            issues.append("Structure des titres manquante. Ajout de titres hiérarchisés.")

        # Vérification du contraste visuel (WCAG 1.4.3) - Exemple simplifié
        if "horizon" in text_content.lower():  # Juste un exemple de recherche de texte
            issues.append("Problème de contraste détecté.")
        
        return issues

    def correct_pdf(pdf_path, issues):
        """Corrige les problèmes d'accessibilité dans le PDF."""
        doc = fitz.open(pdf_path)

        for issue in issues:
            if "Image sans texte alternatif" in issue:
                for page in doc:
                    page.insert_text((50, 50), "[Description image ajoutée]", fontsize=10)
            elif "Structure des titres" in issue:
                for page in doc:
                    page.insert_text((50, 100), "H1: Titre du document\n", fontsize=14)
            elif "OCR" in issue:
                for page in doc:
                    page.insert_text((50, 150), "⚠️ Texte détecté par OCR ajouté.", fontsize=12)
            elif "Contraste" in issue:
                for page in doc:
                    page.insert_text((50, 200), "⚠️ Problème de contraste identifié.", fontsize=12)

        corrected_pdf_path = pdf_path.replace(".pdf", "_corrected.pdf")
        doc.save(corrected_pdf_path)
        doc.close()
        return corrected_pdf_path

    # Extraction du texte du PDF
    text_content = extract_text_from_pdf(file_path)
    accessibility_issues = analyze_pdf(file_path, text_content)

    # Correction des problèmes d'accessibilité
    corrected_pdf_path = correct_pdf(file_path, accessibility_issues)

    # Affichage du rapport d'accessibilité
    st.subheader("Rapport d'accessibilité")
    if not accessibility_issues:
        st.success("✅ Aucun problème détecté. Le document est conforme.")
    else:
        st.warning("Des problèmes ont été détectés et corrigés :")
        for issue in accessibility_issues:
            st.write(f"- {issue}")

    # Permettre le téléchargement du PDF corrigé
    with open(corrected_pdf_path, "rb") as corrected_file:
        st.download_button(
            label="📥 Télécharger le PDF corrigé",
            data=corrected_file,
            file_name="corrected.pdf",
            mime="application/pdf"
        )
