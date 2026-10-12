from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field


class RegistroIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProyectoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(default="", max_length=2000)
    ruta: str = Field(default="", max_length=500,
                      description="Carpeta de trabajo donde el agente genera archivos")


class CredencialIn(BaseModel):
    proveedor: str = Field(max_length=50)  # groq | ollama | openai | anthropic | gratuito
    etiqueta: str = Field(default="", max_length=200)
    api_key: str = Field(default="", max_length=500)  # vacío = modelo gratuito


class TareaIn(BaseModel):
    objetivo: str = Field(min_length=3, max_length=4000)
    project_id: int | None = None
    modelo: str = Field(default="gratuito", max_length=50)  # proveedor a usar
    archivos: list[str] = []
    ruta: str = Field(default="", max_length=500,
                      description="Carpeta de trabajo (si vacío, usa la del proyecto o el workspace)")


class ContinuarIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class GuardarArchivoIn(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    contenido: str = Field(max_length=1_000_000)
    ruta: str = Field(default="", max_length=500)
    tarea_id: int | None = None
