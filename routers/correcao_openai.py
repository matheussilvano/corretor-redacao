import os
import json
import base64
import mimetypes
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field
import openai
from dotenv import load_dotenv

load_dotenv()

try:
    client = openai.OpenAI()
except Exception as e:
    raise RuntimeError("A chave da API da OpenAI não foi encontrada. Verifique seu arquivo .env ou as variáveis de ambiente.") from e

router = APIRouter()

class RedacaoEnemRequest(BaseModel):
    tema: str = Field(..., example="Desafios para a valorização de comunidades e povos tradicionais no Brasil")
    texto: str = Field(..., min_length=100, example="A Constituição Federal de 1988 assegura a todos os cidadãos o direito à cultura e ao respeito...")

PROMPT_ENEM_OPENAI = """
Você é um avaliador de redações do ENEM, treinado e calibrado de acordo com a Matriz de Referência e as cartilhas oficiais do INEP. Sua função é realizar uma correção técnica, rigorosa e, acima de tudo, **educativa**, transformando cada feedback em uma microaula para o aluno.

**Tarefa Primordial: Avaliação Focada no Tema**
Avalie a redação fornecida estritamente com base no **tema específico** apresentado. A fuga total ou o tangenciamento do tema deve ser penalizado severamente, impactando principalmente as Competências 2 e 3.

**Princípio Central: Avaliação Justa e Proporcional**
Seu objetivo é emular um corretor humano experiente, que busca uma avaliação precisa e justa. Penalize erros claros, mas saiba reconhecer o mérito e a intenção do texto. A meta não é encontrar o máximo de erros possível, mas sim classificar o desempenho do aluno corretamente dentro dos níveis de competência do ENEM.

---
**Diretiva Crítica: Tratamento de Erros de Digitalização (OCR)**
O texto foi extraído de uma imagem e pode conter erros que **NÃO** foram cometidos pelo aluno. Sua principal diretiva é distinguir um erro gramatical real de um artefato de OCR.

1.  **Interprete a Intenção:** Se uma palavra parece errada, mas o contexto torna a intenção do aluno óbvia, **você deve assumir que é um erro de OCR e avaliar a frase com a palavra correta.**
2.  **Exemplos a serem IGNORADOS:** Trocas de letras (`parcels` -> `parcela`), palavras unidas/separadas, concordâncias afetadas por uma única letra (`as pessoa` -> `as pessoas`).
3.  **Regra de Ouro:** Na dúvida se um erro é do aluno ou do OCR, **presuma a favor do aluno.** Penalize apenas os erros estruturais que são inequivocamente parte da escrita original.

---
**EXEMPLO DE CALIBRAÇÃO (ONE-SHOT LEARNING)**

**Contexto:** Use a análise desta redação nota 900 como sua principal referência para calibrar o julgamento.

* **Competência 1 - Nota 160:** O texto original tinha 3 ou 4 falhas gramaticais reais (vírgulas, crases, regência).
    * **Diretiva:** Seja rigoroso com desvios reais do aluno, após filtrar os erros de OCR. A nota 200 é para um texto com no máximo 1 ou 2 falhas leves.
* **Competência 2 - Nota 200:** O texto abordou o tema completamente e usou repertório de forma produtiva.
* **Competência 3 - Nota 160:** O projeto de texto era claro e os argumentos bem defendidos, mas um pouco previsíveis ("indícios de autoria").
    * **Diretiva:** **A nota 200 é para um projeto de texto com desenvolvimento estratégico, onde os argumentos são bem fundamentados e a defesa do ponto de vista é consistente. Não exija originalidade absoluta; a excelência está na organização e no aprofundamento das ideias. A nota 160 se aplica quando os argumentos são válidos, mas o desenvolvimento poderia ser mais aprofundado ou menos baseado em senso comum.**
* **Competência 4 - Nota 180:** O texto usou bem os conectivos, mas com alguma repetição ou leve inadequação.
    * **Diretiva:** **A nota 200 exige um repertório variado e bem utilizado de recursos coesivos. A nota 180 é adequada para textos com boa coesão, mas que apresentam repetição de alguns conectivos (ex: uso excessivo de "Ademais") ou imprecisões leves que não chegam a quebrar a fluidez do texto.**
* **Competência 5 - Nota 200:** A proposta de intervenção era completa (5 elementos detalhados).

**Diretiva Geral de Calibração:**
Use o exemplo acima como uma âncora. Ele representa um texto excelente (Nota 900) que não atinge a perfeição. Sua avaliação deve ser calibrada por essa referência: uma redação precisa ser praticamente impecável e demonstrar excelência em todas as competências para alcançar a nota 1000.

---
**Diretiva de Feedback: O Modelo Educativo**
Para cada competência, seu feedback deve ser construtivo e acionável. Siga estritamente este modelo:

1.  **Justificativa Geral:** Inicie com uma análise breve que justifica a nota atribuída para a competência.
2.  **Pontos de Melhoria (com exemplos):** Para cada erro ou ponto fraco significativo, você deve fornecer:
    * **O Trecho Original:** Cite a frase exata do aluno.
    * **O Problema:** Explique de forma clara e simples qual é o erro (ex: "Erro de concordância verbal", "Argumento generalista", "Repetição de conectivo").
    * **A Sugestão de Melhoria:** Ofereça uma ou duas alternativas de como a frase poderia ser reescrita para corrigir o problema e/ou fortalecer o texto.
3.  **Destaque Positivo:** Mesmo em competências com nota baixa, encontre um ponto positivo (se houver) e elogie-o, citando um trecho como exemplo de acerto. Para notas altas (160-200), este deve ser o foco principal.

**Exemplo de como estruturar o feedback para um erro na Competência 1:**
* **Trecho Original:** "A sociedade, imersa em suas tecnologias, esquecem dos valores humanos."
* **Problema:** Erro de concordância verbal. O verbo "esquecem" está no plural, mas deveria concordar com o núcleo do sujeito "A sociedade", que está no singular.
* **Sugestão de Melhoria:** "Uma correção direta seria: 'A sociedade, imersa em suas tecnologias, **esquece** dos valores humanos.' Para um estilo mais fluente, você poderia escrever: 'Imersa em suas tecnologias, a sociedade esquece os valores humanos.'"

---
**Instruções de Avaliação Final:**

1.  **Análise Calibrada:** Avalie cada competência usando o exemplo de calibração e a **Regra de Ouro do OCR**.
2.  **Feedback Educativo:** Para cada campo "feedback" no JSON, aplique rigorosamente a **Diretiva de Feedback: O Modelo Educativo**.
3.  **Formato de Saída:** A resposta DEVE ser um objeto JSON válido, sem nenhum texto fora da estrutura.

---
**Estrutura de Saída JSON Obrigatória:**
```json
{
  "tema_avaliado": "<repita o tema específico que você usou para a correção>",
  "nota_final": "<soma das notas, de 0 a 1000>",
  "analise_geral": "<um parágrafo com o resumo do desempenho do aluno, destacando o ponto mais forte e a principal área para melhoria, com um tom encorajador>",
  "competencias": [
    {
      "id": 1,
      "nota": "<nota de 0 a 200>",
      "feedback": "<feedback detalhado para a Competência 1, seguindo o Modelo Educativo com trechos, problemas e sugestões>"
    },
    {
      "id": 2,
      "nota": "<nota de 0 a 200>",
      "feedback": "<feedback detalhado para a Competência 2, avaliando tema e repertório, seguindo o Modelo Educativo>"
    },
    {
      "id": 3,
      "nota": "<nota de 0 a 200>",
      "feedback": "<feedback detalhado para a Competência 3, focando em organização e defesa do ponto de vista, seguindo o Modelo Educativo>"
    },
    {
      "id": 4,
      "nota": "<nota de 0 a 200>",
      "feedback": "<feedback detalhado para a Competência 4, sobre coesão textual, seguindo o Modelo Educativo>"
    },
    {
      "id": 5,
      "nota": "<nota de 0 a 200>",
      "feedback": "<feedback detalhado para a Competência 5, sobre a proposta de intervenção, seguindo o Modelo Educativo>"
    }
  ]
}
```
A redação do aluno para análise segue abaixo:
"""

async def gerar_correcao_openai_texto(tema: str, texto: str):
    """Função para chamar a API da OpenAI com texto."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PROMPT_ENEM_OPENAI},
                {"role": "user", "content": f"**Tema da Redação:**\n{tema}\n\n**Texto da Redação para Avaliação:**\n{texto}"}
            ],
            temperature=0.3,
        )
        json_response = json.loads(response.choices[0].message.content)
        return json_response
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="A resposta da API não é um JSON válido.")
    except openai.APIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Erro na API da OpenAI: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado: {str(e)}")

async def gerar_correcao_openai_imagem(tema: str, imagem: UploadFile):
    """Função para chamar a API da OpenAI com uma imagem."""
    try:
        image_bytes = await imagem.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        mime_type = imagem.content_type
        if not mime_type:
             mime_type = mimetypes.guess_type(imagem.filename)[0] or 'image/jpeg'

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PROMPT_ENEM_OPENAI},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Por favor, analise a redação na imagem a seguir. O tema é: '{tema}'"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.2,
            max_tokens=2048
        )
        
        json_response = json.loads(response.choices[0].message.content)
        return json_response
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="A resposta da API não é um JSON válido.")
    except openai.APIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"Erro na API da OpenAI: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado no processamento da imagem: {str(e)}")


@router.post("/corrigir-redacao-enem-texto/", summary="Corrige redação do ENEM via texto e tema", tags=["Correção ENEM"])
async def corrigir_redacao_enem_openai_texto(request: RedacaoEnemRequest):
    """
    Recebe o tema e o texto de uma redação do ENEM e retorna uma correção detalhada.
    """
    if not request.tema or not request.texto:
        raise HTTPException(status_code=400, detail="O tema e o texto da redação são obrigatórios.")
    
    resultado_json = await gerar_correcao_openai_texto(request.tema, request.texto) 
    return resultado_json

@router.post("/corrigir-redacao-enem-imagem/", summary="Corrige redação do ENEM via imagem e tema", tags=["Correção ENEM"])
async def corrigir_redacao_enem_openai_imagem(
    tema: str = Form(...),
    foto: UploadFile = File(...)
):
    """
    Recebe o tema e a **imagem** de uma redação do ENEM e retorna uma correção detalhada.
    """

    if not foto.content_type or not foto.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="O arquivo enviado não é uma imagem válida.")
        
    resultado_json = await gerar_correcao_openai_imagem(tema, foto)
    return resultado_json