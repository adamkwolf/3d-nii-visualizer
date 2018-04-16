# 3D Nifti Visualizer
<img src="https://github.com/adamkwolf/3d-nii-visualizer/blob/master/images/visualization.png" style="width: 100px;"/>

### Setup
1. Install `virtualenv` and create a new environemnt <env-name>
2. Activate the environemnt `source <env-name>/bin/activate`
3. Install the dependencies (PyQt5, vtk, and sip) `pip install -r requirements.txt`
4. Use `./sample_data` or add your datasets in the root directory and modify `BRAIN_FILE` and `TUMOR_FILE` path in `brain_tumor_3d.py`
5. Start the program `python brain_tumor_3d.py`
