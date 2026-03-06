
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import final1...")
    import final1
    print("✅ Successfully imported final1.Backend starts up correctly.")
except Exception as e:
    print(f"❌ Failed to import final1: {e}")
    import traceback
    traceback.print_exc()
