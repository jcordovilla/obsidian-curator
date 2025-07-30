# this script loads markdown notes from a specified directory,
# extracts their text content, and identifies any attachments linked within them.
# It uses the markdown-it library for rendering markdown to text.
import os
import re
from markdown_it import MarkdownIt

NOTES_DIR = '/Users/jose/Documents/Evermd'  # Change to your folder name

def find_md_files(root_folder):
    md_files = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for fname in filenames:
            if fname.endswith('.md'):
                md_files.append(os.path.join(dirpath, fname))
    return md_files

def extract_attachments(md_text):
    # Find markdown links pointing to attachments
    # Example: ![desc](../attachments/file.pdf) or [desc](../attachments/file.pdf)
    pattern = r'\[.*?\]\((.*?)\)'
    return re.findall(pattern, md_text)

def md_to_text(md_text):
    md = MarkdownIt()
    rendered = md.render(md_text)
    # Remove excessive newlines/formatting
    plain_text = re.sub(r'\n+', '\n', rendered)
    return plain_text.strip()

notes_data = []

for md_file in find_md_files(NOTES_DIR):
    with open(md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()
    attachments = extract_attachments(md_text)
    plain_text = md_to_text(md_text)
    notes_data.append({
        'path': md_file,
        'text': plain_text,
        'attachments': attachments
    })

print(f"Found {len(notes_data)} notes.")
for note in notes_data[:3]:
    print("="*40)
    print(f"Path: {note['path']}")
    print(f"Preview: {note['text'][:300]}")
    print(f"Attachments: {note['attachments']}")
