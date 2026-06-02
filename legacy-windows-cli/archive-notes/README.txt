FH6 Road Finder - Consolidated Version
=====================================

This version combines the useful parts of the Claude and Codex builds.

What this version keeps
-----------------------

- Portable Windows BAT launcher.
- Local .venv dependency setup.
- PNG-first workflow based on RGB(128,128,128), from HSV(0,0,50.2).
- JPEG/JPG/BMP/TIFF support with warnings.
- Tolerance presets 0, 1, 2, 5, and 8.
- Tiny red hits stay visible in the generated images.
- Black highlight PNGs, overlay PNGs, transparent mask PNGs, and report.html.
- No CSV files. The coordinates were not useful for this workflow.
- Separate map stitcher tool for combining overlapping screenshots.


Best first choices
------------------

For real PNG screenshots:

  Choose option 6.

That runs tolerance 0, 1, and 2 first, which avoids wasting time on too many
false positives.

For JPEG screenshots:

  Choose option 4.

That runs tolerance 5, which compensates for JPEG color shifts better than 0,
1, or 2.


How to run
----------

1. Put map screenshots into the input folder.
2. Double-click Run_FH6_Road_Finder.bat.
3. Pick the tolerance option by pressing one number key.
4. Open output\report.html.
5. Check the *_overlay.png files first.

You can ignore coordinates completely. The main thing is the red highlight on
the images.


Map stitcher
------------

Claude left a design for an optional stitcher. It is now included:

  Run_FH6_Map_Stitcher.bat

Use it when you have multiple overlapping map screenshots at the same zoom level
and want to combine them into one larger image first.

The stitcher reads from:

  input

It writes:

  output\stitched_map.png
  output\coverage_map.png

The BAT asks whether to crop the in-game UI. The default is Y, using:

  crop top 60 pixels
  crop bottom 55 pixels

The BAT uses manual translation matching so every screenshot is placed. If one
cannot be aligned confidently, it is placed to the side with a warning instead
of being silently dropped.

If stitching looks wrong, try PNG screenshots with more overlap, or rerun and
choose N for cropping.

After stitching, open coverage_map.png. Orange checkerboard areas are likely
gaps. Take more screenshots of those areas, add them to input, and run the
stitcher again.


Important note about JPEG
-------------------------

PNG is still best. JPEG compression changes exact road grey pixels.

This consolidated version can process JPEG, but use tolerance 5 or 8 if the
strict PNG-style modes do not find anything useful.


Manual command example
----------------------

  .venv\Scripts\python.exe tools\fh6_road_finder.py ^
    --input input ^
    --output output ^
    --target-rgb 128,128,128 ^
    --tolerances 5 ^
    --highlight-color 255,0,0 ^
    --overlay-alpha 0.85 ^
    --distance-mode channel


Detection logic
---------------

Default distance mode:

  channel

A pixel matches when:

  abs(R - target_R) <= tolerance
  abs(G - target_G) <= tolerance
  abs(B - target_B) <= tolerance

The default target is:

  RGB(128,128,128)

Even very small matching blobs are shown in the overlay, black highlight, and
transparent mask images.
