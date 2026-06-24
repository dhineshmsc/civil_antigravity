def check_brackets(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        for char_num, char in enumerate(line, 1):
            if char in '({[':
                stack.append((char, line_num, char_num))
            elif char in ')}]':
                if not stack:
                    print(f"Mismatched closing bracket '{char}' at line {line_num}, col {char_num}")
                    return False
                top_char, top_line, top_col = stack.pop()
                if top_char != pairs[char]:
                    print(f"Mismatched bracket: '{char}' at line {line_num}, col {char_num} does not match '{top_char}' from line {top_line}, col {top_col}")
                    return False
                    
    if stack:
        print(f"Unclosed brackets left on stack: {len(stack)}")
        for char, line, col in stack[:5]:
            print(f"Unclosed '{char}' at line {line}, col {col}")
        return False
        
    print("All brackets, parentheses, and braces match perfectly!")
    return True

if __name__ == "__main__":
    check_brackets("frontend/static/app.jsx")
