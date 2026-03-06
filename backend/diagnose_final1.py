
import sys
import os
import traceback

# Add backend to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import final1...")
    import final1
    print("SUCCESS: Successfully imported final1.")
except Exception as e:
    print("ERROR: Failed to import final1.")
    print(f"Exception type: {type(e).__name__}")
    print(f"Exception message: {str(e)}")
    traceback.print_exc()
