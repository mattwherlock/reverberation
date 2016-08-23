#!/usr/bin/env python
'''
Takes a batch of linear reverberation patterns and returns the distance from the top of the image to the last unbroken line.  Prints result to screen and writes to a csv file called 'line_heights.csv'.  Input files are DICOM, and the output distances are in cm.
'''

import warnings
warnings.filterwarnings("ignore")

import dicom
import numpy as np
from PIL import Image
from skimage.feature import peak_local_max
from skimage.filters import gaussian
from skimage import io
import pandas as pd
from glob import glob

# read dicom, reshape, convert to greyscale, crop to actual image, return scaleF
def get_image(file):
    data = dicom.read_file(file)
    # values for crop from dicom header:
    x0 = data.SequenceOfUltrasoundRegions[0].RegionLocationMinX0
    x1 = data.SequenceOfUltrasoundRegions[0].RegionLocationMaxX1
    y0 = data.SequenceOfUltrasoundRegions[0].RegionLocationMinY0
    y1 = data.SequenceOfUltrasoundRegions[0].RegionLocationMaxY1
    # scale factor to convert pixel distances to cm
    scale_f = data.scale_f = data.SequenceOfUltrasoundRegions[0].PhysicalDeltaY
    px = data.pixel_array
    # reshape if pixel data is output as rgb,rgb,rgb,...
    if data.SamplesPerPixel == 3:
        new = px.reshape(data.Rows, data.Columns, data.SamplesPerPixel)
        # convert to greyscale
    new = np.ndarray.mean(new, axis=2).astype(np.uint8)
    # crop image
    new = new[y0:y1,(x0+56):(x1-54)]
    return new, scale_f

def last_line(infile):
    new, scale_f = get_image(infile)
    image_raw = new
    # use gaussian blur to remove some noise
    image = gaussian(image_raw, sigma=1.5)

    # find mean intensity vertically (mean per row) as a 1D array
    # this will be used to find the pixel height of each reverberation line
    means = np.mean(image, axis=1)

    # call peaks based on pixel intensity, filtered over background noise
    peaks = peak_local_max(means, threshold_rel=0.2)

    # select a 6 pixel high band for each line and find the average intensity
    hmeans = [np.mean(image[i-3:i+3]) for i in peaks]
    #print 'pixel heights of called peaks : '

    # select a 6 pixel high band for each line
    broad_lines = [image[i-3:i+3] for i in peaks]

    # get mean intensity at each horizontal point for each line
    # this compresses the band into a single pixel high representation
    compress = [np.mean(line, axis=0) for line in broad_lines]

    # find gaps in each line where intensity falls below a threshold
    # if there are more than 10 pixels of gap, call the line broken
    gapped_lines = []
    for i in range(len(compress)): # for each line...
        gap = []
        [gap.append(point) for point in compress[i] if point <= 0.2*compress[i].mean()]
        # if there are enough gaps in a line, add the previous line
        if len(gap) >= 10: # might need to tune this threshold
            gapped_lines.append(i-1)
            break
        # if there are not enough gaps to call a break, add the last line
    if len(gapped_lines) == 0:
        gapped_lines.append(i)

    # give pixel distance to last unbroken line        
    height = str(np.squeeze(peaks[gapped_lines]*scale_f))
    # get the input filename as a string
    filename = str(item,)
    # combine file name and height as pairs
    data = zip([filename], [height])
    data = [filename, height]
    return data

df = pd.DataFrame(columns=['file','depth (cm)'])

for item in glob('*'):
    data = last_line(item)
    df.loc[len(df)] = data
    
print(df) # to screen
df.to_csv('line_heights.csv', index=False)