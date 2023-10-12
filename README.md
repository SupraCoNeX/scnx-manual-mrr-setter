# Manual Multi-Rate Retry Chain Setter

This package implements a simple user space transmission rate control algorithm to be used with [rateman](https://github.com/SupraCoNeX/scnx-rateman). It allows users to specify which rate to use at which stage of the multi-rate retry chain (MRR) for a given interval and in an abstract manner.


## Configuration Parameters

These are the configuration parameters (values shown are defaults) and how to pass them to `rateman.Station::start_rate_control()`
```
cfg = {
	multi_rate_retry: "random;1"
	update_interval_ns: 10_000_000
}

await sta.start_rate_control("manual_mrr_setter", cfg)
```


### `multi_rate_retry`

There are five options for each of the MRR stage:

- `slowest`: Select the slowest rate supported by the station. 
- `fastest`: Select the fastest rate supported by the station. 
- `random`: Select a random rate out of the all rates supported by the station.
- `round_robin`: Cycle through all the rates supported by the station.
- `rate-idx`: Select a specific rate identified by its index (in hexadecimal).

### `update_interval_ns`

Update interval defines the time between updates to the MRR in nanoseconds. 


## Examples

1. options = {"multi_rate_retry":"slowest;1"}; will set the MRR with the lowest supported rate with count 1. Update interval used is 10e6 ns. 
2. options = {"multi_rate_retry":"random,slowest;4,1"}; will set a randomly chosen rate in the first MRR stage and the slowest supported rate in the second, with counts 4 and 1 respectively. Update interval used is 10e6 ns. 
3. options = {"multi_rate_retry":"round_robin,fastest;5,2"}; will set consecutive rates the first MRR stage from the set of supported rated in a round robin manner with count 5, while the second stage is set with the fastest supported rate with count 2. Update interval used is 10e6 ns. 
4. options = {"update_interval_ns":50e6}; will set a randomly chosen rate in the first MRR stage with count 1. Update interval used is 50e6 ns. 


## Notes

- The number of stages added to `multi_rate_retry` must comply with the hardware capabilities. Currently, this is not ensured in the package.


    
