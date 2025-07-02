# MakeCode Arcade Asset Tools

## Create asset from image files

```
~ $ ./img2asset.py -h
usage: img2asset.py [-h] [-o OUTPUT] [-w WIDTH] [-H HEIGHT] [-p PALETTE | -f PALETTE_FILE] input_path [input_path ...]

Create MakeCode Arcade compatible asset(s) from image(s) and save PNG file(s) for reference.

positional arguments:
  input_path            The path(s) to the input image file(s), supports wildcards (e.g. '*.bmp').

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   Directory where output files will be saved.
                        Defaults to current directory.
  -w, --width WIDTH     The desired width of the output image(s) in pixels.
                        Defaults to 160 if --height is also omitted.
                        If only --width is provided, height is scaled to maintain aspect ratio.
  -H, --height HEIGHT   The desired height of the output image(s) in pixels.
                        Defaults to 120 if --width is also omitted.
                        If only --height is provided, width is scaled to maintain aspect ratio.
  -p, --palette PALETTE
                        A comma-separated list of hex colors (e.g., '#FF0000,#00FF00') to use as a custom palette.
                        The first color is used for transparency. Up to 16 colors are supported.
                        If provided, this palette is used instead of generating one from the image(s).
  -f, --palette-file PALETTE_FILE
                        Path to a JSON file containing a custom palette.
                        The JSON should have a 'palette' key with a list of hex color strings.
                        e.g., {"palette": ["#000000", "#FFFFFF", ...]}
```
