#!/usr/bin/env python3
"""
Krinsky-Robb Confidence Interval Visualization (Version 2)
"""
import matplotlib.pyplot as plt
import numpy as np

# Set Japanese font support
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans CJK JP', 'IPAexGothic', 'TakaoPGothic']
plt.rcParams['axes.unicode_minus'] = False

# Data from Krinsky-Robb CI results
parameters = ['ASC', "MF (A' -A)", 'MF × Score', 'MF × Lfprefer', 'MF × TDR', 'MF × RA']
point_estimates = [1548.322, 336.866, 110.068, -176.160, 489.733, 10.551]
ci_lower = [1195.323, 240.655, 62.755, -307.357, -158.274, -70.760]
ci_upper = [1899.704, 429.120, 157.663, -44.421, 1143.116, 91.263]

# Calculate error bars (distance from point estimate to CI bounds)
lower_errors = [pe - cl for pe, cl in zip(point_estimates, ci_lower)]
upper_errors = [cu - pe for pe, cu in zip(point_estimates, ci_upper)]
errors = [lower_errors, upper_errors]

# Create figure with larger size
fig, ax = plt.subplots(figsize=(14, 8))

# Create horizontal bar chart with error bars
y_pos = np.arange(len(parameters))
# Assign colors: gray for CI crossing zero, blue for positive, red for negative
colors = []
for pe, cl, cu in zip(point_estimates, ci_lower, ci_upper):
    if cl < 0 and cu > 0:  # CI crosses zero
        colors.append('#808080')  # Gray
    elif pe > 0:
        colors.append('#2E86AB')  # Blue
    else:
        colors.append('#A23B72')  # Red-purple

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
        label_x = pe + upper_errors[i] + 80
        ha_align = 'left'
    else:
        label_x = pe - lower_errors[i] - 80
        ha_align = 'right'

    # Show point estimate (mean) prominently
    ax.text(label_x, i, f'Mean: {pe:.2f}\nCI: [{cl:.1f}, {cu:.1f}]',
            va='center', ha=ha_align,
            fontsize=14, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.8))

plt.tight_layout()
plt.savefig('krinsky_robb_ci_plot2.png', dpi=300, bbox_inches='tight')
print("Plot saved as 'krinsky_robb_ci_plot2.png'")

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
    ax2.text(cu + 60, i, f'{param}\nMean: {pe:.2f}\nCI: [{cl:.1f}, {cu:.1f}]',
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
plt.savefig('krinsky_robb_ci_ranges2.png', dpi=300, bbox_inches='tight')
print("Plot saved as 'krinsky_robb_ci_ranges2.png'")

plt.show()
