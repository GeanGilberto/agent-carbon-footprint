from google.adk.agents.llm_agent import Agent
from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

API_KEY = os.getenv("TRELLO_API_KEY")
API_SECRET = os.getenv("TRELLO_API_SECRET")
TOKEN = os.getenv("TRELLO_TOKEN")

def get_temporal_context() -> str:
    now = datetime.now()
    return now.strftime('%Y/%m/%d %H:%M:%S')

def get_client() -> TrelloClient:
    return TrelloClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        token=TOKEN
    )

def get_board(board_name="DIO") -> Board:
    client = get_client()

    board = next((b for b in client.list_boards() if b.name == board_name), None)

    if not board:
        raise ValueError(f"Board '{board_name}' não encontrado")

    return board


def adicionar_tarefa(nome_da_task: str, descricao_da_task: str, due_date: str):
    
    board = get_board()

    # Obter a lista onde quer adicionar o card
    listas = board.list_lists()

    minha_lista = next((l for l in listas if l.name.upper() in {"TO DO", "TODO", "NA FILA"}), None)

    if not minha_lista:
        raise ValueError("Lista inicial não encontrada")
    
    # Criar o card (task)
    card = minha_lista.add_card(
        name=nome_da_task,
        desc=descricao_da_task,
        due=due_date
    )
    
    return f"✅ Card criado: {card.name}"

def listar_tarefas(status: str = "todas") -> list[dict]:    
    board = get_board()
    
    listas = board.list_lists()        

    if status.lower() == "todas":
        listas_filtradas = listas
    elif status.lower() == "na fila":
        listas_filtradas = [l for l in listas if l.name.upper() in ['NA FILA', 'TO DO', 'TODO']]
    elif status.lower() == "em andamento":
        listas_filtradas = [l for l in listas if l.name.upper() in ['EM ANDAMENTO', 'DOING']]
    elif status.lower() == "esperando validação"    :
        listas_filtradas = [l for l in listas if l.name.upper() in ['ESPERANDO VALIDAÇÃO', 'WAITING FOR VALIDATION']]
    elif status.lower() == "concluido":
        listas_filtradas = [l for l in listas if l.name.upper() in ['CONCLUÍDO', 'CONCLUIDO', 'DONE']]
    else:
        listas_filtradas = listas

    tarefas = []

    for lista in listas_filtradas:
        cards = lista.list_cards()
        for card in cards:
            tarefas.append({
                "nome": card.name,
                "descricao": card.desc,
                "vencimento": card.due,
                "status": lista.name,
                "id": card.id
            })
    
    return tarefas

def mudar_status_tarefa(nome_da_task: str, novo_status: str) -> str:
    try:
        board = get_board()
        listas = board.list_lists()
                       
        # Mapear status para listas
        status_map = {
            "na fila": "NA FILA",
            "em andamento": "EM ANDAMENTO",
            "esperando validação": "ESPERANDO VALIDAÇÃO",
            "concluido": "CONCLUÍDO"
        }
        
        nome_lista_destino = status_map.get(novo_status.lower())

        if not nome_lista_destino:
            return f"❌ Status inválido. Use: 'na fila', 'em andamento', 'esperando validação' ou 'concluido'"
        
        # Encontrar lista de destino
        lista_destino = next((l for l in listas if l.name.upper() == nome_lista_destino.upper()), None)

        if not lista_destino:
            return f"❌ Lista '{nome_lista_destino}' não encontrada no board"
        
         # Buscar card em todas as listas
        card_encontrado = None
        lista_origem = None

        for lista in listas:
            cards = lista.list_cards()
            card_encontrado = next(
                (c for c in cards if c.name.lower() == nome_da_task.lower()), 
                None
            )
            if card_encontrado:
                lista_origem = lista
                break
        
        if not card_encontrado:
            return f"❌ Card '{nome_da_task}' não encontrado"
        
        # Mover
        card_encontrado.change_list(lista_destino.id)
        return f"✅ '{nome_da_task}': {lista_origem.name} → {lista_destino.name}"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

def remover_tarefa(nome_da_task: str) -> str:
    try:
        board = get_board()
        listas = board.list_lists()

        card_encontrado = None

        for lista in listas:
            cards = lista.list_cards()

            card_encontrado = next(
                (
                    c for c in cards
                    if c.name.lower() == nome_da_task.lower()
                ),
                None
            )

            if card_encontrado:
                break

        if not card_encontrado:
            return f"❌ Card '{nome_da_task}' não encontrado"

        nome_card = card_encontrado.name

        # Remove permanentemente o card
        card_encontrado.delete()

        return f"✅ Card '{nome_card}' removido com sucesso"

    except Exception as e:
        return f"❌ Erro ao remover tarefa: {str(e)}"


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='Agente de Organização de Tarefas',
    instruction="""
        Você é um agente de organização de tarefas.     
        Sua função é receber uma tarefa e criar um card no Trello com o nome e descrição da tarefa.
        Você deve me perguntar as atividas que tenho no dia e criar um card para cada uma delas.
        Você inicia a conversa assim que for ativado, perguntando quais são as tarefas do dia.
        Sempre inicie a conversa perguntando quais são as tarefas do dia informando a data com pela tool get_temporal_context, 
        e depois vá perguntando se tem mais alguma tarefa, até que o usuário diga que não tem mais tarefas.
        Suas funções:
          1. Adicionar novas tarefas com nome e descrição
          2. Listar todas as tarefas ou filtrar por status
          3. Marcar tarefas como concluídas
          4. Remover tarefas da lista
          5. Mudar o status da tarefa (ex: de "Na Fila" para "Em Andamento" e de "Em Andamento" para "Esperando Validação" ou "Concluído")
          6. Gerar contexto temporal (data e hora atual) para organizar as tarefas do dia
""",
    tools=[get_temporal_context, adicionar_tarefa, listar_tarefas, mudar_status_tarefa, remover_tarefa],
)