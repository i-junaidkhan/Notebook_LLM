import json
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from open_notebook.ai.provision import provision_langchain_model


class MindMapState(dict):
    notebook_id: str
    sources_text: List[str]
    concepts: List[str]
    tree_json: Optional[Dict[str, Any]]
    error: Optional[str]


async def extract_concepts(state: MindMapState) -> MindMapState:
    """Extract key concepts from sources using LLM."""
    combined_text = "\n\n".join(state["sources_text"][:10])
    
    # Use "transformation" type (which you have configured)
    model = await provision_langchain_model(
        content=combined_text,
        model_id=None,
        default_type="transformation"
    )

    prompt = f"""Extract 20-30 key concepts or topics from this text (1-5 words each).
Return ONLY a JSON array of strings, nothing else.

Text:
{combined_text[:8000]}

Output format: ["concept1", "concept2", ...]"""

    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            concepts = json.loads(content[start:end])
            state["concepts"] = concepts[:40]
        else:
            state["concepts"] = []
    except Exception as e:
        state["error"] = str(e)
        state["concepts"] = []

    return state


async def build_hierarchy(state: MindMapState) -> MindMapState:
    """Build tree hierarchy from concepts using LLM."""
    if state.get("error") or not state["concepts"]:
        return state

    combined_text = "\n\n".join(state["sources_text"][:10])
    
    # Use "chat" type (which you have configured)
    model = await provision_langchain_model(
        content=combined_text,
        model_id=None,
        default_type="chat"
    )

    concepts_str = ", ".join(state["concepts"])
    prompt = f"""Group these concepts into a mind map tree with at most 7 main branches.
Each branch should have 2-10 sub-concepts.

Return ONLY this JSON structure:
{{
    "root": "Main Topic",
    "children": [
        {{
            "label": "Branch 1",
            "children": [
                {{"label": "Sub-concept 1"}},
                {{"label": "Sub-concept 2"}}
            ]
        }}
    ]
}}

Concepts: {concepts_str}"""
    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            state["tree_json"] = json.loads(content[start:end])
        else:
            state["error"] = "No JSON found in response"
    except Exception as e:
        state["error"] = str(e)

    return state


builder = StateGraph(MindMapState)
builder.add_node("extract_concepts", extract_concepts)
builder.add_node("build_hierarchy", build_hierarchy)

builder.set_entry_point("extract_concepts")
builder.add_edge("extract_concepts", "build_hierarchy")
builder.add_edge("build_hierarchy", END)

mindmap_graph = builder.compile()
