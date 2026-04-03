from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from loguru import logger

from open_notebook.domain.notebook import Notebook, Source
from open_notebook.graphs.mindmap import mindmap_graph
from open_notebook.database.repository import ensure_record_id, repo_query

router = APIRouter()


def _flatten_tree(tree: Dict[str, Any], parent_idx: Optional[int] = None, level: int = 0, counter: List[int] = None, nodes_list: List[Dict] = None, edges_list: List[Dict] = None):
    """Flatten tree into nodes and edges with sequential indices."""
    if counter is None:
        counter = [0]
    if nodes_list is None:
        nodes_list = []
    if edges_list is None:
        edges_list = []

    current_idx = counter[0]
    counter[0] += 1

    # Calculate positions for tree layout
    y_spacing = 150
    x_spacing = 250

    nodes_list.append({
        "idx": current_idx,
        "label": tree.get("label", tree.get("root", "Node")),
        "summary": tree.get("summary", ""),
        "level": level,
        "position_x": current_idx * x_spacing,
        "position_y": level * y_spacing
    })

    if parent_idx is not None:
        edges_list.append({
            "parent_idx": parent_idx,
            "child_idx": current_idx
        })

    for child in tree.get("children", []):
        _flatten_tree(child, current_idx, level + 1, counter, nodes_list, edges_list)

    return nodes_list, edges_list


def _validate_mindmap_tree(tree: Dict[str, Any], max_depth: int = 3, max_branches: int = 5) -> tuple[bool, str]:
    """Validate mindmap tree structure before database insertion."""
    if not isinstance(tree, dict) or "root" not in tree or "children" not in tree:
        return False, "Invalid tree structure: missing root or children"

    def _validate_node(node: Dict, level: int) -> tuple[bool, str]:
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            return False, f"Invalid label at level {level}"
        summary = node.get("summary")
        if summary is not None and not isinstance(summary, str):
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

        source_refs = await repo_query(
            "SELECT VALUE in FROM reference WHERE out = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)}
        )

        logger.info(f"Found {len(source_refs) if source_refs else 0} source references for notebook {notebook_id}")

        if not source_refs:
            raise HTTPException(status_code=400, detail="No sources linked to this notebook")

        sources_text = []
        for source_id in source_refs:
            source = await Source.get(str(source_id))
            if source and source.full_text:
                sources_text.append(source.full_text)

        if not sources_text:
            raise HTTPException(status_code=400, detail="No source content available")

        logger.info(f"Collected {len(sources_text)} sources with content for mindmap generation")

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

        if "root" in tree and "label" not in tree:
            tree["label"] = tree["root"]

        is_valid, error_msg = _validate_mindmap_tree(tree)
        if not is_valid:
            logger.error(f"Invalid mindmap structure: {error_msg}")
            raise HTTPException(status_code=500, detail=f"AI output validation failed: {error_msg}")

        logger.info(f"Generated tree structure: {tree}")

        # === COMPLETE CLEANUP: Delete ALL old mindmap data for this notebook ===
        existing = await repo_query(
            "SELECT * FROM mindmap WHERE notebook = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)}
        )
        for old_mindmap in (existing or []):
            old_id = old_mindmap["id"]
            logger.info(f"Deleting old mindmap and all related data: {old_id}")
            await repo_query("DELETE FROM mindmap_edge WHERE mindmap = $id", {"id": old_id})
            await repo_query("DELETE FROM mindmap_node WHERE mindmap = $id", {"id": old_id})
            await repo_query("DELETE FROM mindmap WHERE id = $id", {"id": old_id})

        # Also clean up any orphaned nodes/edges (safety net)
        await repo_query("DELETE FROM mindmap_node WHERE mindmap = NONE OR mindmap = NULL")
        await repo_query("DELETE FROM mindmap_edge WHERE mindmap = NONE OR mindmap = NULL")

        # === CREATE MINDMAP RECORD ===
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

        # === FLATTEN TREE TO NODES AND EDGES ===
        nodes_list, edges_list = _flatten_tree(tree)
        logger.info(f"Flattened tree: {len(nodes_list)} nodes, {len(edges_list)} edges")

        # === CREATE NODES AND CAPTURE THEIR REAL DB IDs ===
        idx_to_real_id = {}  # Maps our sequential index to actual DB-generated ID

        for node in nodes_list:
            node_result = await repo_query(
                """
                CREATE mindmap_node SET
                mindmap = $mindmap_id,
                label = $label,
                summary = $summary,
                level = $level,
                source_refs = [],
                position_x = $position_x,
                position_y = $position_y
                """,
                {
                    "mindmap_id": ensure_record_id(mindmap_id),
                    "label": node["label"],
                    "summary": node.get("summary", ""),
                    "level": node.get("level", 0),
                    "position_x": node.get("position_x", 0),
                    "position_y": node.get("position_y", 0)
                }
            )
            if node_result:
                real_id = node_result[0]["id"]
                idx_to_real_id[node["idx"]] = real_id
                logger.debug(f"Created node idx={node['idx']} -> real_id={real_id}")

        # === CREATE EDGES USING REAL NODE IDs ===
        edges_created = 0
        for edge in edges_list:
            parent_real_id = idx_to_real_id.get(edge["parent_idx"])
            child_real_id = idx_to_real_id.get(edge["child_idx"])

            if parent_real_id and child_real_id:
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
                        "from_node": str(parent_real_id),
                        "to_node": str(child_real_id),
                        "relation_type": "parent-child"
                    }
                )
                edges_created += 1
            else:
                logger.warning(f"Skipped edge: parent_idx={edge['parent_idx']} child_idx={edge['child_idx']} - ID not found")

        logger.info(f"Successfully created mindmap {mindmap_id} with {len(idx_to_real_id)} nodes and {edges_created} edges")

        return {
            "id": mindmap_id,
            "notebook_id": notebook_id,
            "title": tree.get("root", notebook.name),
            "node_count": len(idx_to_real_id),
            "edge_count": edges_created
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
            "SELECT * FROM mindmap WHERE notebook = $notebook_id ORDER BY created_at DESC LIMIT 1",
            {"notebook_id": ensure_record_id(notebook_id)}
        )

        if not result:
            return None

        mindmap_data = result[0]
        mindmap_id = mindmap_data["id"]

        nodes_result = await repo_query(
            "SELECT * FROM mindmap_node WHERE mindmap = $mindmap_id",
            {"mindmap_id": ensure_record_id(mindmap_id)}
        )

        edges_result = await repo_query(
            "SELECT * FROM mindmap_edge WHERE mindmap = $mindmap_id",
            {"mindmap_id": ensure_record_id(mindmap_id)}
        )

        return {
            "id": str(mindmap_id),
            "notebook_id": notebook_id,
            "title": mindmap_data.get("title"),
            "nodes": [
                {
                    "id": str(n["id"]),
                    "label": n.get("label"),
                    "summary": n.get("summary"),
                    "level": n.get("level", 0),
                    "position_x": n.get("position_x", 0),
                    "position_y": n.get("position_y", 0)
                }
                for n in (nodes_result or [])
            ],
            "edges": [
                {
                    "id": str(e["id"]),
                    "source": str(e.get("from_node")),
                    "target": str(e.get("to_node")),
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

        for mindmap in result:
            mindmap_id = mindmap["id"]
            await repo_query("DELETE FROM mindmap_edge WHERE mindmap = $id", {"id": ensure_record_id(mindmap_id)})
            await repo_query("DELETE FROM mindmap_node WHERE mindmap = $id", {"id": ensure_record_id(mindmap_id)})
            await repo_query("DELETE FROM mindmap WHERE id = $id", {"id": ensure_record_id(mindmap_id)})

        return {"message": "Mind map deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting mindmap for notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
