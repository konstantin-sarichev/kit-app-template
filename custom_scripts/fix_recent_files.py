import carb.settings
import logging

def fix_recent_files():
    """
    Clears the recent files list in Kit settings to resolve 'bad menu item' errors.
    Run this script from the Script Editor in Omniverse.
    """
    print("Checking for recent files settings...")
    settings = carb.settings.get_settings()

    # Common keys for recent files in Kit
    keys_to_check = [
        "/persistent/app/file/recentFiles",
        "/app/file/recentFiles",
        "/persistent/app/files/recent",
        "/app/files/recent"
    ]

    cleared = False
    for key in keys_to_check:
        recent = settings.get(key)
        if recent:
            print(f"Found recent files at '{key}': {recent}")
            # Clear it
            settings.set(key, [])
            print(f"✓ Cleared '{key}'")
            cleared = True
        else:
            print(f"No recent files at '{key}'")

    if cleared:
        print("\nSUCCESS: Recent files cleared. Please restart the application.")
    else:
        print("\nNo recent files found to clear. The setting key might be different.")

if __name__ == "__main__":
    fix_recent_files()
