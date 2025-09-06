#!/usr/bin/env python3
"""
Test script to validate Solarized color values against the official specification.

Official Solarized color palette by Ethan Schoonover:
https://ethanschoonover.com/solarized/
"""

import json
import re
from pathlib import Path

# Official Solarized color palette
OFFICIAL_SOLARIZED_COLORS = {
    'base03': '#002b36',
    'base02': '#073642',
    'base01': '#586e75',
    'base00': '#657b83',
    'base0': '#839496',
    'base1': '#93a1a1',
    'base2': '#eee8d5',
    'base3': '#fdf6e3',
    'yellow': '#b58900',
    'orange': '#cb4b16',
    'red': '#dc322f',
    'magenta': '#d33682',
    'violet': '#6c71c4',
    'blue': '#268bd2',
    'cyan': '#2aa198',
    'green': '#859900'
}

# Expected mappings for solarized dark theme
DARK_THEME_MAPPING = {
    'background': 'base03',
    'foreground': 'base0', 
    'cursor': 'base1',
    'cursorAccent': 'base03',
    'selection': 'base02',
    'black': 'base02',
    'red': 'red',
    'green': 'green',
    'yellow': 'yellow',
    'blue': 'blue',
    'magenta': 'magenta',
    'cyan': 'cyan',
    'white': 'base2',
    'brightBlack': 'base01',
    'brightRed': 'orange',
    'brightGreen': 'base1',
    'brightYellow': 'base00',
    'brightBlue': 'base0',
    'brightMagenta': 'violet',
    'brightCyan': 'base1',
    'brightWhite': 'base3'
}

# Expected mappings for solarized light theme
LIGHT_THEME_MAPPING = {
    'background': 'base3',
    'foreground': 'base00',
    'cursor': 'base01',
    'cursorAccent': 'base3',
    'selection': 'base2',
    'black': 'base02',
    'red': 'red',
    'green': 'green',
    'yellow': 'yellow',
    'blue': 'blue',
    'magenta': 'magenta',
    'cyan': 'cyan',
    'white': 'base2',
    'brightBlack': 'base01',
    'brightRed': 'orange',
    'brightGreen': 'base1',
    'brightYellow': 'base00',
    'brightBlue': 'base0',
    'brightMagenta': 'violet',
    'brightCyan': 'base1',
    'brightWhite': 'base3'
}


def extract_colors_from_js():
    """Extract color definitions from the JavaScript file."""
    js_file_path = Path(__file__).parent / 'static' / 'js' / 'app.js'
    
    if not js_file_path.exists():
        raise FileNotFoundError(f"JavaScript file not found: {js_file_path}")
    
    with open(js_file_path, 'r') as f:
        content = f.read()
    
    # Extract solarizedDarkTheme
    dark_pattern = r'const solarizedDarkTheme = \{(.*?)\};'
    dark_match = re.search(dark_pattern, content, re.DOTALL)
    
    # Extract solarizedLightTheme  
    light_pattern = r'const solarizedLightTheme = \{(.*?)\};'
    light_match = re.search(light_pattern, content, re.DOTALL)
    
    if not dark_match or not light_match:
        raise ValueError("Could not find solarized theme definitions in JavaScript file")
    
    # Parse color values
    def parse_colors(theme_content):
        colors = {}
        color_pattern = r'(\w+):\s*[\'"]([#\w]+)[\'"]'
        for match in re.finditer(color_pattern, theme_content):
            key, value = match.groups()
            colors[key] = value.lower()
        return colors
    
    dark_colors = parse_colors(dark_match.group(1))
    light_colors = parse_colors(light_match.group(1))
    
    return dark_colors, light_colors


def validate_color_values(theme_colors, theme_mapping, theme_name):
    """Validate color values against official palette."""
    errors = []
    
    for key, expected_solarized_name in theme_mapping.items():
        if key not in theme_colors:
            errors.append(f"{theme_name}: Missing color definition for '{key}'")
            continue
        
        actual_color = theme_colors[key]
        expected_color = OFFICIAL_SOLARIZED_COLORS[expected_solarized_name].lower()
        
        if actual_color != expected_color:
            errors.append(
                f"{theme_name}: {key} should be {expected_color} ({expected_solarized_name}) "
                f"but found {actual_color}"
            )
    
    return errors


def main():
    """Main validation function."""
    print("Validating Solarized color values...")
    print("=" * 50)
    
    try:
        # Extract colors from JavaScript
        dark_colors, light_colors = extract_colors_from_js()
        
        # Validate dark theme
        dark_errors = validate_color_values(dark_colors, DARK_THEME_MAPPING, "Dark Theme")
        
        # Validate light theme
        light_errors = validate_color_values(light_colors, LIGHT_THEME_MAPPING, "Light Theme")
        
        # Report results
        total_errors = len(dark_errors) + len(light_errors)
        
        if total_errors == 0:
            print("✅ SUCCESS: All solarized color values are correct!")
            print(f"✅ Dark theme: {len(dark_colors)} colors validated")
            print(f"✅ Light theme: {len(light_colors)} colors validated")
            print(f"✅ All colors match the official Solarized palette specification")
        else:
            print(f"❌ FAILED: Found {total_errors} color validation errors:")
            print()
            
            if dark_errors:
                print("Dark Theme Errors:")
                for error in dark_errors:
                    print(f"  - {error}")
                print()
            
            if light_errors:
                print("Light Theme Errors:")
                for error in light_errors:
                    print(f"  - {error}")
            
            return 1
        
        print()
        print("Official Solarized Palette Reference:")
        print("Base colors:", {k: v for k, v in OFFICIAL_SOLARIZED_COLORS.items() if k.startswith('base')})
        print("Accent colors:", {k: v for k, v in OFFICIAL_SOLARIZED_COLORS.items() if not k.startswith('base')})
        
        return 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1


if __name__ == '__main__':
    exit(main())