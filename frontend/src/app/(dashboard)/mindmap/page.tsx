'use client'

import { useState, useEffect } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, RefreshCw, Loader2, Network } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useMindMap, useGenerateMindMap } from '@/lib/hooks/use-mindmap'
import { MindMapFlow } from '@/components/mindmap/MindMapFlow'
import { useToast } from '@/lib/hooks/use-toast'

export default function MindMapPage() {
    const { t } = useTranslation()
    const { toast } = useToast()
    const [selectedNotebookId, setSelectedNotebookId] = useState<string>('')

    const { data: notebooks, isLoading: notebooksLoading } = useNotebooks()
    const { data: mindmap, isLoading: mindmapLoading, refetch } = useMindMap(selectedNotebookId)
    const { mutate: generate, isPending: isGenerating } = useGenerateMindMap()

    useEffect(() => {
        if (!selectedNotebookId && notebooks && notebooks.length > 0) {
            setSelectedNotebookId(notebooks[0].id)
        }
    }, [notebooks, selectedNotebookId])

    const handleGenerate = () => {
        if (!selectedNotebookId) return
        generate(selectedNotebookId, {
            onSuccess: () => {
                toast({ title: "Success", description: "Mind map generated" })
                refetch()
            },
            onError: (err) => {
                toast({ title: "Error", description: err.message, variant: "destructive" })
            }
        })
    }

    return (
        <AppShell>
            <div className="flex-1 flex flex-col h-full overflow-hidden">
                <div className="p-6 space-y-6 flex-shrink-0 border-b bg-background z-10">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-2 bg-primary/10 rounded-lg">
                                <Network className="h-6 w-6 text-primary" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold">Mind Map</h1>
                                <p className="text-sm text-muted-foreground">Visualize notebook concepts</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="w-[250px]">
                                <Select value={selectedNotebookId} onValueChange={setSelectedNotebookId} disabled={notebooksLoading}>
                                    <SelectTrigger><SelectValue placeholder="Select a notebook..." /></SelectTrigger>
                                    <SelectContent>
                                        {notebooks?.map((nb: any) => (
                                            <SelectItem key={nb.id} value={nb.id}>{nb.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button variant="outline" size="icon" onClick={() => refetch()} disabled={!selectedNotebookId || mindmapLoading}>
                                <RefreshCw className={`h-4 w-4 ${mindmapLoading ? 'animate-spin' : ''}`} />
                            </Button>
                            <Button onClick={handleGenerate} disabled={!selectedNotebookId || isGenerating}>
                                {isGenerating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
                                {mindmap ? 'Regenerate' : 'Generate Map'}
                            </Button>
                        </div>
                    </div>
                </div>
                <div className="flex-1 bg-slate-50 relative overflow-hidden">
                    {!selectedNotebookId ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
                            <Network className="h-16 w-16 mb-4 opacity-20" />
                            <p>Select a notebook to view its mind map</p>
                        </div>
                    ) : mindmapLoading ? (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                    ) : mindmap?.nodes?.length ? (
                        <div className="w-full h-full p-4">
                            <MindMapFlow nodes={mindmap.nodes} edges={mindmap.edges} />
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-muted-foreground">
                            <div className="bg-white p-8 rounded-full shadow-sm">
                                <Network className="h-12 w-12 text-slate-300" />
                            </div>
                            <div className="text-center">
                                <h3 className="font-medium text-lg text-foreground">No Mind Map Found</h3>
                                <p className="text-sm max-w-sm mt-1">Generate a mind map to visualize concepts in this notebook.</p>
                            </div>
                            <Button onClick={handleGenerate} disabled={isGenerating}>Generate Now</Button>
                        </div>
                    )}
                </div>
            </div>
        </AppShell>
    )
}