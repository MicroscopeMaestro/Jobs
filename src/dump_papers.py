import os
from pypdf import PdfReader

papers_dir = 'assets/papers'
for f in sorted(os.listdir(papers_dir)):
    if f.endswith('.pdf'):
        print(f'### Paper: {f}')
        try:
            reader = PdfReader(os.path.join(papers_dir, f))
            text = '\n'.join([p.extract_text() or '' for p in reader.pages])
            print(text[:4000]) # Dump first 4000 chars
        except Exception as e:
            print(f'Error reading {f}: {e}')
        print('\n---\n')
