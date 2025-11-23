#!/usr/bin/env python3
"""
Krinsky-Robb Confidence Interval Visualization
"""
import matplotlib.pyplot as plt
import numpy as np

# Set Japanese font support
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans CJK JP', 'IPAexGothic', 'TakaoPGothic']
plt.rcParams['axes.unicode_minus'] = False

# Data from Krinsky-Robb CI results
parameters = ['freshlabel', 'labelB', 'freshlabelB', 'asc', 'freshness', 'label']
point_estimates = [437.024, 290.707, -398.607, 821.295, 127.283, -172.753]
ci_lower = [329.937, 166.988, -555.682, 734.414, 32.294, -266.700]
ci_upper = [545.796, 415.801, -244.501, 911.571, 220.769, -80.971]

# Calculate error bars (distance from point estimate to CI bounds)
lower_errors = [pe - cl for pe, cl in zip(point_estimates, ci_lower)]
upper_errors = [cu - pe for pe, cu in zip(point_estimates, ci_upper)]
errors = [lower_errors, upper_errors]

# Create figure with larger size
fig, ax = plt.subplots(figsize=(14, 8))

# Create horizontal bar chart with error bars
y_pos = np.arange(len(parameters))
colors = ['#2E86AB' if pe > 0 else '#A23B72' for pe in point_estimates]

bars = ax.barh(y_pos, point_estimates, color=colors, alpha=0.7, height=0.6)

# Add error bars (confidence intervals)
ax.errorbar(point_estimates, y_pos, xerr=errors, fmt='none',
            ecolor='black', capsize=8, capthick=2.5, linewidth=2)

# Customize plot with larger fonts
ax.set_yticks(y_pos)
ax.set_yticklabels(parameters, fontsize=16, fontweight='bold')
ax.set_xlabel('Parameter Value', fontsize=18, fontweight='bold')
ax.set_title('Krinsky-Robb CI for Individual Parameters\n(Point Estimates with 95% Confidence Intervals)',
             fontsize=20, fontweight='bold', pad=20)
ax.axvline(x=0, color='black', linestyle='-', linewidth=1.2)
ax.grid(axis='x', alpha=0.3, linestyle='--')
ax.tick_params(axis='x', labelsize=14)

# Add value labels showing point estimates and CI ranges
for i, (bar, pe, cl, cu) in enumerate(zip(bars, point_estimates, ci_lower, ci_upper)):
    # Position for text
    if pe > 0:
        label_x = pe + upper_errors[i] + 60
        ha_align = 'left'
    else:
        label_x = pe - lower_errors[i] - 60
        ha_align = 'right'

    # Show point estimate (mean) prominently
    ax.text(label_x, i, f'Mean: {pe:.2f}\nCI: [{cl:.1f}, {cu:.1f}]',
            va='center', ha=ha_align,
            fontsize=14, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.8))

plt.tight_layout()
plt.savefig('krinsky_robb_ci_plot.png', dpi=300, bbox_inches='tight')
print("Plot saved as 'krinsky_robb_ci_plot.png'")

# Also create a second plot showing CI ranges more explicitly
fig2, ax2 = plt.subplots(figsize=(14, 8))

for i, (param, pe, cl, cu) in enumerate(zip(parameters, point_estimates, ci_lower, ci_upper)):
    # Draw CI line
    ax2.plot([cl, cu], [i, i], 'o-', linewidth=4, markersize=12,
             color=colors[i], alpha=0.6, label=param)
    # Draw point estimate (mean)
    ax2.plot(pe, i, 'D', markersize=16, color=colors[i],
             markeredgecolor='black', markeredgewidth=2)

    # Add text annotations with point estimate
    ax2.text(cu + 40, i, f'{param}\nMean: {pe:.2f}\nCI: [{cl:.1f}, {cu:.1f}]',
             va='center', ha='left', fontsize=13, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.8))

ax2.set_yticks(y_pos)
ax2.set_yticklabels(parameters, fontsize=16, fontweight='bold')
ax2.set_xlabel('Parameter Value', fontsize=18, fontweight='bold')
ax2.set_title('Krinsky-Robb 95% Confidence Intervals\n(◆ = Mean/Point Estimate, Line = CI Range)',
              fontsize=20, fontweight='bold', pad=20)
ax2.axvline(x=0, color='black', linestyle='-', linewidth=1.2)
ax2.grid(axis='x', alpha=0.3, linestyle='--')
ax2.tick_params(axis='x', labelsize=14)
ax2.invert_yaxis()

plt.tight_layout()
plt.savefig('krinsky_robb_ci_ranges.png', dpi=300, bbox_inches='tight')
print("Plot saved as 'krinsky_robb_ci_ranges.png'")

plt.show()
