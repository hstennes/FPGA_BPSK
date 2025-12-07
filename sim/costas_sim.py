import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

rng = np.random.default_rng(0)

def generate_bpsk_with_freq_offset(
    num_samples: int,
    samples_per_symbol: int = 1,
    freq_offset_hz: float = 50.0,
    fs: float = 1_000_000.0,
    noise_std: float = 0.0,
    seed: int | None = None,
):
    rng = np.random.default_rng(0)

    num_symbols = int(np.ceil(num_samples / samples_per_symbol))
    symbols = rng.choice([-1.0, +1.0], size=num_symbols)

    bpsk_sequence = np.repeat(symbols, samples_per_symbol)
    bpsk_sequence = bpsk_sequence[:num_samples]

    n = np.arange(num_samples) 
    phase = 2 * np.pi * freq_offset_hz * n / fs
    freq_rot = np.exp(1j * phase)

    iq = bpsk_sequence.astype(np.complex64) * freq_rot

    if noise_std > 0:
        noise = (rng.standard_normal(num_samples) +
                 1j * rng.standard_normal(num_samples)) * noise_std
        iq += noise.astype(np.complex64)

    return iq.astype(np.complex64)


sample_rate = 19e3

samples = generate_bpsk_with_freq_offset(
    num_samples=250,
    samples_per_symbol=1,
    freq_offset_hz=300,   # simulate a 200 Hz offset
    fs=sample_rate,
    noise_std=0
)


# Prepare animation
fig, ax = plt.subplots()
ax.set_xlim(-1.5, 1.5)
ax.set_ylim(-1.5, 1.5)
ax.set_xlabel("I")
ax.set_ylabel("Q")
ax.set_title("Animated IQ Scatter")
scatter = ax.scatter([], [])

# Update function
def update(frame):
    window = samples[frame*10:frame*10+10]  # show more samples over time
    scatter.set_offsets(np.column_stack((window.real, window.imag)))
    return scatter,

# Animate
anim = FuncAnimation(fig, update, frames=200, interval=50, blit=True)

plt.show()

# Save to GIF
# gif_path = "/iq_animation.gif"
# anim.save(gif_path, writer=PillowWriter(fps=20))


N = len(samples)
phase = 0
freq = 0
# These next two params is what to adjust, to make the feedback loop faster or slower (which impacts stability)
alpha = 0.5
beta = 0.02
out = np.zeros(N, dtype=np.complex64)
freq_log = []
error_log = []
phase_log = []
phase_change_log = []
for i in range(N):
    out[i] = samples[i] * np.exp(-1j*phase) # adjust the input sample by the inverse of the estimated phase offset
    error = np.real(out[i]) * np.imag(out[i]) # This is the error formula for 2nd order Costas Loop (e.g. for BPSK)

    # Advance the loop (recalc phase and freq offset)
    freq += (beta * error)
    freq_log.append(freq) # convert from angular velocity to Hz for logging


    phase_change_log.append(freq + (alpha * error))

    phase += freq + (alpha * error)
    phase_log.append(phase)
    error_log.append(error)

    if i < 5:
        print(f"original {samples[i]:.6f} rot {out[i]:.6f}, error {error_log[i]:.6f}, freq {freq_log[i]:.6f}, phase {phase_log[i]:.6f}")

    # Optional: Adjust phase so its always between 0 and 2pi, recall that phase wraps around every 2pi
    while phase >= 2*np.pi:
        phase -= 2*np.pi
    while phase < 0:
        phase += 2*np.pi
x = out

print(samples[0])
print(x[0])

print("max change in phase in one step:", max(phase_change_log))

# ----------------------------------------------
# Old animated plots
# ----------------------------------------------
# fig, (ax_iq, ax_freq) = plt.subplots(1, 2, figsize=(10, 4))

# # IQ scatter initial setup
# ax_iq.set_xlim(-1.5, 1.5)
# ax_iq.set_ylim(-1.5, 1.5)
# ax_iq.set_title("Costas Loop Output: IQ Scatter")
# ax_iq.set_xlabel("I")
# ax_iq.set_ylabel("Q")
# scatter = ax_iq.scatter([], [])

# # Frequency plot setup
# ax_freq.set_title("Estimated Frequency Offset")
# ax_freq.set_xlabel("Sample Index")
# ax_freq.set_ylabel("Hz")
# ax_freq.set_xlim(0, N)
# ax_freq.set_ylim(min(freq_log), max(freq_log))
# line, = ax_freq.plot([], [])

# # update animation frame
# def update(frame):
#     # update IQ scatter (sliding window)
#     window = out[frame:(frame+1)]
#     scatter.set_offsets(np.column_stack((window.real, window.imag)))

#     # update freq estimate line
#     line.set_data(np.arange(frame), freq_log[:frame])

#     return scatter, line

# anim = FuncAnimation(fig, update, frames=N, interval=30, blit=True)

# plt.show()


fig, ((ax_iq, ax_error), (ax_freq, ax_phase)) = plt.subplots(2, 2, figsize=(10, 8))
ax_iq.set_xlim(-1.5, 1.5)
ax_iq.set_ylim(-1.5, 1.5)
ax_iq.set_xlabel("I")
ax_iq.set_ylabel("Q")
ax_iq.set_title("IQ Plot")
scatter = ax_iq.scatter(out.real, out.imag)

ax_error.set_title("Error")
ax_error.set_xlabel("Sample Index")
ax_error.set_ylabel("err")
ax_error.plot(np.arange(len(error_log)), error_log)

ax_freq.set_title("Frequency")
ax_freq.set_xlabel("Sample Index")
ax_freq.set_ylabel("Hz")
ax_freq.plot(np.arange(len(freq_log)), freq_log)

ax_phase.set_title("Phase")
ax_phase.set_xlabel("Sample Index")
ax_phase.set_ylabel("Phase (radians)")
ax_phase.plot(np.arange(len(phase_log)), phase_log)

plt.show()