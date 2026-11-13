with open('/home/deamon/Sentinel_Omega/sentinel_omega/infrastructure/dashboard/web/src/components/tabs/EspacioFirmasTab.tsx', 'r') as f:
    content = f.read()

# Remove duplicate xDeFn, yDeFn, CLASE_COLORS, colorClase, umbralRadio (2nd), exigibleFirmas (2nd)
# Find the section between "const exigibleFirmas = firmasConCoords.filter" and "return ("
import re

# Pattern to match the duplicate section
old_pattern = r'''  const umbralRadio = Math\.min\(640 - 56 - 16, 400 - 8 - 42\) \* 0\.06;

  const exigibleFirmas = firmasConCoords\.filter\(\(f\) => f\.exigible === 1\);

  const xDeFn = \(v: number\) => 56 \+ \(\(v - \(xRange\?\.min \?\? 0\)\) / \(\(xRange\?\.max \?\? 1\) - \(xRange\?\.min \?\? 0\) \|\| 1\)\) \* \(640 - 56 - 16\);
  const yDeFn = \(v: number\) => 8 \+ \(400 - 8 - 42\) - \(\(v - \(yRange\?\.min \?\? 0\)\) / \(\(yRange\?\.max \?\? 1\) - \(yRange\?\.min \?\? 0\) \|\| 1\)\) \* \(400 - 8 - 42\);

  const CLASE_COLORS: Record<string, string> = \{
    SISMO_M4: "var\(--color-serie-1\)",
    SISMO_M5: "var\(--color-serie-2\)",
    SISMO_M6: "var\(--color-serie-3\)",
    SISMO_M7: "var\(--color-serie-4\)",
    ERUPCION: "var\(--color-critico-dim\)",
    TORMENTA_GEOMAGNETICA: "var\(--color-serie-1\)",
    DESGASIFICACION: "var\(--color-serie-2\)",
    DEFAULT: "var\(--color-base-600\)",
  \};

  function colorClase\(clase: string \| null \| undefined\): string \{
    if \(!clase\) return "var\(--color-base-600\)";
    const key = String\(clase\)\.toUpperCase\(\);
    const colors: Record<string, string> = \{
      SISMO_M4: "var\(--color-serie-1\)",
      SISMO_M5: "var\(--color-serie-2\)",
      SISMO_M6: "var\(--color-serie-3\)",
      SISMO_M7: "var\(--color-serie-4\)",
      ERUPCION: "var\(--color-critico-dim\)",
      TORMENTA_GEOMAGNETICA: "var\(--color-serie-1\)",
      DESGASIFICACION: "var\(--color-serie-2\)",
      DEFAULT: "var\(--color-base-600\)",
    \};
    return colors\[key\] \?\? colors\.DEFAULT;
  \}

  const umbralRadio = Math\.min\(640 - 56 - 16, 400 - 8 - 42\) \* 0\.06;

  const exigibleFirmas = firmasConCoords\.filter\(\(f\) => f\.exigible === 1\);

  return \('''

new_text = '''  const umbralRadio = Math.min(640 - 56 - 16, 400 - 8 - 42) * 0.06;

  const exigibleFirmas = firmasConCoords.filter((f) => f.exigible === 1);

  return ('''

new_content = content.replace(old_pattern, new_text)

with open('/home/deamon/Sentinel_Omega/sentinel_omega/infrastructure/dashboard/web/src/components/tabs/EspacioFirmasTab.tsx', 'w') as f:
    f.write(new_content)

print("Fixed!")