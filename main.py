from fastapi import FastAPI
from routers import correcao_openai

app = FastAPI(
    title="API de Correção de Redação com IA",
    description="Uma API para corrigir redações do ENEM usando a API da OpenAI.",
    version="1.0.0"
)

# Inclui as rotas definidas no arquivo correcao_openai.py
app.include_router(correcao_openai.router, prefix="/api", tags=["Correção ENEM"])

@app.get("/", summary="Rota raiz da aplicação")
def read_root():
    return {"status": "API de Correção de Redação no ar!"}

# Para rodar a aplicação, use o comando no terminal:
# uvicorn main:app --reload