import nibabel as nib
example_filename = "./data/original/HGG/Brats17_2013_2_1/Brats17_2013_2_1_seg.nii.gz"
img = nib.load(example_filename)
data = img.get_data()
print(data)