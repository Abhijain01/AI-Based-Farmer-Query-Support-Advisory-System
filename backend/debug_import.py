import sys
print(f"Python: {sys.executable}")
try:
    print("Attempting to import sentence_transformers...")
    from sentence_transformers import SentenceTransformer
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
