#!/usr/bin/env python3
 
import argparse
from PIL import Image, ImageOps
import os
import re
import json
import glob

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

def convert_and_resize(input_path, width=None, height=None, scale_mode="fit"):
    """
    Converts an image to RGBA format, with optional resizing.
    Images are only shrunk, never enlarged.
    
    Args:
        input_path (str): The path to the input image file.
        width (int, optional): The desired width of the output image. Defaults to None.
        height (int, optional): The desired height of the output image. Defaults to None.
        scale_mode (str): How to handle aspect ratio mismatch - "fit" or "fill". Defaults to "fit".
    """
    try:
        # Open the image
        img = Image.open(input_path)
        orig_width, orig_height = img.size

        # Handle resizing
        if width is not None and height is not None:
            # Only shrink, never enlarge
            target_width = min(width, orig_width)
            target_height = min(height, orig_height)
            if target_width < orig_width or target_height < orig_height:
                if scale_mode == "fill":
                    print(f"Resizing and cropping image to {target_width}x{target_height} pixels (fill mode).")
                    img = ImageOps.fit(img, (target_width, target_height))
                else:  # fit mode (default)
                    print(f"Resizing and padding image to {target_width}x{target_height} pixels (fit mode).")
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
        # Convert to RGBA to support transparency in intermediate format
        img_rgba = img.convert("RGBA")
        return img_rgba
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
    return None

def create_palette_from_image(img_rgba):
    """
    Creates a 16-color palette from the image, reserving index 0 for transparency.
    
    Args:
        img_rgba (PIL.Image): The source RGBA image to generate a palette from.
    
    Returns:
        PIL.Image: A new 16-color paletted image that can be used as a palette.
    """
    # To generate a palette from image content, we should only consider opaque pixels.
    # Create a version of the image with a white background to avoid the alpha channel
    # influencing the quantizer.
    img_rgb = Image.new("RGB", img_rgba.size, (255, 255, 255))
    img_rgb.paste(img_rgba, mask=img_rgba.getchannel('A'))

    print("Creating a 15-color palette from the image, reserving color 0 for transparency.")
    # Quantize to 15 colors for the image content.
    quantized_to_15 = img_rgb.quantize(colors=15)
    
    # Get the 15-color palette (45 bytes)
    palette_15_colors = quantized_to_15.getpalette()[:15*3]
    
    # Create a new 16-color palette: [transparent_color] + [15 image colors]
    # Use black for the transparent color placeholder and pad to 256 colors.
    final_palette_data = [0, 0, 0] + palette_15_colors
    final_palette_data.extend([0, 0, 0] * (256 - 16))
    
    # Create a dummy 1x1 paletted image to hold our new palette.
    palette_image = Image.new('P', (1, 1))
    palette_image.putpalette(final_palette_data)
    return palette_image

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

def write_asset_files(imgs_rgba, img_names, asset_path, palette_image):
    """
    Write the images to PNG files and create TypeScript asset file for all images.
    Args:
        imgs_rgba (list[PIL.Image]): List of RGBA PIL image objects.
        img_names (list[str]): List of base names for the output files.
        asset_path (str): The path where the asset file will be saved.
        palette_image (PIL.Image): The palette image to apply.
    """
    with open(asset_path, 'w') as f_asset:
        # Write palette once
        palette_data = palette_image.getpalette()
        if palette_data:
            hex_palette = "".join([f"{x:02X}" for x in palette_data[:16*3]])
            f_asset.write(f'namespace palettes {{\n    export const shared_Colors = color.bufferToPalette(hex`{hex_palette}`);\n}}\n\n')

        f_asset.write('namespace images {\n')
        for img_rgba, img_name in zip(imgs_rgba, img_names):
            var_name = sanitize_js_var_name(os.path.basename(img_name))
            print(f"Applying palette to create '{os.path.basename(img_name)}'.")

            # Ensure source is RGBA to access alpha channel
            if img_rgba.mode != "RGBA":
                img_rgba = img_rgba.convert("RGBA")

            # Check for transparency in the source image to decide quantization strategy
            has_transparency = img_rgba.getchannel('A').getextrema()[0] < 255

            if has_transparency:
                # For images with transparent pixels, map them to index 0.
                quantized_rgb_part = img_rgba.convert("RGB").quantize(palette=palette_image)

                # Find which palette index is black (0,0,0)
                pal = palette_image.getpalette()[:16*3]
                black_rgb = (0, 0, 0)
                black_index = None
                for i in range(16):
                    if tuple(pal[i*3:i*3+3]) == black_rgb:
                        black_index = i
                        break
                if black_index is None:
                    black_index = 15  # fallback

                # Create a new paletted image, initialized to color index 0 (transparent).
                quantized_img = Image.new("P", img_rgba.size, 0)
                quantized_img.putpalette(palette_image.getpalette())

                # Prepare the quantized data, remapping black_index to 15
                quantized_data = list(quantized_rgb_part.getdata())
                remapped_data = []
                alpha_data = list(img_rgba.getchannel('A').getdata())
                for q, a in zip(quantized_data, alpha_data):
                    if a == 0:
                        remapped_data.append(0)  # transparent
                    elif q == black_index:
                        remapped_data.append(15)  # black
                    else:
                        # Avoid assigning transparent index to opaque pixels
                        if q == 0:
                            remapped_data.append(1)  # shift to a non-transparent index
                        else:
                            remapped_data.append(q)
                quantized_img.putdata(remapped_data)
            else:
                # For opaque images, quantize to the 15 non-transparent colors and shift indices.
                full_palette_data = palette_image.getpalette()
                
                # 1. Create a temporary 15-color palette (from index 1-15) for the quantizer.
                palette_for_quantization_data = full_palette_data[3:16*3]
                temp_palette_image = Image.new("P", (1, 1))
                temp_palette_image.putpalette(palette_for_quantization_data + ([0, 0, 0] * (256 - 15)))
                
                # 2. Quantize the image using only these 15 colors. The result has indices 0-14.
                quantized_to_15_colors = img_rgba.convert("RGB").quantize(palette=temp_palette_image)
                
                # 3. Create the final image, remapping pixel indices from 0-14 to 1-15 to avoid using index 0.
                quantized_img = Image.new("P", img_rgba.size)
                quantized_img.putpalette(full_palette_data)
                quantized_img.putdata([p + 1 for p in quantized_to_15_colors.getdata()])

            img_width, img_height = quantized_img.size
            packed_bytes = bytearray()
            for x in range(img_width):
                for y in range(0, img_height, 2):
                    pixel1 = quantized_img.getpixel((x, y))
                    pixel2 = quantized_img.getpixel((x, y + 1)) if y + 1 < img_height else 0
                    byte = (pixel2 << 4) | (pixel1 & 0x0F)
                    packed_bytes.append(byte)
            pixel_hex_string = packed_bytes.hex().upper()
            f_asset.write(f'    export const {var_name} = \nimage.ofBuffer(hex`e4{img_width:02X}{img_height:02X}00{pixel_hex_string}`);\n\n')
            # img`` format
            img_tag_rows = []
            hex_digits = ".123456789abcdef"
            for y in range(img_height):
                row_str = [(hex_digits[quantized_img.getpixel((x, y))]) for x in range(img_width)]
                img_tag_rows.append(" ".join(row_str))
            img_tag_content = "\n".join([f"    {row}" for row in img_tag_rows])
            f_asset.write(f'    //% imghres\n    export const {var_name}_img = img`\n{img_tag_content}\n`\n\n')
            # Save PNG to output dir
            output_dir = os.path.dirname(asset_path)
            output_path = os.path.join(output_dir, f"{img_name}.png")
            quantized_img.save(output_path, transparency=0)
            print(f"Image successfully saved to '{output_path}'")
        f_asset.write('}\n')
        print(f"TypeScript asset file created at '{asset_path}'")

def main():
    """
    Command-line interface for converting images to MakeCode Arcade assets.
    """
    parser = argparse.ArgumentParser(
        description="Create MakeCode Arcade compatible asset(s) from image(s) and save PNG file(s) for reference.",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("input_path", nargs='+',
                        help="The path(s) to the input image file(s), supports wildcards (e.g. '*.bmp').")
    parser.add_argument("-o", "--output", default=".",
                        help="Directory where output files will be saved.\nDefaults to current directory.")
    parser.add_argument("-w", "--width", type=int, help=
        "The desired width of the output image(s) in pixels.\nDefaults to 160 if --height is also omitted.\n"
        "If only --width is provided, height is scaled to maintain aspect ratio.")
    parser.add_argument("-H","--height", type=int, help=
        "The desired height of the output image(s) in pixels.\nDefaults to 120 if --width is also omitted.\n"
        "If only --height is provided, width is scaled to maintain aspect ratio.")
    parser.add_argument("-s", "--scale", choices=["fit", "fill"], default="fit", help=
        "How to handle aspect ratio mismatch when both width and height are specified.\n"
        "'fit' (default): pad image to fit within dimensions, maintaining aspect ratio.\n"
        "'fill': crop image to fill dimensions, maintaining aspect ratio.")
    palette_group = parser.add_mutually_exclusive_group()
    palette_group.add_argument("-p", "--palette", type=str, help=
        "A comma-separated list of hex colors (e.g., '#FF0000,#00FF00') to use as a custom palette.\n"
        "The first color is used for transparency. Up to 16 colors are supported.\n"
        "If provided, this palette is used instead of generating one from the image(s).")
    palette_group.add_argument("-f", "--palette-file", type=str, help=
        "Path to a JSON file containing a custom palette.\n"
        "The JSON should have a 'palette' key with a list of hex color strings.\n"
        "e.g., {\"palette\": [\"#000000\", \"#FFFFFF\", ...]}")
    args = parser.parse_args()

    input_paths = args.input_path  # This is now a list
    output_dir = args.output
    width = args.width
    height = args.height
    scale_mode = args.scale

    # If no dimensions are specified, default to 160x120
    if width is None and height is None:
        width = 160
        height = 120

    # Expand wildcards for each input path and filter out files that can't be opened
    input_files = []
    for pattern in input_paths:
        input_files.extend(glob.glob(pattern))
    input_files = sorted(set(input_files))
    imgs_to_process = []
    img_base_names = []
    for file in input_files:
        try:
            img = convert_and_resize(file, width=width, height=height, scale_mode=scale_mode)
            if img is not None:
                imgs_to_process.append(img)
                img_base_names.append(os.path.splitext(os.path.basename(file))[0])
        except Exception:
            continue

    if not imgs_to_process:
        print("No valid input images found.")
        return

    # Palette selection
    palette_image = None
    if args.palette:
        print("Using custom palette provided via command line.")
        palette_image = create_palette_from_hex_colors(args.palette)
    elif args.palette_file:
        print(f"Using custom palette from file: {args.palette_file}")
        palette_image = create_palette_from_json_file(args.palette_file)
    else:
        print("Generating shared palette from all input images.")
        # Use all images to generate a shared palette
        # Stack all images vertically for palette extraction
        total_height = sum(img.height for img in imgs_to_process)
        max_width = max(img.width for img in imgs_to_process)
        combined = Image.new("RGBA", (max_width, total_height))
        y_offset = 0
        for img in imgs_to_process:
            combined.paste(img, (0, y_offset))
            y_offset += img.height
        palette_image = create_palette_from_image(combined)

    if palette_image:
        # Use assets.ts if multiple images, else <basename>.ts
        asset_path = os.path.join(output_dir, "assets.ts") if len(imgs_to_process) > 1 else os.path.join(output_dir, f"{img_base_names[0]}.ts")
        write_asset_files(imgs_to_process, img_base_names, asset_path, palette_image)
    else:
        print("Could not create or load a palette. Aborting.")

if __name__ == "__main__":
    main()
