import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

points_of_interest = [(0,0),(0,4),(4,4)]
step_quantity = 4
"""
if type(step_quantity) is not int:

    raise ValueError("step_quantity must be an integer")"""

pts = np.asarray(points_of_interest)

x = pts[:,0] #defines x points of interest
y = pts[:,1] #defines y points of interest

x_pairs = sliding_window_view(x, 2)  #this function creates pairs of points for linspace, 
y_pairs = sliding_window_view(y, 2)

x_array = [np.linspace(x0, x1, step_quantity) for x0, x1 in x_pairs] #linspace between pairs creates the numpy array of where to move for each step
y_array = [np.linspace(y0, y1, step_quantity) for y0, y1 in y_pairs]

print("X pairs:\n", x_array)
print("Y pairs:\n", y_array)




#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#wrap this into a function
def generate_xy_array(points_of_interest, step_quantity):

    pts = np.asarray(points_of_interest)

    x = pts[:,0] #defines x points of interest
    y = pts[:,1] #defines y points of interest

    x_pairs = sliding_window_view(x, 2)  #this function creates pairs of points for linspace, 
    y_pairs = sliding_window_view(y, 2)

    x_array = [np.linspace(x0, x1, step_quantity) for x0, x1 in x_pairs] #linspace between pairs creates the numpy array of where to move for each step
    y_array = [np.linspace(y0, y1, step_quantity) for y0, y1 in y_pairs]

    return x_array, y_array

#example usage

points_of_interest = [(0,0),(0,1),(1,1),(1,0),(2,0),(2,0.5)]
step_quantity = 10

x_array, y_array = generate_xy_array(points_of_interest, step_quantity)

print("X array:\n", x_array)
print("Y array:\n", y_array)

#plot

import matplotlib.pyplot as plt

for x_line, y_line in zip(x_array, y_array):
    plt.plot(x_line, y_line, marker='o')
plt.title("XY Movement Array")
plt.xlabel("X Position")
plt.ylabel("Y Position")
plt.grid()
plt.show()


#what if we look at a function that generates waveforms for scanning?

#This is a lot easier

x = np.linspace(0, 4, step_quantity)
y = np.sin(x * (np.pi / 2))   #example function for y

plt.figure()

print("X waveform:\n", x)
print("Y waveform:\n", y)
#plot
plt.plot(x, y, marker='o')
plt.title("XY Movement Waveform")
plt.xlabel("X Position")
plt.ylabel("Y Position")
plt.grid()
plt.show()