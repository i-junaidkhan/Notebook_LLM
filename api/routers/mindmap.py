from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from loguru import logger

from open_notebook.domain.notebook import Notebook, Source
from open_notebook.graphs.mindmap import mindmap_graph
from open_notebook.database.repository import ensure_record_id, repo_query

router = APIRouter()


def _tree_to_nodes_edges(tree: Dict[str, Any], mindmap_id: str, parent_id: Optional[str] = None, level: int = 0, counter: List[int] = None):
    """Convert nested tree JSON to flat nodes and edges."""
    if counter is None:
        counter = [0]

    nodes = []
    edges = []

    # Generate unique node ID
    node_id = f"mindmap_node:{mindmap_id.replace('mindmap:', '')}_{counter[0]}"
    counter[0] += 1

    node = {
        "id": node_id,
        "mindmap": mindmap_id,
        "label": tree.get("label", tree.get("root", "Node")),
        "summary": tree.get("summary", ""),
        "level": level,
        "source_refs": tree.get("source_refs", [])
    }
    nodes.append(node)

    if parent_id:
        edges.append({
            "mindmap": mindmap_id,
            "from_node": parent_id,
            "to_node": node_id,
            "relation_type": "parent-child"
        })

    for child in tree.get("children", []):
        child_nodes, child_edges = _tree_to_nodes_edges(child, mindmap_id, node_id, level + 1, counter)
        nodes.extend(child_nodes)
        edges.extend(child_edges)
    
    return nodes, edges


def _validate_mindmap_tree(tree: Dict[str, Any], max_depth: int = 3, max_branches: int = 5) -> tuple[bool, str]:
    """Validate mindmap tree structure before database insertion."""
    if not isinstance(tree, dict) or "root" not in tree or "children" not in tree:
        return False, "Invalid tree structure: missing root or children"
    
    def _validate_node(node: Dict, level: int) -> tuple[bool, str]:
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            return False, f"Invalid label at level {level}"
        if not isinstance(node.get("summary"), str):
            return False, f"Invalid summary at level {level}"
        if level > max_depth:
            return False, f"Tree exceeds max depth {max_depth}"
        children = node.get("children", [])
        if not isinstance(children, list) or len(children) > max_branches:
            return False, f"Invalid children at level {level} (max {max_branches})"
        for child in children:
            valid, msg = _validate_node(child, level + 1)
            if not valid:
                return False, msg
        return True, "OK"
    
    return _validate_node(tree, 0)


@router.post("/notebooks/{notebook_id}/mindmap")
async def generate_mindmap(notebook_id: str):
    """Generate a new mind map for a notebook."""
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Get source IDs linked to this notebook
        source_refs = await repo_query(
            "SELECT VALUE in FROM reference WHERE out = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)}
        )

        logger.info(f"Found {len(source_refs) if source_refs else 0} source references for notebook {notebook_id}")

        if not source_refs:
            raise HTTPException(status_code=400, detail="No sources linked to this notebook")

        # Fetch full source data including full_text (NO TRUNCATION)
        sources_text = []
        for source_id in source_refs:
            source = await Source.get(str(source_id))
            if source and source.full_text:
                sources_text.append(source.full_text)  # ✅ Removed [:5000]

        if not sources_text:
            raise HTTPException(status_code=400, detail="No source content available")

        logger.info(f"Collected {len(sources_text)} sources with content for mindmap generation")

        # Run the LangGraph mindmap generation
        result = await mindmap_graph.ainvoke({
            "notebook_id": notebook_id,
            "sources_text": sources_text,
            "concepts": [],
            "tree_json": None,
            "error": None
        })

        if result.get("error"):
            raise HTTPException(status_code=500, detail=f"Mind map generation failed: {result['error']}")

        tree = result.get("tree_json")
        if not tree:
            raise HTTPException(status_code=500, detail="No tree structure generated")

        # ✅ Validate tree structure
        is_valid, error_msg = _validate_mindmap_tree(tree)
        if not is_valid:
            logger.error(f"Invalid mindmap structure: {error_msg}")
            raise HTTPException(status_code=500, detail=f"AI output validation failed: {error_msg}")

        logger.info(f"Generated tree structure: {tree}")

        # Delete existing mindmap if any
        existing = await repo_query(
            "SELECT * FROM mindmap WHERE notebook = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)}
        )
        if existing:
            old_id = existing[0]["id"]
            await repo_query("DELETE FROM mindmap_edge WHERE mindmap = $id", {"id": old_id})
            await repo_query("DELETE FROM mindmap_node WHERE mindmap = $id", {"id": old_id})
            await repo_query("DELETE FROM mindmap WHERE id = $id", {"id": old_id})

        # ✅ Transaction block for atomic creation
        mindmap_id = None
        try:
            await repo_query("BEGIN TRANSACTION", {})
            
            # 1. Create mindmap record
            mindmap_result = await repo_query(
                """
                CREATE mindmap SET
                notebook = $notebook_id,
                title = $title,
                created_at = time::now(),
                updated_at = time::now()
                """,
                {
                    "notebook_id": ensure_record_id(notebook_id),
                    "title": tree.get("root", notebook.name)
                }
            )
            if not mindmap_result:
                raise Exception("Failed to create mindmap record")
            mindmap_id = mindmap_result[0]["id"]

            # 2. Generate nodes/edges WITH correct mindmap_id
            nodes, edges = _tree_to_nodes_edges(tree, mindmap_id)

            # 3. Insert nodes
            for node in nodes:
                await repo_query(
                    """
                    CREATE mindmap_node SET
                    mindmap = $mindmap_id,
                    label = $label,
                    summary = $summary,
                    level = $level,
                    source_refs = $source_refs
                    """,
                    {
                        "mindmap_id": ensure_record_id(mindmap_id),
                        "label": node["label"],
                        "summary": node.get("summary", ""),
                        "level": node.get("level", 0),
                        "source_refs": node.get("source_refs", [])
                    }
                )
            
            # 4. Insert edges
            for edge in edges:
                await repo_query(
                    """
                    CREATE mindmap_edge SET
                    mindmap = $mindmap_id,
                    from_node = $from_node,
                    to_node = $to_node,
                    relation_type = $relation_type
                    """,
                    {
                        "mindmap_id": ensure_record_id(mindmap_id),
                        "from_node": edge["from_node"],
                        "to_node": edge["to_node"],
                        "relation_type": edge.get("relation_type", "parent-child")
                    }
                )
            
            await repo_query("COMMIT TRANSACTION", {})

        except Exception as e:
            # Rollback on error
            if mindmap_id:
                await repo_query("ROLLBACK TRANSACTION", {})
                # Clean up partial data
                await repo_query("DELETE FROM mindmap WHERE id = $id", {"id": ensure_record_id(mindmap_id)})
            logger.error(f"Transaction failed: {e}")
            raise HTTPException(status_code=500, detail=f"Mindmap creation failed: {str(e)}")

        logger.info(f"Successfully created mindmap {mindmap_id} with {len(nodes)} nodes and {len(edges)} edges")

        return {
            "id": mindmap_id,
            "notebook_id": notebook_id,
            "title": tree.get("root", notebook.name),
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating mindmap for notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notebooks/{notebook_id}/mindmap")
async def get_mindmap(notebook_id: str):
    """Get existing mind map for a notebook."""
    try:
        result = await repo_query(
            "SELECT * FROM mindmap WHERE notebook = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)}
        )

        if not result:
            return None

        mindmap_data = result[0]
        mindmap_id = mindmap_data["id"]

        # Get nodes
        nodes_result = await repo_query(
            "SELECT * FROM mindmap_node WHERE mindmap = $mindmap_id",
            {"mindmap_id": ensure_record_id(mindmap_id)}
        )

        # Get edges
        edges_result = await repo_query(
            "SELECT * FROM mindmap_edge WHERE mindmap = $mindmap_id",
            {"mindmap_id": ensure_record_id(mindmap_id)}
        )
        
        return {
            "id": mindmap_id,
            "notebook_id": notebook_id,
            "title": mindmap_data.get("title"),
            "nodes": [
                {
                    "id": n["id"],
                    "label": n.get("label"),
                    "summary": n.get("summary"),
                    "level": n.get("level", 0),
                    "position_x": n.get("position_x"),
                    "position_y": n.get("position_y")
                }
                for n in (nodes_result or [])
            ],
            "edges": [
                {
                    "id": e["id"],
                    "from_node": e.get("from_node"),
                    "to_node": e.get("to_node"),
                    "relation_type": e.get("relation_type", "parent-child")
                }
                for e in (edges_result or [])
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching mindmap for notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notebooks/{notebook_id}/mindmap")
async def delete_mindmap(notebook_id: str):
    """Delete mind map for a notebook."""
    try:
        result = await repo_query(
            "SELECT * FROM mindmap WHERE notebook = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)}
        )

        if not result:
            raise HTTPException(status_code=404, detail="Mind map not found")

        mindmap_id = result[0]["id"]

        # Delete edges, nodes, then mindmap (order matters for foreign keys)
        await repo_query("DELETE FROM mindmap_edge WHERE mindmap = $id", {"id": ensure_record_id(mindmap_id)})
        await repo_query("DELETE FROM mindmap_node WHERE mindmap = $id", {"id": ensure_record_id(mindmap_id)})
        await repo_query("DELETE FROM mindmap WHERE id = $id", {"id": ensure_record_id(mindmap_id)})

        return {"message": "Mind map deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting mindmap for notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))