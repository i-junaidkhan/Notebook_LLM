import json
import math
import random
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from loguru import logger

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.utils.embedding import generate_embeddings

# --- 1. Pure Python Math & Clustering (No external libraries needed) ---

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate the mathematical distance between two concept embeddings."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 * norm2 != 0 else 0

def kmeans_cluster(concepts: List[str], embeddings: List[List[float]], k: int = 4) -> List[List[str]]:
    """Group concepts together mathematically based on their embedding similarity."""
    if not concepts or not embeddings:
        return []
    if len(concepts) <= k:
        return [[c] for c in concepts]
    
    # Initialize random centroids
    centroids = random.sample(embeddings, k)
    cluster_concepts = [[] for _ in range(k)]
    
    # Run a few iterations to group similar concepts
    for _ in range(5):
        clusters = [[] for _ in range(k)]
        cluster_concepts = [[] for _ in range(k)]
        
        for concept, emb in zip(concepts, embeddings):
            # Find closest centroid using cosine similarity
            sims = [cosine_similarity(emb, c) for c in centroids]
            best_idx = sims.index(max(sims))
            clusters[best_idx].append(emb)
            cluster_concepts[best_idx].append(concept)
            
        # Update centroids to the center of the new clusters
        for i in range(k):
            if clusters[i]:
                centroids[i] = [sum(col)/len(col) for col in zip(*clusters[i])]
                
    # Return lists of grouped concepts, removing empty clusters
    return [c for c in cluster_concepts if c]


# --- 2. LangGraph Pipeline ---

class MindMapState(dict):
    notebook_id: str
    sources_text: List[str]
    concepts: List[str]
    concept_embeddings: List[List[float]]
    clusters: List[List[str]]
    tree_json: Optional[Dict[str, Any]]
    error: Optional[str]


async def extract_concepts(state: MindMapState) -> MindMapState:
    """Node 1: Smartly extract concepts by analyzing the actual semantic domain, ignoring document type or noise."""
    
    # Intelligently sample the document: Start, Middle, and End to capture the whole picture
    total_len = len(state["sources_text"])
    if total_len > 3:
        sampled_text = "\n\n".join([
            state["sources_text"][0],  # Abstract/Intro
            state["sources_text"][total_len // 2], # Core Body
            state["sources_text"][-1]  # Conclusion
        ])
    else:
        sampled_text = "\n\n".join(state["sources_text"])
        
    # Truncate to a safe limit for the LLM context window
    sampled_text = sampled_text[:12000]

    try:
        model = await provision_langchain_model(
            content=sampled_text,
            model_id=None,
            default_type="transformation"
        )

        # The "Smart" Prompt: Forces the AI to identify the domain first, eliminating author names, affiliations, and boilerplate.
        prompt = f"""You are an expert data extraction algorithm. Analyze the following document sample.
        
Step 1: Identify the core semantic subject matter (e.g., 'Cybersecurity', 'Financial Economics', 'Software Engineering').
Step 2: Ignore all academic boilerplate, author names, universities, publication dates, and table of contents.
Step 3: Extract exactly 15 to 20 highly specific, technical concepts or main ideas related ONLY to that core subject.

Return ONLY a comma-separated list of short phrases (1-3 words each). Do not include Step 1 or Step 2 in your output.

Text:
{sampled_text}"""

        response = await model.ainvoke([HumanMessage(content=prompt)])
        
        # Parse the output safely
        raw_concepts = [c.strip().strip('-*."\'') for c in response.content.split(",")]
        # Filter out obvious metadata hallucinations if the AI slipped up
        stop_words = ["abstract", "introduction", "conclusion", "references", "author", "university", "copyright"]
        concepts = [c for c in raw_concepts if c and 2 <= len(c) <= 40 and c.lower() not in stop_words][:15]
        
        if not concepts:
            raise ValueError("Model returned an empty list of concepts.")
            
        state["concepts"] = concepts
        logger.info(f"Smartly extracted {len(concepts)} concepts: {concepts}")
        
    except Exception as e:
        logger.error(f"Concept extraction failed: {e}")
        state["error"] = str(e)
        state["concepts"] = []

    return state



async def embed_concepts(state: MindMapState) -> MindMapState:
    """Node 2: Convert textual concepts into mathematical vectors."""
    if state.get("error") or not state.get("concepts"):
        return state

    try:
        logger.info("Generating embeddings for concepts...")
        embeddings = await generate_embeddings(state["concepts"])
        state["concept_embeddings"] = embeddings
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        state["error"] = f"Embedding failed: {e}"
        
    return state


async def cluster_concepts(state: MindMapState) -> MindMapState:
    """Node 3: Pure math clustering (No LLM). Groups concepts together."""
    if state.get("error") or not state.get("concept_embeddings"):
        return state

    try:
        concepts = state["concepts"]
        embeddings = state["concept_embeddings"]
        
        # Decide how many main branches we want (max 4)
        k = min(4, max(2, len(concepts) // 3))
        
        clusters = kmeans_cluster(concepts, embeddings, k=k)
        state["clusters"] = clusters
        logger.info(f"Formed {len(clusters)} mathematical clusters.")
        
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        state["error"] = f"Clustering failed: {e}"

    return state


async def build_hierarchy(state: MindMapState) -> MindMapState:
    """Node 4: Python builds the JSON tree. LLM only generates short labels."""
    if state.get("error") or not state.get("clusters"):
        return state

    combined_text = "\n\n".join(state["sources_text"][:10])
    
    try:
        model = await provision_langchain_model(
            content=combined_text, 
            model_id=None, 
            default_type="chat"
        )

        # 1. Base Structure built in Python (Zero risk of JSON parsing errors)
        tree = {
            "root": "Main Topic",
            "summary": "Generated mindmap based on source documents.",
            "children": []
        }

        # 2. Micro-prompt for the Root Title
        try:
            root_prompt = f"What is the single main overall topic of this text? Return ONLY a 2-5 word title.\n\Text:\n{combined_text[:3000]}"
            root_resp = await model.ainvoke([HumanMessage(content=root_prompt)])
            tree["root"] = root_resp.content.strip().replace('"', '')[:50]
        except Exception:
            tree["root"] = "Document Overview" # Fallback

        # 3. Micro-prompt for each Branch
        for cluster in state["clusters"]:
            if not cluster: 
                continue
                
            concepts_str = ", ".join(cluster)
            prompt = f"Give a 1-3 word category name that groups these related concepts together: [{concepts_str}]. Return ONLY the short category name, nothing else."
            
            try:
                branch_resp = await model.ainvoke([HumanMessage(content=prompt)])
                branch_label = branch_resp.content.strip().replace('"', '')[:30]
            except Exception:
                branch_label = cluster[0] # Fallback to the first item if LLM fails

            # Construct the branch safely in Python
            branch = {
                "label": branch_label,
                "summary": f"Key cluster containing {len(cluster)} concepts.",
                "children": []
            }

            # Add the extracted concepts as sub-branches (leaves)
            for concept in cluster[:5]:
                branch["children"].append({
                    "label": concept,
                    "summary": "",
                    "children": []
                })

            tree["children"].append(branch)

        state["tree_json"] = tree
        logger.info("Successfully constructed full hierarchical tree.")
        
    except Exception as e:
        logger.error(f"Hierarchy building failed: {e}")
        state["error"] = str(e)
        
    return state


# --- 3. Graph Compilation ---

builder = StateGraph(MindMapState)
builder.add_node("extract_concepts", extract_concepts)
builder.add_node("embed_concepts", embed_concepts)
builder.add_node("cluster_concepts", cluster_concepts)
builder.add_node("build_hierarchy", build_hierarchy)

builder.set_entry_point("extract_concepts")
builder.add_edge("extract_concepts", "embed_concepts")
builder.add_edge("embed_concepts", "cluster_concepts")
builder.add_edge("cluster_concepts", "build_hierarchy")
builder.add_edge("build_hierarchy", END)

mindmap_graph = builder.compile()
