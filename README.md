<img width="964" alt="carboNmp" src="https://github.com/stpf99/imageUpscale-gui/blob/5ed56173708c7d8b12209cc1dbdbdfa04760b47b/screnhoot.png">


Image Upscaler with Edge-Preserving Smoothing
This is a Python-based graphical application for upscaling images while preserving edge details and smoothing uniform color areas to reduce tonal artifacts. Built using PyGObject (GTK4), PIL, NumPy, and SciPy, it provides an interactive GUI for loading, upscaling, and exporting images.
Features

Load and export images (JPEG, PNG).
Adjustable upscale multiplier (1x to 16x).
Edge detection using Sobel filter with customizable detail level.
Smoothing of uniform color areas with Gaussian blur, controlled by a smoothing threshold (default 85%).
Real-time preview of original and upscaled images with adjustable view percentages.
Full-resolution export of upscaled images.
