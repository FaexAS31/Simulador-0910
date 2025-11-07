import os
import re
from pathlib import Path

def remove_comments_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        in_docstring = False
        docstring_char = None
        
        for line in lines:
            stripped = line.lstrip()
            
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"
                if not in_docstring:
                    in_docstring = True
                    docstring_char = quote
                    if stripped.count(quote) >= 2:
                        in_docstring = False
                    continue
                elif docstring_char == quote:
                    in_docstring = False
                    continue
            elif in_docstring:
                continue
            
            if '#' in line:
                code_part = ''
                in_string = False
                string_char = None
                escaped = False
                
                for i, char in enumerate(line):
                    if escaped:
                        code_part += char
                        escaped = False
                        continue
                    
                    if char == '\\':
                        code_part += char
                        escaped = True
                        continue
                    
                    if char in ('"', "'") and not in_string:
                        in_string = True
                        string_char = char
                        code_part += char
                    elif char == string_char and in_string:
                        in_string = False
                        string_char = None
                        code_part += char
                    elif char == '#' and not in_string:
                        break
                    else:
                        code_part += char
                
                line = code_part.rstrip() + '\n' if code_part.strip() else ''
            
            if line.strip() or not cleaned_lines or cleaned_lines[-1].strip():
                cleaned_lines.append(line)
        
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        if cleaned_lines:
            cleaned_lines.append('\n')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    base_dir = Path(__file__).parent
    
    exclude_dirs = {'__pycache__', 'migrations', 'env', 'venv', '.git', 'staticfiles', 'media', 'logs'}
    exclude_files = {'remove_comments.py'}
    
    python_files = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and file not in exclude_files:
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to process")
    print("=" * 60)
    
    success_count = 0
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, base_dir)
        if remove_comments_from_file(file_path):
            print(f"✅ {rel_path}")
            success_count += 1
        else:
            print(f"❌ {rel_path}")
    
    print("=" * 60)
    print(f"\n✅ Successfully processed {success_count}/{len(python_files)} files")

if __name__ == '__main__':
    main()
