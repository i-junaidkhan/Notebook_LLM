import asyncio
from open_notebook.domain.notebook import Notebook

async def run_diag():
    nb = await Notebook.get('notebook:z8bphte7inz4m9h8uf7r')
    if not nb:
        print('Notebook not found!')
        return
        
    sources = await nb.get_sources()
    print(f'Found {len(sources)} sources linked to this notebook.')
    
    for s in sources:
        text_len = len(s.full_text) if s.full_text else 0
        print(f'Source ID: {s.id} | Processing Status: {s.status} | Text Length: {text_len}')
        if text_len == 0:
            print('   -> DIAGNOSIS: This source has no extracted text! The mindmap will fail.')

if __name__ == '__main__':
    asyncio.run(run_diag())
