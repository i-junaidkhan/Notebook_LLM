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
    """Build tree hierarchy from concepts using LLM."""
    if state.get("error") or not state["concepts"]:
        return state

    combined_text = "\n\n".join(state["sources_text"][:10])

    model = await provision_langchain_model(
        content=combined_text,
        model_id=None,
        default_type="chat"
    )

    concepts_str = ", ".join(state["concepts"])
    
    # ✅ FIXED PROMPT: Strict JSON schema, no stray text
    prompt = f"""You are a knowledge graph architect. Build a hierarchical mind map from the provided concepts and source text.

SOURCES:
{combined_text[:12000]}

CONCEPTS TO ORGANIZE:
{concepts_str}

REQUIREMENTS:
1. Output MUST be valid JSON matching this EXACT schema:
{{
  "root": "Concise main topic (max 8 words)",
  "children": [
    {{
      "label": "Branch name (max 6 words)",
      "summary": "One-sentence explanation of this branch",
      "level": 1,
      "source_refs": ["keyword1", "keyword2"],
      "children": [
        {{
          "label": "Sub-branch name",
          "summary": "One-sentence explanation",
          "level": 2,
          "source_refs": ["keyword3"],
          "children": []
        }}
      ]
    }}
  ]
}}

2. STRUCTURE RULES:
   - Root level: 3-5 main branches MAX
   - Each branch: 2-4 sub-branches MAX
   - Max depth: 3 levels (root → branch → sub-branch)
   - No empty "children" arrays

3. CONTENT RULES:
   - Labels: Concrete, specific, action-oriented (NOT "Overview", "Introduction")
   - Summaries: Factual, max 20 words, derived from SOURCES above
   - source_refs: Include 1-3 keywords from the concept list that support each node
   - level: Integer (1 for main branches, 2 for sub-branches)

4. OUTPUT FORMAT:
   - Return ONLY the JSON object, no markdown, no explanations
   - Use double quotes for all strings
   - Escape special characters properly

If concepts are insufficient or unrelated, return: {{"error": "Insufficient content to generate mind map"}}
"""
    
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