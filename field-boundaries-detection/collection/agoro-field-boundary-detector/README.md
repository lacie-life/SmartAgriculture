# Agoro Field Boundary Detector

Detect field boundaries using satellite imagery.

[Ref](https://radix.ai/blog/2021/6/from-a-to-z-on-field-boundary-detection-a-computer-vision-use-case/)

## Installation
To install this package in your environment, run:

```bash
pip install git+https://github.com/radix-ai/agoro-field-boundary-detector.git
```


## Usage
To use the field boundary detector model together with the Google Earth Engine (model's input data), use the `FieldBoundaryDetectorInterface` class.
This class provides an interface on top of the field boundary detector model by adding these next steps:
1. Translate a `(latitude,longitude)` coordinate into an image extracted from GEE 
2. Predict the field-boundary of the field overlapping with the provided coordinate (image's center pixel)
3. Translate the extracted polygon from pixel-coordinates to geographical `(lat,lng)` coordinates

This interface also allows you to easily make predictions with a higher certainty, by changing the default `0.5` certainty in the class' call.

```python
from agoro_field_boundary_detector import FieldBoundaryDetectorInterface

# Load in the model, will start GEE session
model = FieldBoundaryDetectorInterface(model_path=...)

# Make the prediction
pred = model(lat=39.6679328199836, lng=-95.4287818841267)
# Result
# [
#     (39.683761135289785, -95.4369042849299),
#     (39.6837431689841, -95.43695096539429), 
#     ...
#     (39.683761135289785, -95.4368809446977), 
#     (39.683761135289785, -95.4369042849299)
# ]

# Make the prediction with a higher certainty threshold
pred_certain = model(lat=39.6679328199836, lng=-95.4287818841267, thr=0.9)
# Result
# [
#     (39.68350960701023, -95.43681092400112), 
#     (39.683491640704545, -95.43685760446552), 
#     ...
#     (39.683491640704545, -95.43678758376893), 
#     (39.68350960701023, -95.43681092400112)
# ]

```

If you want to use the field boundary detector model in separation (i.e. without GEE), use the `FieldBoundaryDetector` class.
This class will predict pixel-level polygon boundaries when fed an image. It also enables you to fetch all other polygons found in this image as well. 

```python
import numpy as np
from agoro_field_boundary_detector import FieldBoundaryDetector

# Load in the model, will start GEE session
model = FieldBoundaryDetector(model_path=...)

# Make the prediction
im = np.asarray(...)
single_polygon = model(im)
# Result
# [
#     (34, 67),
#     (41, 67), 
#     ...
#     (26, 87), 
#     (34, 67),
# ]

# Get all polygons found in the image
im = np.asarray(...)
all_polygons = model.get_all_polygons(im)
# Result
# [[
#     (34, 67),
#     ...
#     (34, 67),
# ],
# ...
# [
#     (41, 67), 
#     ...
#     (41, 67), 
# ]]
```


## Development

### Setup Environment
In order to initialise your environment properly, run the following command in the root of this project:
```shell
tasks/init.sh
```
This creates a conda environment with all the necessary dependencies (run and development dependencies). 

If you only need the run dependencies, use:
```shell
pip install .
```

### Exporting images
A script on how to export Google Earth Engine images - more specifically those from the National Agriculture Imagery Program dataset - can be found under `i_export_field_data.py`.
This script utilises the functions and classes found in the `google_earth_engine` subfolder.
Note that you need to sign-up for Google Earth Engine first ([here](https://earthengine.google.com/signup/)), before you can export images from it.

### Data Annotation
A script on how to augment the extracted images can be found under `ii_augment_data.py`.
This script utilises the functions and classes found in the `augmentation` subfolder.

### Model Training
A script on how to train, evaluate, and infer the field boundary detector model can be found under `iii_train_mask_rcnn.py`.
This script utilises the function and classes found in the `field_detection` subfolder.

### Model inference
The `main.py` file combines both the field boundary detector model, and the Google Earth Engine code in a single interface. 
This script allows you to easily query the model. The only things you need are a pre-trained model and the `(latitude,longitude)` coordinate of the field for which you want to extract the boundaries for.
