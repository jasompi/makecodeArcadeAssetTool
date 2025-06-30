# MakeCode Arcade Asset Tools

## Create asset from image files

```
./img2asset.py -h
usage: img2asset.py [-h] [-w WIDTH] [--height HEIGHT] [--palette PALETTE | --palette-file PALETTE_FILE] input_path [output_path]

Create MakeCode Arcade compatible asset from image and save a PNG file for reference.

positional arguments:
  input_path            The path to the input JPG image file.
  output_path           The path for the output PNG file.
                        If omitted, the input filename with a .png extension will be used.

options:
  -h, --help            show this help message and exit
  -w, --width WIDTH     The desired width of the output image in pixels.
                        Defaults to 160 if --height is also omitted.
                        If only --width is provided, height is scaled to maintain aspect ratio.
  --height HEIGHT       The desired height of the output image in pixels.
                        Defaults to 120 if --width is also omitted.
                        If only --height is provided, width is scaled to maintain aspect ratio.
  --palette PALETTE     A comma-separated list of hex colors (e.g., '#FF0000,#00FF00') to use as a custom palette.
                        The first color is used for transparency. Up to 16 colors are supported.
                        If provided, this palette is used instead of generating one from the image.
  --palette-file PALETTE_FILE
                        Path to a JSON file containing a custom palette.
                        The JSON should have a 'palette' key with a list of hex color strings.
                        e.g., {"palette": ["#000000", "#FFFFFF", ...]}
```
