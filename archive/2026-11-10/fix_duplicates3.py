with open('/home/deamon/Sentinel_Omega/sentinel_omega/infrastructure/dashboard/web/src/components/tabs/EspacioFirmasTab.tsx', 'r') as f:
    lines = f.readlines()

# Find the lines to remove (duplicates)
# Lines 203-234 are duplicates that need to be removed
# Line 203: const xDeFn
# Line 204: const yDeFn
# Line 206-215: const CLASE_COLORS
# Line 217-231: function colorClase
# Line 233: const umbralRadio (duplicate)
# Line 234: const exigibleFirmas (duplicate)

new_lines = []
skip = False
skip_until = 0

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Skip duplicate declarations (lines 203-234 in original, but line numbers shifted)
    if 202 <= line_num <= 234:
        # Check if this is part of the duplicate block
        stripped = line.strip()
        if stripped.startswith('const xDeFn') or stripped.startswith('const yDeFn'):
            continue
        if stripped.startswith('const CLASE_COLORS'):
            skip = True
            continue
        if skip and stripped.startswith('};'):
            skip = False
            continue
        if skip:
            continue
        if stripped.startswith('function colorClase'):
            skip = True
            continue
        if skip and stripped.startswith('}') and line.count('}') > line.count('{'):
            skip = False
            continue
        if skip:
            continue
        if stripped.startswith('const umbralRadio') and line_num > 199:
            continue
        if stripped.startswith('const exigibleFirmas') and line_num > 201:
            continue
        if skip:
            continue
    
    new_lines.append(line)

with open('/home/deamon/Sentinel_Omega/sentinel_omega/infrastructure/dashboard/web/src/components/tabs/EspacioFirmasTab.tsx', 'w') as f:
    f.writelines(new_lines)

print("Fixed!")