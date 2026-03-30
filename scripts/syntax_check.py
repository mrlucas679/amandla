"""Quick syntax check for all modified files."""
import ast
import sys

FILES = [
    "backend/main.py",
    "sasl_transformer/transformer.py",
    "sasl_transformer/config.py",
    "sasl_transformer/routes.py",
    "backend/services/ollama_service.py",
    "backend/services/sign_maps.py",
    "sasl_transformer/grammar_rules.py",
]

ok = True
for path in FILES:
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        ast.parse(source, filename=path)
        print(f"OK  {path}")
    except SyntaxError as e:
        print(f"ERR {path}: {e}")
        ok = False
    except FileNotFoundError:
        print(f"NOT FOUND: {path}")
        ok = False

print("\nAll OK" if ok else "\nSome files FAILED")
sys.exit(0 if ok else 1)

