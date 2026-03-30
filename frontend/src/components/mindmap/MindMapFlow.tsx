'use client'

import { useCallback, useMemo } from 'react'
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    Node,
    Edge,
    Position,
    Handle,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'

interface MindMapNodeData {
    label: string
    summary?: string
    level: number
}

interface MindMapFlowProps {
    nodes: Array<{
        id: string
        label: string
        summary?: string
        level: number
        position_x?: number
        position_y?: number
    }>
    edges: Array<{
        id: string
        from_node: string
        to_node: string
    }>
    onNodeClick?: (nodeId: string) => void
}

const nodeColors = ['#2563eb', '#0891b2', '#059669', '#d97706', '#dc2626', '#7c3aed', '#c026d3']

const MindMapNode = ({ data }: { data: MindMapNodeData }) => {
    return (
        <div className="px-4 py-2 rounded-lg border bg-white shadow-sm min-w-[120px] text-center">
            <Handle type="target" position={Position.Top} className="opacity-0" />
            <div className="font-medium text-sm text-gray-800">{data.label}</div>
            {data.summary && (
                <div className="text-xs text-gray-500 mt-1 line-clamp-2">{data.summary}</div>
            )}
            <Handle type="source" position={Position.Bottom} className="opacity-0" />
        </div>
    )
}

// Dagre layout helper
const getLayoutedElements = (nodes: any[], edges: any[], direction = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 60 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: 160, height: 60 });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.from_node, edge.to_node);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            position: {
                x: nodeWithPosition.x - 80,
                y: nodeWithPosition.y - 30,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};

export function MindMapFlow({ nodes: inputNodes, edges: inputEdges, onNodeClick }: MindMapFlowProps) {
    const nodeTypes = useMemo(() => ({ mindmap: MindMapNode }), [])

    // Convert input data to React Flow nodes and edges with layout
    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        const flowNodes: Node[] = inputNodes.map((node) => ({
            id: node.id,
            type: 'mindmap',
            data: {
                label: node.label,
                summary: node.summary,
                level: node.level,
            },
            position: { x: 0, y: 0 }, // temporary, will be overwritten
        }));

        const flowEdges: Edge[] = inputEdges.map((edge) => ({
            id: edge.id,
            source: edge.from_node,
            target: edge.to_node,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#94a3b8', strokeWidth: 2 },
        }));

        // Apply layout
        return getLayoutedElements(flowNodes, flowEdges);
    }, [inputNodes, inputEdges]);

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

    return (
        <div className="h-[600px] w-full border rounded-lg">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-right"
            >
                <Background />
                <Controls />
                <MiniMap />
            </ReactFlow>
        </div>
    )
}