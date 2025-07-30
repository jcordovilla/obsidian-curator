# This script classifies notes from a personal archive using Llama-3.1 to determine their usefulness for a knowledge base.

import os
import re
import json
import random
from markdown_it import MarkdownIt
from llama_cpp import Llama

# ---------------- CONFIG ----------------
NOTES_DIR = '/Users/jose/Documents/Evermd'      # Folder with your .md notes
MODEL_PATH = 'models/llama-3.1-8b-instruct-q6_k.gguf'  # Update if needed
JSON_OUTPUT = 'note_classification.json'
MAX_NOTES = 10
MAX_NOTE_CHARS = 2000  # Lowered to avoid context window errors

def find_md_files(root_folder):
    md_files = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for fname in filenames:
            if fname.endswith('.md'):
                md_files.append(os.path.join(dirpath, fname))
    return md_files

def extract_attachments(md_text):
    pattern = r'\[.*?\]\((.*?)\)'
    return re.findall(pattern, md_text)

def md_to_text(md_text):
    md = MarkdownIt()
    rendered = md.render(md_text)
    plain_text = re.sub(r'\n+', '\n', rendered)
    return plain_text.strip()

def get_llama_response(llm, prompt, max_tokens=512):
    response = llm(prompt=prompt, max_tokens=max_tokens, stop=["</s>", "###"])
    if 'choices' in response:
        return response['choices'][0]['text'].strip()
    else:
        return response['text'].strip()

# Use a smaller context window for stability on Apple Silicon
llm = Llama(model_path=MODEL_PATH, n_gpu_layers=-1, n_ctx=4096, n_threads=8)

notes_data = []
all_md_files = find_md_files(NOTES_DIR)
if len(all_md_files) <= MAX_NOTES:
    selected_md_files = all_md_files
else:
    selected_md_files = random.sample(all_md_files, MAX_NOTES)

for md_file in selected_md_files:
    with open(md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()
    attachments = extract_attachments(md_text)
    plain_text = md_to_text(md_text)
    # Truncate very long notes (should avoid OOM error)
    if len(plain_text) > MAX_NOTE_CHARS:
        print(f"Warning: Truncating {md_file} to first {MAX_NOTE_CHARS} characters")
        plain_text = plain_text[:MAX_NOTE_CHARS]
    notes_data.append({
        'path': md_file,
        'text': plain_text,
        'attachments': attachments
    })

results = []

for note in notes_data:
    prompt = (
        "You are an intelligent assistant helping organize a knowledge base for content creation and knowledge management.\n"
        "Here is a note extracted from a personal archive:\n\n"
        "----\n"
        f"{note['text']}\n"
        "----\n\n"
        "Evaluate the usefulness of this note for a knowledge base meant for future search, learning, and generating new content about infrastructure in all its aspects: planning, design, financing, construction, operation, maintenance, and management.\n"
        "Respond with one word only: 'useful' if the note contains meaningful, structured, or potentially valuable information for knowledge management or content creation. "
        "Respond 'not useful' if the note is clutter, trivial, redundant, incomplete, or not worth keeping. "
        "After your verdict, provide a short reason (max 1 sentence).\n\n"
        "Your answer format:\nVerdict: <useful|not useful>\nReason: <reason>"
    )

    print(f"Processing: {note['path']} ...")
    llm_response = get_llama_response(llm, prompt)
    print(llm_response)
    verdict = "undecided"
    reason = ""
    m = re.search(r"Verdict:\s*(useful|not useful)", llm_response, re.I)
    if m:
        verdict = m.group(1).lower()
    m2 = re.search(r"Reason:\s*(.*)", llm_response, re.I)
    if m2:
        reason = m2.group(1).strip()
    results.append({
        'path': note['path'],
        'verdict': verdict,
        'reason': reason
    })

with open(JSON_OUTPUT, 'w', encoding='utf-8') as jsonfile:
    json.dump(results, jsonfile, ensure_ascii=False, indent=2)

print(f"\nClassification complete. Results saved to {JSON_OUTPUT}")
print("Review your notes and let me know when you're ready for attachment (PDF/image) text extraction.")
