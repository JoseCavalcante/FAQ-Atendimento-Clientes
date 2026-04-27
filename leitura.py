from Service.llmService import LLMService

def printResposta():
    try:
        service = LLMService()
        
        context = """
        Para alterar uma senha no aplicativo, clique no menu 'Minha conta' e selecione 'Alterar senha'.
        Para alterar a senha pelo site, acesse 'Configurações' no menu do topo.
        Em seguida, selecione 'Minha conta' e 'Alterar senha'.
        """
        
        question = "Como alterar minha senha?"
        
        print(f"Pergunta: {question}")
        response = service.get_response(question, context)
        print(f"Resposta: {response}")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    printResposta()
