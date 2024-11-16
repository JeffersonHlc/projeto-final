from fastapi import APIRouter, UploadFile, Depends
import json
import xml.etree.ElementTree as ET
import csv
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FileMetadata

router = APIRouter()

@router.post("/upload/")
async def upload_file(file: UploadFile, db: Session = Depends(get_db)):
    data = None
    file_format = None

    if file.filename.endswith('.json'):
        content = await file.read()
        data = json.loads(content)
        file_format = "json"

    elif file.filename.endswith('.xml'):
        content = await file.read()
        root = ET.fromstring(content)
        data = [{elem.tag: elem.text for elem in child} for child in root]
        file_format = "xml"

    elif file.filename.endswith('.csv'):
        content = await file.read()
        decoded = content.decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        data = [row for row in reader]
        file_format = "csv"

    elif file.filename.endswith('.txt'):
        content = await file.read()
        lines = content.decode('utf-8').splitlines()
        data = []
        for line in lines:
            pessoa = {}
            campos = line.split(', ')
            for campo in campos:
                if ': ' in campo:
                    chave, valor = campo.split(': ', 1)
                    pessoa[chave.strip()] = valor.strip()
            if pessoa:
                data.append(pessoa)
        file_format = "txt"

    else:
        return {"error": "Formato de arquivo não suportado"}

    metadata_entry = FileMetadata(
        filename=file.filename,
        file_format=file_format,
        columns=str(data)[:255]
    )
    db.add(metadata_entry)
    db.commit()
    db.refresh(metadata_entry)

    return {
        "filename": file.filename,
        "file_format": file_format,
        "data": data,
        "metadata_id": metadata_entry.id
    }

@router.get("/files/")
async def list_files(db: Session = Depends(get_db)):
    files = db.query(FileMetadata).all()
    return files

