from fastapi import FastAPI, HTTPException, UploadFile
import os
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware
import datetime
import json
import pandas as pd
import xml.etree.ElementTree as ET
from app.database import engine, SessionLocal
from app.models import Base, FileMetadata
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"BASE_DIR: {BASE_DIR}")

templates_dir = os.path.join(BASE_DIR, "templates")
static_dir = os.path.join(BASE_DIR, "static")

print(f"Templates Directory: {templates_dir}")
print(f"Static Directory: {static_dir}")


app = FastAPI()

app.mount("/static", StaticFiles(directory=static_dir), name="static")

API_KEY = os.getenv('GOOGLE_API_KEY', 'SUA_CHAVE_API')
os.environ['GOOGLE_API_KEY'] = API_KEY
genai.configure(api_key=API_KEY)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)

# Função para gerar texto usando o Gemini
def gerar_texto(prompt: str) -> str:
    try:
        response = genai.generate_text(prompt=prompt)
        return response.result if response and response.result else "Erro na geração de texto"
    except Exception as e:
        return f"Erro na API de geração de texto: {str(e)}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(BASE_DIR, "app/templates")  # Certifique-se de definir isso antes

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    try:
        with open(os.path.join(templates_dir, "index.html")) as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Página index.html não encontrada.")

# Endpoint para upload de arquivos
@app.post("/upload/")
async def upload_file(file: UploadFile):
    db = SessionLocal()
    try:
        nome_arquivo = file.filename
        formato = nome_arquivo.split('.')[-1].lower()
        colunas = []
        conteudo = None

        # Processamento de arquivos
        if formato == 'csv':
            df = pd.read_csv(file.file)
            colunas = [{"nomeColuna": col, "tipoDado": str(df[col].dtype)} for col in df.columns]
            conteudo = df.to_dict(orient="records")
        elif formato == 'json':
            df = pd.read_json(file.file)
            colunas = [{"nomeColuna": col, "tipoDado": str(df[col].dtype)} for col in df.columns]
            conteudo = df.to_dict(orient="records")
        elif formato == 'xml':
            file.file.seek(0)
            tree = ET.parse(file.file)
            root = tree.getroot()
            first_element = root[0] if len(root) > 0 else None
            if first_element is not None:
                colunas = [{"nomeColuna": child.tag, "tipoDado": "string"} for child in first_element]
            conteudo = [{child.tag: child.text for child in elem} for elem in root]
        elif formato == 'txt':
            lines = file.file.read().decode('utf-8').splitlines()
            conteudo = [{"line": line} for line in lines]
            colunas = [{"nomeColuna": "line", "tipoDado": "string"}]
        else:
            raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")

        # Geração de texto com Gemini
        prompt = f"Metadados: {colunas}. Conteúdo: {conteudo}"
        resultado_gemini = gerar_texto(prompt)

        # Metadados para salvar no banco
        metadados = {
            "nomeArquivo": nome_arquivo,
            "formatoArquivo": formato,
            "data": datetime.datetime.now(),
            "colunas": colunas,
            "conteudo": conteudo
        }

        # Salvar no banco de dados
        nova_entrada = FileMetadata(
            filename=nome_arquivo,
            file_format=formato,
            date_uploaded=datetime.datetime.now(),
            columns=json.dumps(colunas),
            resultado=json.dumps({"resultado_gemini": resultado_gemini, "conteudo": conteudo})
        )
        db.add(nova_entrada)
        db.commit()
        db.refresh(nova_entrada)

        return {"resultado_gemini": resultado_gemini, "metadados": metadados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

