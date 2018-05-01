# A NIfTI (nii.gz) 3D Visualizer using VTK and Qt5

<img src="https://github.com/adamkwolf/3d-nii-visualizer/blob/master/images/visualization.png" style="width: 100px;"/>

### Setup

1.  Install `virtualenv` and create a new environment <env-name>
2.  Activate the environemnt `source <env-name>/bin/activate`
3.  Install the dependencies (PyQt5, vtk, and sip) `pip install -r requirements.txt`
4.  Use `./sample_data` or add your datasets in the root directory and modify `BRAIN_FILE` and `TUMOR_FILE` path in `brain_tumor_3d.py`
5.  Start the program `python brain_tumor_3d.py`

### PyInstaller
* Mac: `sudo pyinstaller brain_tumor_3d.py  --onefile --windowed --osx-bundle-identifier=Theia --icon=icon.icns --name="Theia" -y --clean`
* Windows: `coming soon`
### Test

* `python -m pytest`

### Acknowledgements

[1] S.Bakas et al, "Advancing The Cancer Genome Atlas glioma MRI collections with expert segmentation labels and radiomic features", Nature Scientific Data, 4:170117 (2017) DOI: 10.1038/sdata.2017.117

[2] B.Menze et al, "The Multimodal Brain Tumor Image Segmentation Benchmark (BRATS)", IEEE Transactions on Medical Imaging 34(10), 1993-2024 (2015) DOI: 10.1109/TMI.2014.2377694
