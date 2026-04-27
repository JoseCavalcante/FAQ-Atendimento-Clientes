# 📡 Documentação dos Endpoints da API

## Visão Geral

API de atendimento ao cliente com suporte a LLM (Groq/Llama 3.3) e processamento de PDFs via RAG.

**Base URL:** `http://127.0.0.1:8000`  
**Documentação interativa (Swagger):** `http://127.0.0.1:8000/docs`

---

## 🟢 App — Endpoints Gerais

### `GET /` — Home

**Descrição:** Retorna uma mensagem de boas-vindas. Usado para verificar se a API está online.

| Item | Detalhe |
|---|---|
| **Método** | `GET` |
| **Parâmetros** | Nenhum |
| **Autenticação** | Não |

**Resposta:**
```
"Alou...Esta é a minha HOME!"
```

---

### `GET /alo-mundo` — Alô Mundo

**Descrição:** Endpoint de teste simples para validar que o servidor está respondendo.

| Item | Detalhe |
|---|---|
| **Método** | `GET` |
| **Parâmetros** | Nenhum |
| **Autenticação** | Não |

**Resposta:**
```
"Alou...é por mim que voce procura?"
```

---

## 🤖 LLM — Endpoints de Inteligência Artificial

### `POST /llm` — Consultar LLM com contexto manual

**Descrição:** Envia uma pergunta ao LLM (Groq/Llama 3.3 70B) junto com um contexto fornecido manualmente pelo usuário. O LLM responde **exclusivamente** com base no contexto informado. Se a resposta não estiver no contexto, informa que não possui essa informação.

| Item | Detalhe |
|---|---|
| **Método** | `POST` |
| **Tipo de parâmetros** | Query Parameters |
| **Autenticação** | Não (usa `GROQ_API_KEY` do `.env` internamente) |

**Parâmetros:**

| Nome | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `question` | `string` | ✅ Sim | A pergunta que o usuário deseja fazer |
| `context` | `string` | ✅ Sim | O texto de referência para o LLM basear a resposta |

**Exemplo de chamada:**
```
POST /llm?question=Como abrir uma conta?&context=Para abrir uma conta é necessário documento com foto e comprovante de residência.
```

**Resposta de sucesso (200):**
```json
{
  "response": "Para abrir uma conta, você precisa de um documento com foto e comprovante de residência."
}
```

**Resposta de erro (500):**
```json
{
  "detail": "Mensagem de erro descrevendo o problema"
}
```

**Quando usar:** Quando você já possui o texto de contexto (extraído manualmente de um documento, banco de dados, ou qualquer outra fonte) e quer que o LLM gere uma resposta baseada nele.

---

### `POST /llm/rag` — Consultar LLM com RAG (PDF automático)

**Descrição:** Endpoint de RAG (Retrieval-Augmented Generation) completo. Carrega automaticamente um PDF da pasta `docs/`, extrai e normaliza o texto, monta o contexto com indicação de páginas, e envia ao LLM para gerar a resposta. Não é necessário fornecer o contexto manualmente.

| Item | Detalhe |
|---|---|
| **Método** | `POST` |
| **Tipo de parâmetros** | Query Parameters |
| **Autenticação** | Não (usa `GROQ_API_KEY` do `.env` internamente) |

**Parâmetros:**

| Nome | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `question` | `string` | ✅ Sim | — | A pergunta que o usuário deseja fazer |
| `filename` | `string` | Não | `manual-safebank.pdf` | Nome do arquivo PDF na pasta `docs/` |
| `max_pages` | `integer` | Não | Todas | Limite de páginas a usar como contexto |

**Fluxo interno:**
1. **Carrega** o PDF informado da pasta `docs/`
2. **Normaliza** o texto (remove espaços e quebras de linha excessivas)
3. **Limita** as páginas se `max_pages` for informado
4. **Monta** o contexto com marcação de página: `[Página 1] conteúdo...`
5. **Envia** a pergunta + contexto ao LLM (Groq)
6. **Retorna** a resposta gerada

**Exemplo de chamada:**
```
POST /llm/rag?question=Como alterar minha senha?&filename=manual-safebank.pdf&max_pages=5
```

**Resposta de sucesso (200):**
```json
{
  "response": "Para alterar sua senha, acesse o menu 'Minha Conta' e selecione 'Alterar Senha'...",
  "filename": "manual-safebank.pdf",
  "pages_used": 5
}
```

**Resposta de erro (404):**
```json
{
  "detail": "Arquivo PDF não encontrado: docs/arquivo-inexistente.pdf"
}
```

**Resposta de erro (500):**
```json
{
  "detail": "Mensagem de erro descrevendo o problema"
}
```

**Quando usar:** Quando você quer que o sistema busque automaticamente o contexto de um PDF, sem precisar extrair o texto manualmente. Este é o endpoint principal para uso em produção.

---

## 📄 PDF — Endpoints de Processamento de Documentos

### `POST /pdf/load` — Carregar PDF

**Descrição:** Carrega um arquivo PDF da pasta `docs/` e retorna o conteúdo de texto de todas as páginas, junto com os metadados de cada uma (nome do arquivo fonte, número da página, etc.).

| Item | Detalhe |
|---|---|
| **Método** | `POST` |
| **Tipo de parâmetros** | Query Parameters |
| **Autenticação** | Não |

**Parâmetros:**

| Nome | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `filename` | `string` | ✅ Sim | Nome do arquivo PDF na pasta `docs/` |

**Exemplo de chamada:**
```
POST /pdf/load?filename=manual-safebank.pdf
```

**Resposta de sucesso (200):**
```json
{
  "total_pages": 12,
  "pages": [
    {
      "page_content": "Texto completo da página 1 com formatação original...",
      "metadata": {
        "source": "C:\\...\\docs\\manual-safebank.pdf",
        "page": 0
      }
    },
    {
      "page_content": "Texto completo da página 2...",
      "metadata": {
        "source": "C:\\...\\docs\\manual-safebank.pdf",
        "page": 1
      }
    }
  ]
}
```

**Resposta de erro (404):**
```json
{
  "detail": "Arquivo PDF não encontrado: docs/arquivo.pdf"
}
```

**Quando usar:** Quando você precisa visualizar o conteúdo bruto de um PDF, incluindo quebras de linha e espaçamento originais.

---

### `POST /pdf/normalize` — Carregar e Normalizar PDF

**Descrição:** Carrega um PDF e retorna o conteúdo com o texto normalizado: remove quebras de linha excessivas (`\n\n\n` → `\n`) e espaços múltiplos (`   ` → ` `). Ideal para preparar texto limpo para uso como contexto em consultas ao LLM.

| Item | Detalhe |
|---|---|
| **Método** | `POST` |
| **Tipo de parâmetros** | Query Parameters |
| **Autenticação** | Não |

**Parâmetros:**

| Nome | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `filename` | `string` | ✅ Sim | Nome do arquivo PDF na pasta `docs/` |

**Exemplo de chamada:**
```
POST /pdf/normalize?filename=manual-safebank.pdf
```

**Resposta de sucesso (200):**
```json
{
  "total_pages": 12,
  "pages": [
    {
      "page_content": "Texto normalizado da página 1 sem espaços excessivos...",
      "metadata": {
        "source": "C:\\...\\docs\\manual-safebank.pdf",
        "page": 0
      }
    }
  ]
}
```

**Quando usar:** Quando precisa do texto limpo de um PDF para usar como contexto no endpoint `/llm`, ou para qualquer outro processamento de texto.

---

## 📊 Resumo dos Endpoints

| Tag | Método | Rota | Descrição Resumida |
|---|---|---|---|
| App | `GET` | `/` | Página inicial — verifica se a API está online |
| App | `GET` | `/alo-mundo` | Endpoint de teste |
| LLM | `POST` | `/llm` | Consulta ao LLM com contexto manual |
| LLM | `POST` | `/llm/rag` | Consulta ao LLM com RAG automático via PDF |
| PDF | `POST` | `/pdf/load` | Carrega PDF e retorna conteúdo bruto |
| PDF | `POST` | `/pdf/normalize` | Carrega PDF e retorna conteúdo normalizado |

---

## ⚙️ Configuração

### Variáveis de ambiente (`.env`)

| Variável | Descrição |
|---|---|
| `GROQ_API_KEY` | Chave de API do Groq para acesso ao LLM |
| `OPENAI_API_KEY` | Chave da OpenAI (reservada para uso futuro) |
| `CORS_ORIGINS` | Origens permitidas no CORS, separadas por vírgula |

### PDFs disponíveis na pasta `docs/`

| Arquivo | Conteúdo |
|---|---|
| `manual-safebank.pdf` | Manual de uso do SafeBank (padrão do RAG) |
| `relatorio-financeiro.pdf` | Relatório financeiro |
| `amazon-10k-24.pdf` | Relatório anual Amazon 2024 |
| `amazon-10q-24.pdf` | Relatório trimestral Amazon 2024 |
| `astronomia.pdf` | Conteúdo sobre astronomia |
| `biologia.pdf` | Conteúdo sobre biologia |
| `Currículo1.pdf` / `Currículo2.pdf` / `Currículo3.pdf` | Currículos de exemplo |

### Como executar

```powershell
# Ativar o venv
venv\Scripts\Activate

# Iniciar o servidor
uvicorn main:app --reload
```

O servidor estará disponível em `http://127.0.0.1:8000` e a documentação interativa em `http://127.0.0.1:8000/docs`.
