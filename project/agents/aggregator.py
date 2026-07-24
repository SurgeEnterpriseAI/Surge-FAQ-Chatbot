from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from rag_agent.graph_state import State
from rag_agent.prompts import get_aggregation_prompt

def aggregator(state: State, llm):
    agent_outputs = state.get("agent_outputs", [])
    if not agent_outputs:
        response_text = "I couldn't find any information or execute any actions to resolve your query."
        return {
            "messages": [AIMessage(content=response_text, name="aggregated_response")]
        }
        
    formatted_answers = ""
    for idx, ans in enumerate(agent_outputs, start=1):
        formatted_answers += f"\nAgent '{ans['agent']}' Response:\n{ans['answer']}\n"
        
    prompt_content = (
        f"Original user query: {state.get('originalQuery') or ''}\n\n"
        f"Collected Agent Responses:\n{formatted_answers}\n\n"
        f"INSTRUCTION: Synthesize a unified, single, customer support response. Avoid referring to internal agent names (e.g. do not say 'KnowledgeAgent said'). Act as a single cohesive customer support desk representative. Combine facts and resolve conflicts cleanly."
    )
    
    response = llm.invoke([
        SystemMessage(content=get_aggregation_prompt()),
        HumanMessage(content=prompt_content)
    ])
    
    return {
        "messages": [AIMessage(content=response.content, name="aggregated_response")]
    }
