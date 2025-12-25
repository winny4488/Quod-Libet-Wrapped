#!/usr/bin/env python3
"""
Diagnostic script to inspect Quod Libet database structure
"""

import pickle
import sys

# Disable the validation by monkey-patching before loading
class MockAudioFile(dict):
    """Mock class to bypass validation"""
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)

db_path = "/home/user/.config/quodlibet/songs"

try:
    # Try to import and patch quodlibet if available
    try:
        import quodlibet.formats._audio
        original_setitem = quodlibet.formats._audio.AudioFile.__setitem__
        quodlibet.formats._audio.AudioFile.__setitem__ = lambda self, k, v: dict.__setitem__(self, k, v)
        print("Patched Quod Libet classes")
    except ImportError:
        print("Quod Libet module not found, using alternative method")
    
    with open(db_path, "rb") as f:
        songs_db = pickle.load(f)
    
    print(f"Database type: {type(songs_db)}")
    print(f"Database length: {len(songs_db) if hasattr(songs_db, '__len__') else 'N/A'}")
    print()
    
    # Try to get first few items
    if isinstance(songs_db, list):
        print("Database is a list")
        if songs_db:
            first_item = songs_db[0]
            print(f"First item type: {type(first_item)}")
            
            if isinstance(first_item, dict) or hasattr(first_item, 'keys'):
                print(f"Available keys in song object: {list(first_item.keys())[:20]}")
                print()
                
                # Look for playcount
                for key in first_item.keys():
                    if 'play' in str(key).lower():
                        print(f"Found play-related key: {key} = {first_item[key]}")
                
                print()
                print("Sample song data:")
                sample_keys = ['title', 'artist', 'album', '~#playcount', '~#lastplayed', '~filename']
                for key in sample_keys:
                    if key in first_item:
                        print(f"  {key}: {first_item[key]}")
        
    elif isinstance(songs_db, dict):
        print("Database is a dictionary")
        keys = list(songs_db.keys())[:3]
        print(f"First 3 key types: {[type(k) for k in keys]}")
        print(f"First 3 keys (truncated): {[str(k)[:80] for k in keys]}")
        print()
        
        if keys:
            first_key = keys[0]
            first_value = songs_db[first_key]
            print(f"First value type: {type(first_value)}")
            
            if isinstance(first_value, dict) or hasattr(first_value, 'keys'):
                print(f"Available keys in song object: {list(first_value.keys())[:20]}")
                print()
                
                # Look for playcount
                for key in first_value.keys():
                    if 'play' in str(key).lower():
                        print(f"Found play-related key: {key} = {first_value[key]}")
                
                print()
                print("Sample song data:")
                sample_keys = ['title', 'artist', 'album', '~#playcount', '~#lastplayed']
                for key in sample_keys:
                    if key in first_value:
                        print(f"  {key}: {first_value[key]}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
