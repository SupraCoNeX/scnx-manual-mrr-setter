# Rate Control via Manual MRR Chain Setting

Allows rate setting using the lowest supported rate or a random choice from 
the set of supported rates. 

Options
 - multi_rate_retry
     - e.g. 1) multi_rate_retry = "lowest;1" will set the lowest supported rate with 
     count 1.
     - e.g. 2) multi_rate_retry = "random;lowest;4,1" will set a randomly chosen
     rate as the first rate and the lowest supported rate as second rate in 
     the MRR chain with counts 4 and 1 respectively.
     


    