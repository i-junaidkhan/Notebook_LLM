'use client'

import { useMemo, useEffect } from 'react'
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
        source?: string
        target?: string
        from_node?: string  // Fallback for old API format
        to_node?: string    // Fallback for old API format
        relation_type?: string
    }>
    onNodeClick?: (nodeId: string) => void
}

const MindMapNode = ({ data }: { data: MindMapNodeData }) => {
    const levelColors = [
        'bg-blue-600 text-white border-blue-700',
        'bg-cyan-500 text-white border-cyan-600',
        'bg-emerald-400 text-white border-emerald-500',
        'bg-slate-200 text-gray-800 border-slate-300',
    ]
    const colorClass = levelColors[Math.min(data.level, levelColors.length - 1)]

    return (
        <div className={`px-4 py-3 rounded-lg border-2 shadow-lg min-w-[150px] max-w-[220px] text-center ${colorClass}`}>
            <Handle type="target" position={Position.Top} className="!bg-gray-500 !w-3 !h-3" />
            <div className="font-bold text-sm">{data.label}</div>
            {data.summary && data.summary.trim() !== '' && (
                <div className="text-xs mt-1 opacity-80 line-clamp-2">{data.summary}</div>
            )}
            <Handle type="source" position={Position.Bottom} className="!bg-gray-500 !w-3 !h-3" />
        </div>
    )
}

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
    if (nodes.length === 0) return { nodes: [], edges: [] }

    const dagreGraph = new dagre.graphlib.Graph()
    dagreGraph.setDefaultEdgeLabel(() => ({}))
    dagreGraph.setGraph({
        rankdir: direction,
        ranksep: 150,
        nodesep: 100,
        marginx: 50,
        marginy: 50
    })

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: 200, height: 80 })
    })

    // Only add edges if they have valid source and target
    edges.forEach((edge) => {
        if (edge.source && edge.target) {
            dagreGraph.setEdge(edge.source, edge.target)
        }
    })

    dagre.layout(dagreGraph)

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id)
        if (nodeWithPosition) {
            return {
                ...node,
                position: {
                    x: nodeWithPosition.x - 100,
                    y: nodeWithPosition.y - 40,
                },
            }
        }
        // Fallback position if dagre fails
        return {
            ...node,
            position: { x: 0, y: (node.data as MindMapNodeData).level * 150 }
        }
    })

    return { nodes: layoutedNodes, edges }
}

export function MindMapFlow({ nodes: inputNodes, edges: inputEdges, onNodeClick }: MindMapFlowProps) {
    const nodeTypes = useMemo(() => ({ mindmap: MindMapNode }), [])

    // DEBUG: Log what data we're receiving
    useEffect(() => {
        console.log('=== MINDMAP DEBUG ===')
        console.log('Input Nodes:', inputNodes)
        console.log('Input Edges:', inputEdges)
        console.log('Node count:', inputNodes?.length)
        console.log('Edge count:', inputEdges?.length)
        if (inputEdges?.length > 0) {
            console.log('First edge structure:', inputEdges[0])
        }
        console.log('=====================')
    }, [inputNodes, inputEdges])

    const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
        if (!inputNodes || inputNodes.length === 0) {
            return { nodes: [], edges: [] }
        }

        const flowNodes: Node[] = inputNodes.map((node) => ({
            id: node.id,
            type: 'mindmap',
            data: {
                label: node.label || 'Untitled',
                summary: node.summary || '',
                level: node.level ?? 0,
            },
            position: { x: 0, y: 0 },
        }))

        // Handle BOTH old and new API formats for edges
        const flowEdges: Edge[] = (inputEdges || []).map((edge) => ({
            id: edge.id,
            source: edge.source || edge.from_node || '',  // Try new format first, fallback to old
            target: edge.target || edge.to_node || '',    // Try new format first, fallback to old
            type: 'smoothstep',
            animated: false,
            style: {
                stroke: '#475569',
                strokeWidth: 3
            },
        })).filter(edge => edge.source && edge.target)  // Remove invalid edges

        console.log('Processed flowEdges:', flowEdges)

        return getLayoutedElements(flowNodes, flowEdges, 'TB')

    }, [inputNodes, inputEdges])

    const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges)

    // Update nodes/edges when layouted data changes
    useEffect(() => {
        setNodes(layoutedNodes)
        setEdges(layoutedEdges)
    }, [layoutedNodes, layoutedEdges, setNodes, setEdges])

    if (!layoutedNodes || layoutedNodes.length === 0) {
        return (
            <div className="h-[600px] w-full border rounded-lg flex items-center justify-center bg-gray-50">
                <p className="text-gray-500">No mindmap data available. Generate a mindmap first.</p>
            </div>
        )
    }

    return (
        <div className="h-[700px] w-full border rounded-lg bg-slate-50">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.3 }}
                attributionPosition="bottom-right"
                minZoom={0.1}
                maxZoom={2}
            >
                <Background color="#cbd5e1" gap={20} size={2} />
                <Controls />
                <MiniMap
                    nodeColor={(node) => {
                        const level = (node.data as MindMapNodeData)?.level ?? 0
                        const colors = ['#2563eb', '#0891b2', '#34d399', '#94a3b8']
                        return colors[Math.min(level, colors.length - 1)]
                    }}
                    maskColor="rgba(0,0,0,0.1)"
                />
            </ReactFlow>
        </div>
    )
}
