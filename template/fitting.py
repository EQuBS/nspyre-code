import numpy as np
from scipy.optimize import curve_fit

######################################

#####################################
##   Defining fitting functions   ##
#####################################


def single_exponential_decay(t, amp, decay_rate, offset):
    """single exponential decay fitting function

    Args:
        t (float): time
        amp (float): amplitude of exponential decay
        decay_rate (float): T_1, T_2, or other decay rates
        offset (float): offset of fitting data

    Returns:
        float: value with exponential dependence
    """
    return offset - (amp * np.exp(-1 * t/decay_rate))


def double_exponential_decay(t, amp_1, decay_rate_1, amp_2, decay_rate_2, offset):
    """double exponenetial decay fitting function

    Args:
        t (float): time
        amp_1 (float): amplitude of exponential decay
        decay_rate_1 (float): T_1, T_2, or other decay rates
        amp_2 (float): amplitude of exponential decay
        decay_rate_2 (float): T_1, T_2, or other decay rates
        offset (float): offset of fitting data

    Returns:
        float: value with exponential dependence
    """
    return offset - (amp_1 * np.exp(-1 * t/decay_rate_1)+amp_2*np.exp(-1*t/decay_rate_2))


def triple_exponential_decay(t, amp_1, decay_rate_1, amp_2, decay_rate_2, amp_3,
                             decay_rate_3, offset):
    """triple exponenetial decay fitting function

    Args:
        t (float): time
        amp_1 (float): amplitude of exponential decay
        decay_rate_1 (float): T_1, T_2, or other decay rates
        amp_2 (float): amplitude of exponential decay
        decay_rate_2 (float): T_1, T_2, or other decay rates
        amp_3 (float): amplitude of exponential decay
        decay_rate_3 (float): T_1, T_2, or other decay rates
        offset (float): offset of fitting data

    Returns:
        float: value with exponentia dependence
    """
    return (offset - (amp_1 * np.exp(-1 * t/decay_rate_1)+amp_2*np.exp(-1*t/decay_rate_2)
                      + amp_3*np.exp(-1*t/decay_rate_3))
            )
    
def rabi_fit(t, amp, freq, decay_rate, phi, offset):
    return offset + (amp*np.cos(freq*t+phi)*np.exp(-1*t/decay_rate))

def single_lorentz_fit(t, amp, freq, hwhm, offset):
    return offset + amp*((hwhm**2)/((t-freq)**2+hwhm**2))

def double_lorentz_fit(t, amp_1, freq_1, hwhm_1, amp_2, freq_2, hwhm_2, offset):
    return offset + amp_1*((hwhm_1**2)/((t-freq_1)**2+hwhm_1**2)) + amp_2*((hwhm_2**2)/((t-freq_2)**2+hwhm_2**2))


#####################################


def data_reading(data_array, columns=2, units='micro'):
    """ function which takes in data and returns scaled time and time dependant
        arrays

    Args:
        data_array (np.ndarray or str): array with data arrays within it or 
                                        name of csv file/path.
        columns (int, optional): index of last column of interest. Defaults to 2.
        units (str or float, optional): scaling factor for time data. Can also
                                        put custom scaling factor. Defaults to
                                        'micro'.

    Raises:
        TypeError: If data type is not allowed.

    Returns:
        np.ndarray, np.ndarray: time array and dependant array.
    """

    if type(units) == str:
        scale = (10**-6)
    elif type(units) == float:
        scale = units
    elif type(units) == int:
        scale = units
    else:
        raise TypeError("units not set properly")
    t_data = data_array[0]*scale
    y_data = data_array[1]
    return t_data, y_data


def exponential_decay_fitting(data_array, fit, save=True):
    # units rescaling for microsecond x-axis
    rescaling = (10**3)
    prefix = 'μ'
    

    # data extraction
    t_data, y_data = data_reading(data_array, units = 1/rescaling)

    # bound determination
    if y_data[-1] > y_data[1]:
        amp_bound_max = np.inf
        amp_bound_min = 0.00001
    elif y_data[-1] < y_data[1]:
        amp_bound_min = -np.inf
        amp_bound_max = -0.00001
    else:
        amp_bound_min = -np.inf
        amp_bound_max = np.inf

    # Perform curve fitting
    if fit == 'Single':
        bounds = ([amp_bound_min, .00001, y_data[-1]-500],
                  [amp_bound_max, rescaling*10**3, y_data[-1]+500])
        parameters, covariance = curve_fit(single_exponential_decay, t_data,
                                           y_data, bounds=bounds)
        errors = np.sqrt(np.diag(covariance))
        amp, T_1, offset = parameters
        T_1 = T_1 * rescaling
        print("""T1 = {1}{6}s, Err = {4} \namp = {0}, Err = {3}, offset = {2}, 
              Err = {5}""".format(amp, T_1, offset, errors[0], errors[1], errors[2], prefix))
        
        if save == True:
            t_fit = np.linspace(min(t_data), max(t_data), 1000)*rescaling
            return [t_fit,single_exponential_decay(t_fit, amp, T_1, offset)]

    elif fit == 'Double':
        bounds = ([amp_bound_min, .00001, amp_bound_min, 0.00001, y_data[-1]-500],
                  [amp_bound_max, rescaling, amp_bound_max, rescaling,
                   y_data[-1]+500])
        parameters, covariance = curve_fit(double_exponential_decay, t_data,
                                           y_data, bounds=bounds)
        errors = np.sqrt(np.diag(covariance))
        amp_a, T_1_a, amp_b, T_1_b, offset = parameters
        # Redifining T1s so the largest one is T1, second T1'
        T_1_list = [T_1_a, T_1_b]
        T_1 = max(T_1_list)*rescaling
        amp_1 = [amp_a, amp_b][T_1_list.index(T_1/rescaling)]
        T_1_p = min([T_1_a, T_1_b])*rescaling
        amp_2 = [amp_a, amp_b][T_1_list.index(T_1_p/rescaling)]
        T_1_error = float(errors[np.where(parameters == T_1/rescaling)])

        print("""T1 = {1}{6}s, Err = {5}, T1\' = {3}{6}s\namp = {0}, amp\' = {2}, 
              offset = {4}""".format(amp_1, T_1, amp_2, T_1_p, offset, T_1_error, prefix))
            
        if save == True:
            t_fit = np.linspace(t_data[0], t_data[-1], 1000)*rescaling
            return [t_fit,double_exponential_decay(t_fit, amp_a, T_1, amp_b, T_1_p, offset)]
    elif fit == 'Triple':
        bounds = ([amp_bound_min, .00001, amp_bound_min, 0.00001, amp_bound_min,
                   0.00001, y_data[-1]-500], [amp_bound_max, rescaling*10**(-3),
                                              amp_bound_max, rescaling *
                                              10**(-3),
                                              amp_bound_max, rescaling *
                                              10**(-3),
                                              y_data[-1]+500])
        parameters, covariance = curve_fit(triple_exponential_decay, t_data,
                                           y_data, bounds=bounds)
        errors = np.sqrt(np.diag(covariance))
        amp_a, T_1_a, amp_b, T_1_b, amp_c, T_1_c, offset = parameters
        # Redifining T1s so the largest one is T1, second T1', and so on
        T_1_list = [T_1_a, T_1_b, T_1_c]
        T_1 = max([T_1_a, T_1_b, T_1_c])*rescaling
        amp_1 = [amp_a, amp_b, amp_c][T_1_list.index(T_1/rescaling)]
        T_1_p = np.median([T_1_a, T_1_b, T_1_c])*rescaling
        amp_2 = [amp_a, amp_b, amp_c][T_1_list.index(T_1_p/rescaling)]
        T_1_pp = min([T_1_a, T_1_b, T_1_c])*rescaling
        amp_3 = [amp_a, amp_b, amp_c][T_1_list.index(T_1_pp/rescaling)]
        T_1_error = float(errors[np.where(parameters == T_1/rescaling)])

        print("""T1 = {1}{8}s, Err = {7}, T1\' = {3}{8}s, T1\'\' = {5}{8}s
              \namp = {0}, amp\' = {2}, amp\' \' = {4}, offset = {6}""".format(
            amp_1, T_1, amp_2, T_1_p, amp_3, T_1_pp, offset, T_1_error, prefix))


        if save == True:
            t_fit = np.linspace(min(t_data), max(t_data), 1000)*rescaling
            return [t_fit,triple_exponential_decay(t_fit, amp_1, T_1, amp_2,
                                                   T_1_p, amp_3, T_1_pp, offset)]
    else:
        raise NameError("Not a valid fit type")

def rabi_oscillation_fitting(data_array, decay_time_guess = 1, pi_time_guess = 20, save = True):
    # data extraction
    t_data, y_data = data_reading(data_array, units = 1)
    bounds = ([np.max(y_data), 0, 0, 0, -1*np.inf],
              [np.inf, np.inf, np.inf, 2*np.pi, np.inf])
    
    amp_guess = np.max(y_data)*10
    
    max_index = np.argmax(y_data)
    min_index = np.argmin(y_data)
    
    pi_time_guess = np.abs(t_data[max_index]-t_data[min_index])
    
    freq_guess = np.pi / pi_time_guess
    offset_guess = np.mean(y_data)
    
    parameters, covariance = curve_fit(rabi_fit, t_data, y_data, bounds = bounds, p0= [amp_guess, freq_guess, decay_time_guess, 0, offset_guess])
    amp, freq, decay_rate, phi, offset = parameters
    
    errors = np.sqrt(np.diag(covariance))
    
    print("""Pi pulse time: {0}ns\n Freq Error: {1}""".format(np.pi/freq,
                                                              errors[1]))

    if save == True:
        t_fit = np.linspace(t_data[0], t_data[-1], 1000)
        return [t_fit, rabi_fit(t_fit, amp, freq, decay_rate, phi, offset)]
    
def odmr_fitting(data_array, fit, save = True):
    t_data, y_data = data_reading(data_array, units = 1)
    if fit == 'Single':
        p0 = [0, np.mean(t_data), 0.1, y_data[0]]
        parameters, covariance = curve_fit(single_lorentz_fit, t_data, y_data, p0=p0)
        amp, freq, hwhm, offset = parameters
        errors = np.sqrt(np.diag(covariance))
        print("Freq: {0}\nHWHM: {1}".format(freq,hwhm))
        if save == True:
            t_fit = np.linspace(t_data[0], t_data[-1], 1000)
            return [t_fit, single_lorentz_fit(t_fit, amp, freq, hwhm, offset)]
    elif fit == 'Double':
        parameters, covariance = curve_fit(double_lorentz_fit, t_data, y_data)
        amp_1, freq_1, hwhm_1, amp_2, freq_2, hwhm_2, offset = parameters
        errors = np.sqrt(np.diag(covariance))
        if save == True:
            t_fit = np.linspace(t_data[0], t_data[-1], 1000)
            return [t_fit, double_lorentz_fit(t_fit, amp_1, freq_1, hwhm_1,
                                              amp_2, freq_2, hwhm_2, offset)]
    else:
        return ValueError("Not a valid fit type")
    