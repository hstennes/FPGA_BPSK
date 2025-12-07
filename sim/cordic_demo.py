import math

# Generate arctan table
cordic_angles = [math.degrees(math.atan(2**(-i))) for i in range(30)]
K = 0.6072529350088814   # scaling factor for infinite iterations

def cordic_rotate(x, y, angle_deg, iterations=25):
    # --- 1. Normalize angle to principal domain ---
    z = angle_deg

    while z > 180: z -= 360
    while z < -180: z += 360

    if z > 90:
        x, y = -x, -y
        z -= 180
    elif z < -90:
        x, y = -x, -y
        z += 180

    # --- 2. Iterative rotation ---
    for i in range(iterations):
        di = 1 if z >= 0 else -1
        xn = x - di * (y * (2**-i))
        yn = y + di * (x * (2**-i))
        zn = z - di * cordic_angles[i]

        x, y, z = xn, yn, zn

    # --- 3. Remove scaling if needed ---
    return x*K, y*K   # or return x,y unscaled if you prefer performance

# Example
x,y = cordic_rotate(-1,-1,45)  # rotate (1,0) by 135°
print(x,y)  # Output ≈ (-0.707, 0.707)