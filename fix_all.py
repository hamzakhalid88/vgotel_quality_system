# fix_all.py - Create this file in your project root
import sys
import traceback
from PyQt5.QtWidgets import QLineEdit as OriginalQLineEdit

class FixedQLineEdit(OriginalQLineEdit):
    """Fixed QLineEdit that handles integer arguments gracefully"""
    def __init__(self, *args, **kwargs):
        # Filter out integer arguments
        filtered_args = []
        for arg in args:
            if isinstance(arg, int):
                print(f"⚠️ Fixed QLineEdit: Removed integer argument {arg}")
                continue
            filtered_args.append(arg)
        
        # Filter kwargs (keep parent if it's a widget)
        filtered_kwargs = {}
        for key, value in kwargs.items():
            if key == 'parent' or not isinstance(value, int):
                filtered_kwargs[key] = value
        
        try:
            super().__init__(*filtered_args, **filtered_kwargs)
        except Exception as e:
            print(f"⚠️ QLineEdit fallback: {e}")
            super().__init__()

# Replace globally
import PyQt5.QtWidgets
PyQt5.QtWidgets.QLineEdit = FixedQLineEdit

print("✅ fix_all: QLineEdit patched successfully!")