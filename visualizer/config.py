import os

# default brain settings
APPLICATION_TITLE = "Theia – NIfTI (nii.gz) 3D Visualizer"
BRAIN_THRESHOLD = 20
BRAIN_SMOOTHNESS = 500
BRAIN_OPACITY = 0.2
BRAIN_COLORS = [(1.0, 0.9, 0.9)]  # RGB percentages

# default tumor settings
TUMOR_SMOOTHNESS = 500
TUMOR_COLORS = [(1, 0, 0), (0, 1, 0), (0.5, 0.5, 0), (0, 0, 1)]  # RGB percentages
TUMOR_OPACITY = 1.0

# files to load into view
# os.chdir("/Users/adamwolf/Desktop/brain-tumor-3d")
# BRAIN_FILE = "./data/original/HGG/Brats17_2013_12_1/Brats17_2013_12_1_t1ce.nii.gz"
# TUMOR_FILE = "./data/original/HGG/Brats17_2013_12_1/Brats17_2013_12_1_seg.nii.gz"
