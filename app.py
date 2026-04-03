import streamlit as st
import pandas as pd
import PyPDF2
from openai import OpenAI
from docx import Document
from docx.shared import Pt
from io import BytesIO

# 1. Función para leer la estrategia desde el CSV local
def obtener_matriz_estrategia():
    try:
        df = pd.read_csv('estrategia.csv')
        texto = ""
        for _, fila in df.iterrows():
            texto += f"- {fila['Planteo']}: Detectar con '{fila['PalabrasClave']}'. Ejemplo: {fila['Ejemplo']}\n"
        return texto
    except Exception as e:
        return f"Error al cargar matriz: {e}"

# 2. Función MAESTRA para crear el Word con TABLAS REALES
def crear_word_profesional(texto_ia):
    doc = Document()
    # Estilo general
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    lineas = texto_ia.split('\n')
    en_tabla = False
    tabla_word = None

    for linea in lineas:
        linea_limpia = linea.strip()
        if not linea_limpia: continue

        # Identificar si es una fila de tabla de la IA (| Dato | Dato |)
        if linea_limpia.startswith('|') and linea_limpia.count('|') > 1:
            # Ignorar la línea de separación de Markdown |---|---|
            if set(linea_limpia.replace('|', '').replace('-', '').replace(' ', '')) == set():
                continue
            
            # Extraer celdas
            celdas_texto = [c.strip() for c in linea_limpia.split('|') if c.strip()]
            
            if not en_tabla:
                # Crear tabla nueva
                tabla_word = doc.add_table(rows=1, cols=len(celdas_texto))
                tabla_word.style = 'Table Grid'
                hdr_cells = tabla_word.rows[0].cells
                for i, texto in enumerate(celdas_texto):
                    hdr_cells[i].text = texto
                en_tabla = True
            else:
                # Agregar fila a tabla existente
                row_cells = tabla_word.add_row().cells
                for i, texto in enumerate(celdas_texto):
                    if i < len(row_cells):
                        row_cells[i].text = texto
        else:
            en_tabla = False # Salimos de modo tabla
            # Manejo de Títulos
            if linea_limpia.startswith('###'):
                doc.add_heading(linea_limpia.replace('###', '').strip(), level=2)
            elif linea_limpia.startswith('##'):
                doc.add_heading(linea_limpia.replace('##', '').strip(), level=1)
            elif linea_limpia.startswith('#'):
                doc.add_heading(linea_limpia.replace('#', '').strip(), level=0)
            else:
                doc.add_paragraph(linea_limpia.replace('**', ''))

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# 3. Interfaz Streamlit
st.set_page_config(page_title="Analizador Pro v2", page_icon="⚖️")
st.title("⚖️ Analizador de plateos en Contestaciones de demandas de ANSES")

st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

archivo = st.file_uploader("Sube la contestación de ANSES (PDF)", type="pdf")

if st.button("🚀 Iniciar Análisis Profesional"):
    if not api_key or not archivo:
        st.error("Falta la API Key o el archivo.")
    else:
        client = OpenAI(api_key=api_key)
        
        with st.spinner("Extrayendo datos y analizando estrategia..."):
            lector = PyPDF2.PdfReader(archivo)
            texto_demanda = ""
            for pagina in lector.pages:
                texto_demanda += pagina.extract_text() + "\n"
            
            # Limpieza básica para reducir tokens innecesarios
            texto_demanda = " ".join(texto_demanda.split())
            
            matriz = obtener_matriz_estrategia()
            
            prompt_sistema = f"""Actúa como un prolijo Prosecretario de Juzgado Especialista en Seguridad Social.
Tu tarea es analizar el documento adjunto y generar un informe técnico basado estrictamente en la matriz de defensa.

1. PRIMERO: Extrae los datos de identificación:
   - Carátula (Nombre del actor vs ANSES)
   - Número de Expediente
   - Número de Juzgado

2. SEGUNDO: Analiza la presencia de estos planteos según esta matriz de referencia:
{matriz}

3. FORMATO DE SALIDA (ESTRICTO):
# REPORTE DE ANÁLISIS LEGAL
## DATOS DEL EXPEDIENTE
- **Carátula:** [Nombre]
- **Expediente:** [Número]
- **Juzgado:** [Número]

## MATRIZ DE DEFENSA DETECTADA
| Planteo Detectado | Evidencia Textual (Cita breve del párrafo) | Certeza |
| :--- | :--- | :--- |

Usa un tono profesional y técnico."""

            try:
                res = client.chat.completions.create(
                    model="gpt-4o-mini", # CAMBIO CLAVE: Modelo con límites más altos y económico
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": texto_demanda}
                    ],
                    temperature=0
                )
                
                informe_final = res.choices[0].message.content
                st.success("¡Análisis Terminado con éxito!")
                st.markdown(informe_final)
                
                # Generar el Word con la nueva función de tablas
                word_ready = crear_word_profesional(informe_final)
                
                st.download_button(
                    label="📥 Descargar Informe en Word (con tablas)",
                    data=word_ready,
                    file_name="Informe_Estrategia_ANSES.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error detectado: {e}")
