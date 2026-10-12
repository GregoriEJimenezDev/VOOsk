from __future__ import annotations
import httpx
from app.dominio.puertos import ModelAdapter
from app.config import settings


class FakeAdapter(ModelAdapter):
    """Demo sin modelo real: conversa de forma honesta y guía para activar uno gratis."""
    nombre = "gratuito-fake"

    async def completar(self, prompt_sistema: str, prompt_usuario: str, historial=None) -> str:
        import re
        if "SOLO con el plan" in prompt_sistema or "plan numerado" in prompt_usuario:
            return (
                "1. [general] Analizar objetivo - entender qué pide el usuario\n"
                "2. [ejecutar_comando] Listar archivos - ejecutar dir para ver el workspace\n"
                "3. [general] Concluir - resumir el resultado"
            )
        if re.search(r"(?i)\bobjetivo:\s*(hola|hi+|hello|buenas|buenos d[ií]as|hey|qué tal|que tal|saludos)\b",
                     prompt_usuario or ""):
            return ("¡Hola! 👋 Soy VOOsk, pero ahora mismo estoy en MODO DEMO: no tengo "
                    "ningún modelo de IA conectado, así que solo puedo responder plantillas. "
                    "Para hablar con una IA de verdad y gratis tienes dos caminos: 1) abre la "
                    "app de Ollama en tu PC (usa tus modelos locales), o 2) crea una key "
                    "gratuita en console.groq.com y pégala en la sección BYOK → Groq. "
                    "Cuando esté listo, cuéntame qué quieres construir y lo hacemos paso a paso.")
        return (f"[modo demo — sin modelo conectado] Entendí: {prompt_usuario[:300]}. "
                f"Activa Ollama o una key de Groq para una respuesta real.")


class OllamaAdapter(ModelAdapter):
    """Modelo local gratuito vía Ollama (http://localhost:11434).
    Si no se indica modelo, elige solo el mejor disponible (prefiere *-coder)."""
    nombre = "ollama"
    _auto_cache: str | None = None

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")

    async def _modelo_efectivo(self) -> str:
        if self.model:
            return self.model
        if OllamaAdapter._auto_cache:
            return OllamaAdapter._auto_cache
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.base_url}/api/tags")
                nombres = [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            nombres = []
        if not nombres:
            return settings.OLLAMA_MODEL
        coders = [n for n in nombres if "coder" in n.lower()]
        OllamaAdapter._auto_cache = (coders or nombres)[0]
        return OllamaAdapter._auto_cache

    async def completar(self, prompt_sistema: str, prompt_usuario: str, historial=None) -> str:
        try:
            modelo = await self._modelo_efectivo()
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(f"{self.base_url}/api/generate", json={
                    "model": modelo, "system": prompt_sistema,
                    "prompt": prompt_usuario, "stream": False})
                r.raise_for_status()
                return r.json().get("response", "")
        except Exception:
            return await FakeAdapter().completar(prompt_sistema, prompt_usuario, historial)


class GroqAdapter(ModelAdapter):
    """Modelo gratuito por defecto en la nube (Groq, tier gratuito)."""
    nombre = "groq"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.GROQ_API_KEY

    def requiere_api_key(self) -> bool:
        return False  # el servidor puede aportar la key gratuita

    async def completar(self, prompt_sistema: str, prompt_usuario: str, historial=None) -> str:
        if not self.api_key:
            return await FakeAdapter().completar(prompt_sistema, prompt_usuario, historial)
        msgs = [{"role": "system", "content": prompt_sistema}]
        for h in historial or []:
            msgs.append(h)
        msgs.append({"role": "user", "content": prompt_usuario})
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post("https://api.groq.com/openai/v1/chat/completions",
                             headers={"Authorization": f"Bearer {self.api_key}"},
                             json={"model": "llama-3.3-70b-versatile", "messages": msgs})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


class OpenAIAdapter(ModelAdapter):
    """BYOK: el usuario aporta su propia key de OpenAI."""
    nombre = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def requiere_api_key(self) -> bool:
        return True

    async def completar(self, prompt_sistema: str, prompt_usuario: str, historial=None) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key)
        msgs = [{"role": "system", "content": prompt_sistema}]
        msgs += historial or []
        msgs.append({"role": "user", "content": prompt_usuario})
        resp = await client.chat.completions.create(model=self.model, messages=msgs)
        return resp.choices[0].message.content or ""


class AnthropicAdapter(ModelAdapter):
    """BYOK: el usuario aporta su propia key de Anthropic."""
    nombre = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        self.api_key = api_key
        self.model = model

    def requiere_api_key(self) -> bool:
        return True

    async def completar(self, prompt_sistema: str, prompt_usuario: str, historial=None) -> str:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        msg = await client.messages.create(model=self.model, max_tokens=2000,
                                           system=prompt_sistema,
                                           messages=[{"role": "user", "content": prompt_usuario}])
        return "".join(b.text for b in msg.content if b.type == "text")


async def adapter_automatico(groq_key: str = "") -> ModelAdapter:
    """Gratis e inteligente: Ollama local con modelos > Groq en la nube > demo."""
    try:
        async with httpx.AsyncClient(timeout=4) as c:
            r = await c.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags")
            if r.status_code == 200 and r.json().get("models"):
                return OllamaAdapter()
    except Exception:
        pass
    key = groq_key or settings.GROQ_API_KEY
    if key:
        return GroqAdapter(key)
    return FakeAdapter()


def construir_adapter(proveedor: str, api_key_descifrada: str = "") -> ModelAdapter:
    """Factory/Strategy: añadir proveedor = añadir rama aquí, núcleo intacto."""
    p = (proveedor or "gratuito").lower()
    if p in ("gratuito", "fake", "auto"):
        # "gratuito"/"auto" se resuelven de forma asíncrona en el WS (adapter_automatico);
        # aquí se devuelve demo como fallback seguro.
        return FakeAdapter()
    if p == "ollama":
        return OllamaAdapter()
    if p == "groq":
        return GroqAdapter(api_key_descifrada)
    if p == "openai":
        if not api_key_descifrada:
            raise ValueError("OpenAI requiere BYOK: guarda tu API key primero")
        return OpenAIAdapter(api_key_descifrada)
    if p == "anthropic":
        if not api_key_descifrada:
            raise ValueError("Anthropic requiere BYOK: guarda tu API key primero")
        return AnthropicAdapter(api_key_descifrada)
    raise ValueError(f"Proveedor desconocido: {proveedor}")
