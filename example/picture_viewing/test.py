import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV file (replace with your actual file path)
df = pd.read_csv("data/deepgaze_demo.csv")

# Keep only rows where at least one eye is valid
df = df[(df["left_eye_valid"] == 1) | (df["right_eye_valid"] == 1)]

fig, ax = plt.subplots(figsize=(8, 6))

# Left eye trace
left = df[df["left_eye_valid"] == 1]
ax.plot(left["left_eye_gaze_position_x"],
        left["left_eye_gaze_position_y"],
        linestyle="-", linewidth=1.5, alpha=0.5,
        color="tab:blue", label="Left eye")

# Right eye trace
right = df[df["right_eye_valid"] == 1]
ax.plot(right["right_eye_gaze_position_x"],
        right["right_eye_gaze_position_y"],
        linestyle="-", linewidth=1.5, alpha=0.5,
        color="tab:orange", label="Right eye")

ax.invert_yaxis()  # screen coordinates: y increases downward
ax.set_xlabel("Gaze position X (px)")
ax.set_ylabel("Gaze position Y (px)")
ax.set_title("Left and Right Eye Gaze Trace")
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_aspect("equal", adjustable="datalim")
plt.tight_layout()
plt.show()