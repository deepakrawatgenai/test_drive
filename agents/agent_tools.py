import os
import json
from langchain.chat_models import ChatOpenAI
from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.memory import ConversationBufferMemory
from tools.inventory import inventory_lookup
from tools.serper_client import serper_search_and_parse

# ----------------- Tool Definitions -----------------
def serper_tool(query: str) -> str:
    parsed = serper_search_and_parse(query)
    out = f"Summary:\n{parsed.get('summary','')}\nFeatures: {', '.join(parsed.get('features',[]))}\nTrims: {', '.join(parsed.get('trims',[]))}"
    return out

def inventory_tool_fn(payload: str) -> str:
    # payload: 'zipcode=xxxxx;model=RAV4'
    parts = dict([p.split('=') for p in payload.split(';') if '=' in p])
    items = inventory_lookup(parts.get('zipcode',''), parts.get('model'))
    if not items:
        return 'No inventory found.'
    return '\n'.join([f"{it['model']} {it['trim']} @ {it['dealership_name']} VIN:{it['vin']}" for it in items])

def schedule_tool(payload: str) -> str:
    try:
        p = json.loads(payload)
        return 'Test drive scheduled successfully (agent).'
    except Exception as e:
        return f'Invalid payload: {e}'

def get_tools():
    return [
        Tool(name='serper_search', func=serper_tool, description='Fetch latest model info via Serper'),
        Tool(name='inventory_lookup', func=inventory_tool_fn, description='Check inventory near ZIP code'),
        Tool(name='schedule_test_drive', func=schedule_tool, description='Schedule a test drive')
    ]

# ----------------- Agent Setup -----------------
def get_agent_executor():
    if not os.getenv('OPENAI_API_KEY'):
        return None
    llm = ChatOpenAI(temperature=0)
    memory = ConversationBufferMemory(memory_key='chat_history')
    tools = get_tools()
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        memory=memory
    )
    return agent

def run_agent_with_streaming(agent, prompt: str, placeholder):
    try:
        result = agent.run(prompt)
        s = ''
        for ch in result:
            s += ch
            placeholder.markdown(f"**Agent (typing...):** {s}")
        return result
    except Exception as e:
        placeholder.markdown(f"**Agent error:** {e}")
        return str(e)
