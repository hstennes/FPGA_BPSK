import numpy as np
import time
import matplotlib.pyplot as plt

def iq_plot(time_sec,re_signal,im_signal,n_samples,):
    plt.figure()
    plt.subplot(1, 1, 1)
    plt.xlabel('Time (usec)')
    plt.grid()
    plt.plot(time_sec[:n_samples],re_signal[:n_samples],'y-o',label='I signal')
    plt.plot(time_sec[:n_samples],im_signal[:n_samples],'g-o',label='Q signal')
    plt.legend()
    plt.show()

import numpy as np

def generate_bit_samples(bits, samples_per_bit=64, high=1100, low=-1100, std=20, dtype=np.int16):
    # Convert booleans to 0/1 integers
    bit_values = np.array(bits, dtype=int)

    samples = []
    for bit in bit_values:
        mean = high if bit == 1 else low
        # Generate normally-distributed random samples
        s = np.random.normal(loc=mean, scale=std, size=samples_per_bit)
        samples.append(s)

    return np.asarray(np.concatenate(samples), dtype=dtype)

def max_consecutive_gt_1000(arr: np.ndarray) -> int:
    # Boolean array: True where value > 1000
    mask = arr > 1000
    
    # Find boundaries where the mask changes
    # We prepend and append False to catch runs at the edges
    padded = np.r_[False, mask, False]
    diffs = np.diff(padded.astype(int))
    
    # Run starts where diff = 1, ends where diff = -1
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    
    # Compute lengths of each run and return the maximum (or 0 if none)
    if len(starts) == 0:
        return 0
    
    return np.max(ends - starts)


real = np.load("real_data_32.npy")
imag = np.load("imag_data_32.npy")

t = np.arange(0,len(real))

iq_plot(t,real,imag,10000)

# fake = generate_bit_samples([1,0,1,1,0,0,1,0,1,1,1,0,0,0,1,0], std=50)

# iq_plot(t,fake,np.zeros_like(fake),1024)
