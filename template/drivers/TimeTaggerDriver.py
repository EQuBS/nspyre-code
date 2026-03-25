import TimeTagger as tt
from TimeTagger import CHANNEL_UNUSED
from rpyc.utils.classic import obtain 

class tt20:
    
    def __init__(self):
        super().__init__()
        try:
            self.tagger = tt.createTimeTagger()
        except Exception as e:
            print(f"Error initializing Time Tagger: {e}")
    
    #sets the trigger level at which the Time Tagger will register a count
    # - channel: the channel to set the trigger level for (int)
    # - voltage: the voltage at which the Time Tagger will register a count
    def set_trigger_level(self, channel, voltage):
        self.tagger.setTriggerLevel(channel, voltage)

    def sync(self):
        self.tagger.sync()


    #initalizes counter measurement
    # - channels: list of channels to measure
    # - binwidth: width of each bin in ps
    # - n_values: number of bins to store
    # - measurement_duration: duration of the measurement in ps
    def start_counter(self, channels, binwidth, n_values, tagger=None): # Test took measurement duration
        """
        Initializes a counter measurement.

        Args:
            channels (list): List of channels to measure.
            binwidth (int): Width of each bin in ps.
            n_values (int): Number of bins to store.
            tagger (TimeTagger, optional): TimeTagger object or tag_proxy. Defaults to self.tagger.
        """
        if tagger is None:
            tagger = self.tagger
        #elif tagger == 'synchro':
            #tagger = self.synchro()
        try:
            self.counter = tt.Counter(tagger, channels=channels, binwidth=binwidth, n_values=n_values)
            print("Counter properly initialized")
        except Exception as e:
            if not isinstance(channels, list) or not all(isinstance(ch, int) for ch in channels):
                raise ValueError("Channels must be a list of integers.")
            if not isinstance(binwidth, int) or binwidth <= 0:
                raise ValueError("Binwidth must be a positive integer.")
            if not isinstance(n_values, int) or n_values <= 0:
                raise ValueError("N_values must be a positive integer.")
            print(f"Error initializing Counter: {e}")
            try:
                print(f"Tagger: {tagger}")
                print("Tagger properly initialized")
            except Exception as e:
                print(f"Error accessing tagger: {e}")

        #self.counter.startFor(measurement_duration)

    def clear_counter(self):
        self.counter.clear()

    def count_data_Norm(self):
        #start_counter must b e called first to create instance of Counter otherwise exception is raised.
        if not hasattr(self, 'counter'):
            raise AttributeError("Counter has not been initialized. Call start_counter first.")
        self.counter.waitUntilFinished()
        counts_norm = self.counter.getDataNormalized()
        return counts_norm
        
    def sFor_Counter(self, measurement_duration):
        self.counter.startFor(measurement_duration)

    def wait_until_counter(self):
        self.counter.waitUntilFinished(timeout=-1)

    #runs counter measurement for specified duration and returns data  
    #*This method must be run for Time Tagger to run the measurement for the specified duration*
    def get_counter_data(self):
        #start_counter must b e called first to create instance of Counter otherwise exception is raised.
        if not hasattr(self, 'counter'):
            raise AttributeError("Counter has not been initialized. Call start_counter first.")
        self.counter.waitUntilFinished()
        counts = self.counter.getData()
        return counts
    
    #returns the total counts since initalization
    def get_total_counter_counts(self):
        return self.counter.getDataTotalCounts()
    
    #initalizes countrate measurement
    # - channels: list of channels to measure
    # - measurement_duration: duration of the measurement in ps
    def start_countrate(self, channels, measurement_duration, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.countrate = tt.Countrate(tagger, channels=channels)
        self.countrate.startFor(measurement_duration)

    #runs countrate measurement for specified duration and returns data
    #*This method must be run for Time Tagger to run the measurement for the specified duration*
    def get_countrate_data(self):
        self.countrate.waitUntilFinished()
        counts = self.countrate.getData()
        return counts
    
    # Rolando 2/17/2026
    # Introducing the "TimeDifferences" method from "Time histograms" Measurements.
    def TimeDifferences(self, click_channel, start_channel, next_channel, sync_channel, bin_width, n_bins, n_histograms, tagger=None):
        """
        Docstring for TimeDifferences
        
        :param self: Description from Swabian's Time Tagger API
        :param click_channel: Channel on which stop clicks are received.
        :param start_channel: Channel that sets start times relative to 
                              which clicks on the click channel are measured.
        :param next_channel: Channel that increments the histogram index.
        :param sync_channel:  Channel that resets the histogram index to zero.
        :param bin_width: Binwidth in picoseconds.
        :param n_bins: Number of bins in each histogram.
        :param n_histograms: Number of histograms.
        :param tagger: Time tagger object instance.
        :return: Description
        :rtype: Any
        """
        if tagger is None:
            tagger = self.tagger
        self.Time_Differences = tt.TimeDifferences(tagger, click_channel, start_channel, next_channel, sync_channel, bin_width, n_bins, n_histograms)

    def TD_getData(self):
        """
        Docstring for TD_getData
        
        :param self: Description
        :return: A two-dimensional array of size n_histograms by n_bins 
                containing the histograms in row-major format.
        :rtype: Any
        """
        data = self.Time_Differences.getData()
        return obtain(data)
    
    def TD_getIndex(self):
        """
        Docstring for TD_getIndex
        
        :param self: Description
        :return: A vector of size n_bins containing the time bins in ps.
        :rtype: Any
        """
        index = self.Time_Differences.getIndex()
        return obtain(index)
    
    def TD_setMaxRollovers(self, max_rollovers):
        """
        Docstring for TD_setMaxRollovers
        
        :param self: Sets the number of rollovers at which the measurement stops. 
                     To integrate infinitely, set the value to 0, which is the default value.
        :param max_rollovers: Maximum number of rollovers (histogram index resets).
        :type max_rollovers: int
        :return: Description
        :rtype: None
        """
        self.Time_Differences.setMaxCounts(max_rollovers)

    def TD_getHistogramIndex(self):
        """
        Docstring for TD_getHistogramIndex
        
        :param self: The index of the currently processed histogram or 
                     the waiting state. Possible return values are:
                        -2: Waiting for an event on sync_channel (only if sync_channel is defined).
                        -1: Waiting for an event on next_channel (only if sync_channel is defined).
                        0 ...(n_histograms-1): Index of the currently processed histogram.
        :return: The current histogram index, which is incremented by one each time a click is received on the next_channel and reset to zero when a click is received on the sync_channel.
        :rtype: int
        """
        return self.Time_Differences.getHistogramIndex()
    
    def TD_getCounts(self):
        """
        Docstring for TD_getCounts
        
        :param self: Description
        :return: The number of rollovers (histogram index resets).
        :rtype: int
        """
        return self.Time_Differences.getCounts()
    
    def TD_ready(self):
        """
        Docstring for TD_ready
        
        :param self: Description
        :return: True when the required number of rollovers set by
                 'set_MaxRollovers' has been reached.
        :rtype: bool
        """
        return self.Time_Differences.ready()

    #initalizes correlation measurement
    # - channels: list of channels to measure
    # - binwidth: width of each bin in ps
    # - n_values: number of bins to store
    # - max_period: maximum period to measure in ps
    # - n_bins: number of bins to store
    # - measurement_duration: duration of the measurement in ps
    def start_correlation(self, channels, binwidth, n_values, max_period, n_bins, measurement_duration):
        self.correlation = tt.Correlation(self.tagger, channels=channels, binwidth=binwidth, n_values=n_values, max_period=max_period, n_bins=n_bins)
        self.correlation.startFor(measurement_duration)

    #runs correlation measurement for specified duration and returns data
    #*This method must be run for Time Tagger to run the measurement for the specified duration*
    def get_correlation_data(self):
        self.correlation.waitUntilFinished()
        counts = self.correlation.getData()
        return counts
    
    #determines if the specified measurement type is running
    # - measurement_type: object of the measurement class to check
    def is_measurement_running(self, measurement_type):
        return measurement_type.isRunning()
    

    def start_cbm(self, click_channel, begin_channel, end_channel=CHANNEL_UNUSED, n_values=1000, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.cbm = tt.CountBetweenMarkers(tagger, click_channel, begin_channel, end_channel, n_values)
        #self.cbm.startFor(s_For)

    def CBM_start(self):
        self.cbm.start()

    def CBM_sFor(self, duration):
        """startFor() function for CountBetweenMarkers event."""
        self.cbm.startFor(duration)
        self.cbm.waitUntilFinished(duration)

    def cbm_clear(self):
        self.cbm.clear()

    def cbm_get_BinWidths(self):
        BinWidths = self.cbm.getBinWidths()
        return obtain(BinWidths)

    #Counts between marked events, introd. 6/27/2025 by Rolando
    def count_BM(self):
        """
        Uses the TimeTagger CountBetweenMarkers measurement.
        
        Returns: The data from CountBetweenMarkers after measurement.
        """
        try:
            #self.cbm.waitUntilFinished()
            data = self.cbm.getData()
            return obtain(data)
        except AttributeError:
            raise AttributeError("Your TimeTagger module does not have CountBetweenMarkers. Please check your TimeTagger version.")

    """ def unused(self):
        return tt """
    #def get_cbm_Index(self):

    def cbm_ready(self):
        return self.cbm.ready()

    # Create "SynchronizedMeasurements" for tagger, and get its tagger proxy.
    def synchro(self):
        """
        Creates a SynchronizedMeasurement for the Time Tagger and returns its tagger proxy.
        """
        try:
            self.synchro_measurement = tt.SynchronizedMeasurements(self.tagger)
            tagger_proxy = self.synchro_measurement.getTagger()
            return tagger_proxy
        except Exception as e:
            print(f"Error creating SynchronizedMeasurement: {e}")
            return None
    
    # Synchro startFor method
    def sync_sFor(self, duration):
        # After syncho measurement is created, start it for a specified duration.
        self.synchro_measurement.startFor(duration)

    # Synchro waitUntilFinished method
    def sync_wait(self):
        # Wait until the synchronized measurement is finished.
        self.synchro_measurement.waitUntilFinished()

    #frees the Time Tagger object
    def free_time_tagger(self):
        tt.freeTimeTagger(self.tagger)

    def set_in_delay(self, channel, delay):
        """
        Sets the input delay for a specific channel.
        
        Args:
            channel (int): The channel number to set the input delay for.
            delay (float): The delay in nanoseconds.
        """
        self.tagger.setInputDelay(channel, delay)

    def measure_correlation(self, channel_1, channel_2, binwidth, n_bins=1000, tagger=None):
        """
        Args:
            tagger (TimeTagger): Time tagger object.
            channel_1 (int): Channel on which (stop) clicks are received.
            channel_2 (int): Channel on which reference clicks (start) are
                            received (when left empty or set to CHANNEL_UNUSED ->
                            an auto-correlation measurement is performed, which is
                            the same as setting 'channel_1 = channel_2').
                            (default: CHANNEL_UNUSED).
            binwidth (int): Bin width in ps (default: 1000).
            n_bins (int): The number of bins for the correlation measurement.
        """
        if tagger is None:
            tagger = self.tagger
        self.correlation = tt.Correlation(tagger, channel_1, channel_2, binwidth, n_bins)
        #self.correlation.start()

    def gated_ch(self, input_ch, gate_start, gate_stop, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.gated_channel = tt.GatedChannel(tagger, input_ch, gate_start, gate_stop)
        return self.gated_channel

    def get_channel(self):
        return self.gated_channel.getChannel()