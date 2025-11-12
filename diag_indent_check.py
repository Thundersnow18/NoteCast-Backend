import re
p = r'd:\Notecast\backend\pdf_podcast_converter.py'
with open(p, 'rb') as f:
    data = f.read()

# Check for mixed tabs/spaces
lines = data.splitlines()
print('Total lines:', len(lines))

tab_lines = [i+1 for i,l in enumerate(lines) if b'\t' in l]
if tab_lines:
    print('Lines with TAB chars:', tab_lines[:50])
else:
    print('No TAB chars found')

# Detect lines that are indented at top level (no preceding def/class) by scanning naive state
indent_issues = []
block_stack = []
for i,line in enumerate(lines):
    s = line.decode('utf-8', errors='replace')
    stripped = s.lstrip()
    indent = len(s) - len(stripped)
    # skip blank lines
    if not stripped.strip():
        continue
    # find top-level keywords
    if stripped.startswith('def ') or stripped.startswith('class '):
        block_stack.append(indent)
        continue
    # if line is indented but we have no block_stack (i.e., top-level indented line)
    if indent > 0 and not block_stack:
        indent_issues.append((i+1, indent, s.rstrip()))
    # if line dedents below current top of stack, pop stacks
    while block_stack and indent <= block_stack[-1]:
        block_stack.pop()

if indent_issues:
    print('\nTop-level indented lines (possible unexpected indent):')
    for ln,ind,text in indent_issues[:50]:
        print(f'{ln}: indent={ind} | {text}')
else:
    print('\nNo obvious top-level unexpected indents found')

# Print context for last 30 lines to help scanning
print('\n--- Last 40 lines for manual inspection ---')
for i,l in enumerate(lines[-40:], start=len(lines)-40+1):
    print(f'{i:4}: {l.decode("utf-8", errors="replace").rstrip()}')
