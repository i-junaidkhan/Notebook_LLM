from datetime import datetime
from typing import List, Optional, ClassVar
from open_notebook.database.repository import repo_create, repo_query, repo_delete
from open_notebook.domain.base import BaseModel

class MindMapNode(BaseModel):
    table_name: ClassVar[str] = 'mindmap_node'
    mindmap: str
    label: str
    summary: Optional[str] = None
    level: int = 0
    source_refs: Optional[List[dict]] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None

class MindMapEdge(BaseModel):
    table_name: ClassVar[str] = 'mindmap_edge'
    mindmap: str
    from_node: str
    to_node: str
    relation_type: str = 'parent-child'

class MindMap(BaseModel):
    table_name: ClassVar[str] = 'mindmap'
    notebook: str
    title: str
    root_node_id: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    async def get_nodes(self) -> List[MindMapNode]:
        query = "SELECT * FROM mindmap_node WHERE mindmap = $mindmap_id"
        results = await repo_query(query, {"mindmap_id": self.id})
        return [MindMapNode(**r) for r in results] if results else []
    
    async def get_edges(self) -> List[MindMapEdge]:
        query = "SELECT * FROM mindmap_edge WHERE mindmap = $mindmap_id"
        results = await repo_query(query, {"mindmap_id": self.id})
        return [MindMapEdge(**r) for r in results] if results else []
    
    async def delete_cascade(self):
        await repo_query("DELETE FROM mindmap_edge WHERE mindmap = $id", {"id": self.id})
        await repo_query("DELETE FROM mindmap_node WHERE mindmap = $id", {"id": self.id})
        await self.delete()