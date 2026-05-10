content = open('generate_demo_signals.py', encoding='utf-8').read()

# Find the start of cycle 5 block
start_marker = '\n# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n# CYCLE 5'
end_marker = '\ndf_v2 = pd.DataFrame'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print('ERROR: markers not found')
    print('start_idx:', start_idx, 'end_idx:', end_idx)
else:
    new_content = content[:start_idx] + '\n' + content[end_idx:]
    open('generate_demo_signals.py', 'w', encoding='utf-8').write(new_content)
    print('Removed cycle 5. Lines removed:', content[start_idx:end_idx].count('\n'))
