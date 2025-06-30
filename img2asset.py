#!/usr/bin/env python3
 
import argparse
from PIL import Image, ImageOps
import os
import re
import json

def sanitize_js_var_name(name):
    """
    Sanitizes a string to be a valid JavaScript variable name.

    - Replaces invalid characters with underscores.
    - Prepends an underscore if the name starts with a digit.
    - Appends an underscore if the name is a JavaScript reserved keyword.
    """
    # Replace invalid characters with underscores. Allows letters, numbers, _, and $.
    name = re.sub(r'[^a-zA-Z0-9_$]', '_', name)

    # If the name starts with a digit, prepend an underscore.
    if name and name[0].isdigit():
        name = '_' + name

    # Check against a list of JavaScript reserved words.
    js_keywords = {
        'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
        'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function',
        'if', 'import', 'in', 'instanceof', 'new', 'return', 'super', 'switch',
        'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
        'enum', 'implements', 'interface', 'let', 'package', 'private', 'protected',
        'public', 'static', 'await', 'abstract', 'boolean', 'byte', 'char', 'double',
        'final', 'float', 'goto', 'int', 'long', 'native', 'short', 'synchronized',
        'throws', 'transient', 'volatile', 'null', 'true', 'false'
    }
    if name in js_keywords:
        name += '_'

    return name

def convert_and_resize(input_path, width=None, height=None):
    """
    Converts a JPG image to a 16-color paletted PNG format, with optional
    resizing.
    
    Args:
        input_path (str): The path to the input JPG image file.
        output_path (str): The path where the output PNG image will be saved.
        width (int, optional): The desired width of the output image. Defaults to None.
        height (int, optional): The desired height of the output image. Defaults to None.
    """
    try:
        # Open the JPG image
        img = Image.open(input_path)
        orig_width, orig_height = img.size

        # Handle resizing
        if width is not None and height is not None:
            # Only shrink, never enlarge
            target_width = min(width, orig_width)
            target_height = min(height, orig_height)
            if target_width < orig_width or target_height < orig_height:
                print(f"Resizing and padding image to {target_width}x{target_height} pixels (no enlargement).")
                img = ImageOps.pad(img, (target_width, target_height))
            else:
                print(f"Requested size {width}x{height} is larger than original {orig_width}x{orig_height}. Keeping original size.")
                # No resizing, keep original
        elif width is not None or height is not None:
            # Only one dimension is provided, maintain aspect ratio, only shrink
            if width is not None:
                if width < orig_width:
                    print(f"Resizing image to width {width} while maintaining aspect ratio (no enlargement).")
                    aspect_ratio = orig_height / orig_width
                    new_height = int(width * aspect_ratio)
                    img = img.resize((width, new_height), Image.Resampling.LANCZOS)
                else:
                    print(f"Requested width {width} is larger than original {orig_width}. Keeping original size.")
            else:  # height is not None
                if height < orig_height:
                    print(f"Resizing image to height {height} while maintaining aspect ratio (no enlargement).")
                    aspect_ratio = orig_width / orig_height
                    new_width = int(height * aspect_ratio)
                    img = img.resize((new_width, height), Image.Resampling.LANCZOS)
                else:
                    print(f"Requested height {height} is larger than original {orig_height}. Keeping original size.")
        # The quantize method works on 'L' and 'RGB' modes.
        # We convert to 'RGB' to be safe, as JPGs can be in other modes like 'L' or 'CMYK'.
        img_rgb = img.convert("RGB")
        return img_rgb
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
    return None

def create_palette_from_images(img_rgb):
    """
    Creates a 16-color palette image from the given image.
    This palette image can be used to quantize other images.
    
    Args:
        img_rgb (PIL.Image): The source RGB image to generate a palette from.
    
    Returns:
        PIL.Image: A new 16-color paletted image that can be used as a palette.
    """
    print("Creating a 16-color palette from the image.")
    quantized_img = img_rgb.quantize(colors=16)
    return quantized_img

def create_palette_image_from_hex_list(hex_colors):
    """
    Creates a palette image from a list of hex color strings.

    Args:
        hex_colors (list[str]): A list of hex color strings like "#RRGGBB".

    Returns:
        PIL.Image: A new paletted image that can be used as a palette,
                   or None if the input is invalid.
    """
    try:
        if len(hex_colors) > 16:
            print(f"Warning: {len(hex_colors)} colors provided. Only the first 16 will be used.")
            hex_colors = hex_colors[:16]

        palette_data = []
        for color_str in hex_colors:
            color = color_str.strip().lstrip('#')
            if len(color) != 6:
                raise ValueError(f"Invalid hex color format: '{color_str}'")
            palette_data.extend(bytes.fromhex(color))

        # Pad the palette to 256 colors (768 bytes) as required by putpalette.
        # The first N colors are the custom ones, the rest are black.
        num_colors = len(palette_data) // 3
        palette_data.extend([0, 0, 0] * (256 - num_colors))

        # Create a dummy 1x1 paletted image
        palette_image = Image.new('P', (1, 1))
        palette_image.putpalette(palette_data)
        return palette_image
    except (ValueError, IndexError) as e:
        print(f"Error: Could not parse custom palette. Please check the format. Details: {e}")
        return None

def create_palette_from_json_file(file_path):
    """
    Creates a palette image from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        PIL.Image: A new paletted image that can be used as a palette,
                   or None if the input is invalid.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'palette' not in data or not isinstance(data['palette'], list):
            raise ValueError("JSON file must contain a 'palette' key with a list of hex color strings.")
            
        return create_palette_image_from_hex_list(data['palette'])
    except FileNotFoundError:
        print(f"Error: Palette file not found at '{file_path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Please check for syntax errors.")
        return None
    except ValueError as e:
        print(f"Error: Invalid palette JSON format. {e}")
        return None

def create_palette_from_hex_colors(hex_colors_str):
    """
    Creates a palette image from a comma-separated string of hex colors.

    Args:
        hex_colors_str (str): A string like "#RRGGBB,#RRGGBB,..."

    Returns:
        PIL.Image: A new paletted image that can be used as a palette,
                   or None if the input is invalid.
    """
    colors = [c.strip() for c in hex_colors_str.split(',')]
    return create_palette_image_from_hex_list(colors)

def write_asset_files(img_rgb, img_name, asset_path, palette_image):
    """
    Write the image to PNG file and create TypeScript asset files. 

    Args:
        img_rgb (PIL.Image): The source RGB PIL image object.
        img_name (str): The base name for the output files.
        asset_path (str): The path where the asset files will be saved.
        palette_image (PIL.Image): The palette image to apply.
    """
    output_path = f"{img_name}.png"

    var_name = sanitize_js_var_name(os.path.basename(img_name))
    # Apply the palette from the palette_image
    print(f"Applying palette to create '{os.path.basename(output_path)}'.")
    quantized_img = img_rgb.quantize(palette=palette_image)
    with open(asset_path, 'w') as f_asset:
        # Get and write the palette as a hex string from the palette_image
        palette_data = palette_image.getpalette()
        if palette_data:
            # The palette is a flat list of R,G,B values.
            # We take the first 16 colors (48 values).
            hex_palette = "".join([f"{x:02X}" for x in palette_data[:16*3]])
            f_asset.write(f'namespace palettes {{\n    export const {var_name}_Colors = color.bufferToPalette(hex`{hex_palette}`);\n}}\n\n')

        # Get and write the pixel data as a hex string in column-major order.
        img_width, img_height = quantized_img.size
        packed_bytes = bytearray()

        # Iterate column by column, from left to right.
        for x in range(img_width):
            # Within each column, pixels are read from top to bottom.
            # Two 4-bit pixels are packed into one byte.
            for y in range(0, img_height, 2):
                # The first pixel (at y) goes into the lower 4 bits.
                pixel1 = quantized_img.getpixel((x, y))
                # The second pixel (at y+1) goes into the higher 4 bits.
                # If height is odd, the last pixel is paired with 0.
                pixel2 = quantized_img.getpixel((x, y + 1)) if y + 1 < img_height else 0

                byte = (pixel2 << 4) | (pixel1 & 0x0F)
                packed_bytes.append(byte)

        pixel_hex_string = packed_bytes.hex().upper()
        f_asset.write(f'namespace images {{\n    export const {var_name} = \nimage.ofBuffer(hex`e4{img_width:02X}{img_height:02X}00{pixel_hex_string}`);\n}}\n')

    print(f"TypeScript asset file created at '{asset_path}'")
    # Save the image as PNG, making color index 0 transparent.
    quantized_img.save(output_path, transparency=0)
    print(f"Image successfully saved to '{output_path}'")

def main():
    """
    Command-line interface for converting JPG to PNG.
    """
    parser = argparse.ArgumentParser(
        description="Create MakeCode Arcade compatible asset from image and save a PNG file for reference.",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("input_path", help="The path to the input JPG image file.")
    parser.add_argument("output_path", nargs='?', default=None,
                        help="The path for the output PNG file.\n"
                             "If omitted, the input filename with a .png extension will be used.")
    parser.add_argument("-w", "--width", type=int, help=
        "The desired width of the output image in pixels.\n"
        "Defaults to 160 if --height is also omitted.\n"
        "If only --width is provided, height is scaled to maintain aspect ratio.")
    parser.add_argument("--height", type=int, help=
        "The desired height of the output image in pixels.\n"
        "Defaults to 120 if --width is also omitted.\n"
        "If only --height is provided, width is scaled to maintain aspect ratio.")
    
    palette_group = parser.add_mutually_exclusive_group()
    palette_group.add_argument("--palette", type=str, help=
        "A comma-separated list of hex colors (e.g., '#FF0000,#00FF00') to use as a custom palette.\n"
        "The first color is used for transparency. Up to 16 colors are supported.\n"
        "If provided, this palette is used instead of generating one from the image.")
    palette_group.add_argument("--palette-file", type=str, help=
        "Path to a JSON file containing a custom palette.\n"
        "The JSON should have a 'palette' key with a list of hex color strings.\n"
        "e.g., {\"palette\": [\"#000000\", \"#FFFFFF\", ...]}"
    )
    
    args = parser.parse_args()

    input_path = args.input_path
    output_path = args.output_path
    width = args.width
    height = args.height

    # If no dimensions are specified, default to 160x120
    if width is None and height is None:
        width = 160
        height = 120
 
    # Determine base name for output files
    if output_path:
        # Use the provided output path for the base name (without extension)
        base_name = os.path.splitext(output_path)[0]
    else:
        # Use the input path for the base name (without extension)
        base_name = os.path.splitext(os.path.basename(input_path))[0]

    asset_path = f"{base_name}.ts"

    img_to_process = convert_and_resize(input_path, width=width, height=height)
    if img_to_process is not None:
        palette_image = None
        if args.palette:
            print("Using custom palette provided via command line.")
            palette_image = create_palette_from_hex_colors(args.palette)
        elif args.palette_file:
            print(f"Using custom palette from file: {args.palette_file}")
            palette_image = create_palette_from_json_file(args.palette_file)
        if palette_image is None:
            print("Generating a 16-color palette from the image.")
            palette_image = create_palette_from_images(img_to_process)

        if palette_image:
            write_asset_files(img_to_process, base_name, asset_path, palette_image)

if __name__ == "__main__":
    main()
