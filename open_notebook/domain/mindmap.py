from datetime import datetime
from typing import List, Optional, ClassVar
from open_notebook.database.repository import repo_query, ensure_record_id
from open_notebook.domain.base import ObjectModel


class MindMapNode(ObjectModel):
    table_name: ClassVar[str] = 'mindmap_node'
    mindmap: str  # Will be converted to record reference
    label: str
    summary: Optional[str] = None
    level: int = 0
    source_refs: Optional[List[dict]] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None

    def _prepare_save_data(self):
        data = super()._prepare_save_data()
        # Convert mindmap string to record reference
        if 'mindmap' in data and data['mindmap']:
            data['mindmap'] = ensure_record_id(data['mindmap'])
        return data


class MindMapEdge(ObjectModel):
    table_name: ClassVar[str] = 'mindmap_edge'
    mindmap: str
    from_node: str
    to_node: str
    relation_type: str = 'parent-child'

    def _prepare_save_data(self):
        data = super()._prepare_save_data()
        # Convert string IDs to record references
        if 'mindmap' in data and data['mindmap']:
            data['mindmap'] = ensure_record_id(data['mindmap'])
        if 'from_node' in data and data['from_node']:
            data['from_node'] = ensure_record_id(data['from_node'])
        if 'to_node' in data and data['to_node']:
            data['to_node'] = ensure_record_id(data['to_node'])
        return data


class MindMap(ObjectModel):
    table_name: ClassVar[str] = 'mindmap'
    notebook: str
    title: str
    root_node_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def _prepare_save_data(self):
        data = super()._prepare_save_data()
        # Convert notebook string to record reference
        if 'notebook' in data and data['notebook']:
            data['notebook'] = ensure_record_id(data['notebook'])
        # Handle datetime fields - use created_at/updated_at instead of created/updated
        data['created_at'] = data.pop('created', None) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data['updated_at'] = data.pop('updated', None) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Remove root_node_id if None (SurrealDB doesn't like null for string type)
        if data.get('root_node_id') is None:
            data.pop('root_node_id', None)
        return data

    async def get_nodes(self) -> List[MindMapNode]:
        query = "SELECT * FROM mindmap_node WHERE mindmap = $mindmap_id"
        results = await repo_query(query, {"mindmap_id": ensure_record_id(self.id)})
        return [MindMapNode(**r) for r in results] if results else []

    async def get_edges(self) -> List[MindMapEdge]:
        query = "SELECT * FROM mindmap_edge WHERE mindmap = $mindmap_id"
        results = await repo_query(query, {"mindmap_id": ensure_record_id(self.id)})
        return [MindMapEdge(**r) for r in results] if results else []

    async def delete_cascade(self):
        await repo_query("DELETE FROM mindmap_edge WHERE mindmap = $id", {"id": ensure_record_id(self.id)})
        await repo_query("DELETE FROM mindmap_node WHERE mindmap = $id", {"id": ensure_record_id(self.id)})
        await self.delete()
