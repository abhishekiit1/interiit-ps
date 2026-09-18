import os
import re

directory = 'agent/nodes'
for filename in os.listdir(directory):
    if filename.endswith(".py"):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Ensure 'import os' is at the top if we use __file__
        if 'import os' not in content:
            content = "import os\n" + content
            
        # Replace load_prompt("../prompts/...") with os.path.join
        pattern = r'load_prompt\("\.\./prompts/([^"]+)"\)'
        replacement = r'load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/\1"))'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Fixed {filename}")
