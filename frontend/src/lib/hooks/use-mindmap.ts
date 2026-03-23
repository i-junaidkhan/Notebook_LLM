import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5055'

interface MindMapData {
    id: string
    notebook_id: string
    title: string
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
        relation_type: string
    }>
}

async function fetchMindMap(notebookId: string): Promise<MindMapData | null> {
    const res = await fetch(`${API_URL}/api/notebooks/${encodeURIComponent(notebookId)}/mindmap`, {
        credentials: 'include',
    })
    if (!res.ok) throw new Error('Failed to fetch mind map')
    return res.json()
}

async function generateMindMap(notebookId: string): Promise<MindMapData> {
    const res = await fetch(`${API_URL}/api/notebooks/${encodeURIComponent(notebookId)}/mindmap`, {
        method: 'POST',
        credentials: 'include',
    })
    if (!res.ok) throw new Error('Failed to generate mind map')
    return res.json()
}

async function deleteMindMap(notebookId: string): Promise<void> {
    const res = await fetch(`${API_URL}/api/notebooks/${encodeURIComponent(notebookId)}/mindmap`, {
        method: 'DELETE',
        credentials: 'include',
    })
    if (!res.ok) throw new Error('Failed to delete mind map')
}

export function useMindMap(notebookId: string) {
    return useQuery({
        queryKey: ['mindmap', notebookId],
        queryFn: () => fetchMindMap(notebookId),
        enabled: !!notebookId,
    })
}

export function useGenerateMindMap() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: generateMindMap,
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['mindmap', data.notebook_id] })
        },
    })
}

export function useDeleteMindMap() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: deleteMindMap,
        onSuccess: (_, notebookId) => {
            queryClient.invalidateQueries({ queryKey: ['mindmap', notebookId] })
        },
    })
}