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

export function MindMapFlow({ nodes: inputNodes, edges: inputEdges, onNodeClick }: MindMapFlowProps) {
    const nodeTypes = useMemo(() => ({ mindmap: MindMapNode }), [])

    // Calculate tree layout
    const calculateLayout = useCallback(() => {
        const levelWidth = 250
        const nodeHeight = 80
        const levelNodes: { [key: number]: string[] } = {}

        // Group by level
        inputNodes.forEach(node => {
            if (!levelNodes[node.level]) levelNodes[node.level] = []
            levelNodes[node.level].push(node.id)
        })

        const positionedNodes: Node[] = []
        const maxLevel = Math.max(...Object.keys(levelNodes).map(Number))

        for (let level = 0; level <= maxLevel; level++) {
            const nodesAtLevel = levelNodes[level] || []
            const totalHeight = nodesAtLevel.length * nodeHeight
            const startY = -(totalHeight / 2)

            nodesAtLevel.forEach((nodeId, index) => {
                const node = inputNodes.find(n => n.id === nodeId)
                if (node) {
                    positionedNodes.push({
                        id: node.id,
                        type: 'mindmap',
                        position: {
                            x: level * levelWidth,
                            y: startY + (index * nodeHeight),
                        },
                        data: {
                            label: node.label,
                            summary: node.summary,
                            level: node.level,
                        },
                    })
                }
            })
        }

        return positionedNodes
    }, [inputNodes])

    const initialNodes = useMemo(() => calculateLayout(), [calculateLayout])

    const initialEdges: Edge[] = useMemo(() => {
        return inputEdges.map(edge => ({
            id: edge.id,
            source: edge.from_node,
            target: edge.to_node,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#94a3b8', strokeWidth: 2 },
        }))
    }, [inputEdges])

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