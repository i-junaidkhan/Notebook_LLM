import json
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
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
    if state.get("error") or not state["concepts"]:
        return state

    combined_text = "\n\n".join(state["sources_text"][:10])
    model = await provision_langchain_model(content=combined_text, default_type="chat")
    concepts_str = ", ".join(state["concepts"])

    prompt = f"""You are a knowledge graph architect. Build a hierarchical mind map with **exactly 3 levels**: Root → Main Branches → Sub-branches.

Sources:
{combined_text[:8000]}

Concepts: {concepts_str}

**Output format (strict JSON, no extra text):**
{{
  "root": "Main Topic (max 6 words)",
  "children": [
    {{
      "label": "Branch 1 (max 5 words)",
      "summary": "Brief description from sources",
      "children": [
        {{
          "label": "Sub-branch 1.1 (max 5 words)",
          "summary": "Brief description",
          "children": []
        }},
        {{
          "label": "Sub-branch 1.2",
          "summary": "...",
          "children": []
        }}
      ]
    }},
    {{
      "label": "Branch 2",
      "summary": "...",
      "children": [
        {{
          "label": "Sub-branch 2.1",
          "summary": "...",
          "children": []
        }}
      ]
    }}
  ]
}}

Rules:
- Root → 3–5 main branches.
- Each main branch → 2–4 sub-branches.
- Sub-branches have NO further children.
- Each node must have "label" and "children" (even if empty array).
- Return ONLY the JSON object."""
    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            tree = json.loads(content[start:end])
            # Ensure children arrays exist at all levels
            def ensure_children(node):
                if "children" not in node:
                    node["children"] = []
                for child in node.get("children", []):
                    ensure_children(child)
            ensure_children(tree)
            state["tree_json"] = tree
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