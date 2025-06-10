import TimeTagger as tt 

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

    #initalizes counter measurement
    # - channels: list of channels to measure
    # - binwidth: width of each bin in ps
    # - n_values: number of bins to store
    # - measurement_duration: duration of the measurement in ps
    def start_counter(self, channels, binwidth, n_values, measurement_duration):
        
        try:
            self.counter = tt.Counter(self.tagger, channels=channels, binwidth=binwidth, n_values=n_values)
        except Exception as e:
            if not isinstance(channels, list) or not all(isinstance(ch, int) for ch in channels):
                raise ValueError("Channels must be a list of integers.")
            if not isinstance(binwidth, int) or binwidth <= 0:
                raise ValueError("Binwidth must be a positive integer.")
            if not isinstance(n_values, int) or n_values <= 0:
                raise ValueError("N_values must be a positive integer.")
            print(f"Error initializing Counter: {e}")
            try:
                print(f"Tagger: {self.tagger}")
                print("Tagger properly initialized")
            except Exception as e:
                print(f"Error accessing tagger: {e}")

        self.counter.startFor(measurement_duration)
        
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
    def start_countrate(self, channels, measurement_duration):
        self.countrate = tt.Countrate(self.tagger, channels=channels)
        self.countrate.startFor(measurement_duration)

    #runs countrate measurement for specified duration and returns data
    #*This method must be run for Time Tagger to run the measurement for the specified duration*
    def get_countrate_data(self):
        self.countrate.waitUntilFinished()
        counts = self.countrate.getData()
        return counts
    
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
    
    #frees the Time Tagger object
    def free_time_tagger(self):
        tt.freeTimeTagger(self.tagger)