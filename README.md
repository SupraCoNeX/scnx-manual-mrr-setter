# Manual MRR Chain Setter

This package enables setting of Multi-Rate-Retry (MRR) chain for transmission over a given update interval. A `rateman.RateMan` initializes and 
terminates the `start` function of this package. MRR setting is performed per station basis as abstracted in the `rateman` package design < add link >. 

Options for MRR are described within dictionary. Default options,
```
	multi_rate_retry: "random;1"
	update_interval_ns: 10_000_000
```

### List of options:


#### multi_rate_retry

Per MRR stage the rate and count options can be specific using this option.
	
**rate options per MRR stage**\
- `lowest`: Select the lowest theoretical throughput rate supported by the station. 
- `highest`: Select the highest theoretical throughput rate supported by the station. 
- `random`: Select a random rate out of the all rates supported by the station.
- `round_robin`: Select a consecutive rate out of the all rates supported by the station in a round robin manner.
- `rate-idx`: Select a known fixed rate index that belongs to the set of rates supported by the station. This index is required to be in the format defined by the ORCA < add link >

#### update_interval_ns

Update interval defines the time duration for which a give MRR setting use applied. This value is providing in nano seconds unit. 


### Examples

1. options = {"multi_rate_retry":"lowest;1"}; will set the MRR with the lowest supported rate with count 1. Update interval used is 10e6 ns. 
2. options = {"multi_rate_retry":"random,lowest;4,1"}; will set a randomly chosen rate in the first MRR stage and the lowest supported rate in the second, with counts 4 and 1 respectively. Update interval used is 10e6 ns. 
3. options = {"multi_rate_retry":"round_robin, highest;5,2"}; will set consecutive rates the first MRR stage from the set of supported rated in a round robin manner with count 5, while the second stage is set with the highest supported rate with count 2. Update interval used is 10e6 ns. 
4. options = {"update_interval_ns":50e6}; will set a randomly chosen rate in the first MRR stage with count 1. Update interval used is 50e6 ns. 


### Notes

- The number of stages added to `multi_rate_retry` must comply with the hardware capabilities. Currently, this is not ensured in the package.


    