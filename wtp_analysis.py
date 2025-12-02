"""
WTP (Willingness to Pay) Confidence Intervals Analysis
Krinsky-Robb 95% Confidence Intervals for ΔWTP_Fresh
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def load_wtp_data(filepath='wtp_confidence_intervals.csv'):
    """
    Load WTP confidence interval data from CSV file

    Args:
        filepath: Path to the CSV file

    Returns:
        pandas.DataFrame: WTP data with confidence intervals
    """
    df = pd.read_csv(filepath)
    return df


def display_wtp_summary(df):
    """
    Display WTP confidence intervals summary

    Args:
        df: DataFrame containing WTP data
    """
    print("\n" + "="*70)
    print("Krinsky-Robb 95% Confidence Intervals for WTP")
    print("="*70)

    for idx, row in df.iterrows():
        print(f"\n{row['Category']}")
        print(f"  Mean: {row['Mean']:.2f}")
        print(f"  95% CI: [{row['CI_Lower']:.3f}, {row['CI_Upper']:.3f}]")
        if row['LFpref'] != 'All':
            print(f"  LFpref: {row['LFpref']}")

    print("\n" + "="*70)


def calculate_ci_width(df):
    """
    Calculate confidence interval width for each category

    Args:
        df: DataFrame containing WTP data

    Returns:
        pandas.DataFrame: Original data with CI width added
    """
    df['CI_Width'] = df['CI_Upper'] - df['CI_Lower']
    return df


def plot_confidence_intervals(df, output_file='wtp_confidence_intervals.png'):
    """
    Create a horizontal plot of confidence intervals

    Args:
        df: DataFrame containing WTP data
        output_file: Output filename for the plot
    """
    fig, ax = plt.subplots(figsize=(18, 9))

    categories = df['Category'].tolist()
    means = df['Mean'].tolist()
    ci_lower = df['CI_Lower'].tolist()
    ci_upper = df['CI_Upper'].tolist()

    y_positions = range(len(categories))

    # Convert category names to LaTeX format for better mathematical notation
    categories_latex = []
    for cat in categories:
        # Replace ΔWTP_Fresh with proper LaTeX notation
        cat_latex = cat.replace('ΔWTP_Fresh', r'$\Delta WTP_{\mathit{Fresh}}$')
        categories_latex.append(cat_latex)

    # Plot confidence intervals as horizontal lines
    for i, (cat, mean, lower, upper) in enumerate(zip(categories, means, ci_lower, ci_upper)):
        # CI line
        ax.plot([lower, upper], [i, i], 'o-', color='skyblue', linewidth=4, markersize=16)
        # Mean point
        ax.plot(mean, i, 'D', color='darkblue', markersize=20)

        # Add text annotation below or above the mean point to avoid overlap
        if i == 2:  # Bottom row (LFpref=1) - place below
            ax.text(mean, i - 0.38, f'Mean: {mean:.2f}\nCI: [{lower:.3f}, {upper:.3f}]',
                    ha='center', va='top', fontsize=27,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        else:  # Top and middle rows (Overall and LFpref=0) - place above
            ax.text(mean, i + 0.38, f'Mean: {mean:.2f}\nCI: [{lower:.3f}, {upper:.3f}]',
                    ha='center', va='bottom', fontsize=27,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.set_yticks(y_positions)
    ax.set_yticklabels(categories_latex, fontsize=24)
    ax.set_xlabel('WTP Value', fontsize=24)
    ax.set_title(r'Krinsky-Robb 95% Confidence Intervals for $\Delta WTP_{\mathit{Fresh}}$' + '\n(◆ = Mean/Point Estimate, Line = CI Range)',
                 fontsize=28, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Increase tick label size on x-axis
    ax.tick_params(axis='x', labelsize=20)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")

    return fig, ax


def compare_wtp_by_preference(df):
    """
    Compare WTP between different local food preferences

    Args:
        df: DataFrame containing WTP data
    """
    print("\n" + "="*70)
    print("WTP Comparison by Local Food Preference (LFpref)")
    print("="*70)

    # Filter rows with specific LFpref values
    lfpref_data = df[df['LFpref'] != 'All'].copy()

    # Convert LFpref to numeric if needed
    lfpref_data['LFpref'] = pd.to_numeric(lfpref_data['LFpref'], errors='coerce')
    lfpref_data = lfpref_data.dropna(subset=['LFpref'])

    if len(lfpref_data) >= 2:
        lfpref_0_data = lfpref_data[lfpref_data['LFpref'] == 0]
        lfpref_1_data = lfpref_data[lfpref_data['LFpref'] == 1]

        if len(lfpref_0_data) > 0 and len(lfpref_1_data) > 0:
            lfpref_0 = lfpref_0_data.iloc[0]
            lfpref_1 = lfpref_1_data.iloc[0]

            mean_diff = lfpref_1['Mean'] - lfpref_0['Mean']
            percent_diff = (mean_diff / lfpref_0['Mean']) * 100

            print(f"\nLFpref=0 (No preference for local food):")
            print(f"  Mean WTP: {lfpref_0['Mean']:.2f}")

            print(f"\nLFpref=1 (Preference for local food):")
            print(f"  Mean WTP: {lfpref_1['Mean']:.2f}")

            print(f"\nDifference:")
            print(f"  Absolute: {mean_diff:.2f}")
            print(f"  Relative: {percent_diff:.2f}%")
            print(f"\nConclusion: Consumers with local food preference show")
            print(f"            {percent_diff:.1f}% higher WTP for fresh products")

    print("\n" + "="*70)


def main():
    """
    Main function to run WTP analysis
    """
    # Load data
    df = load_wtp_data()

    # Display summary
    display_wtp_summary(df)

    # Calculate CI width
    df = calculate_ci_width(df)
    print("\nConfidence Interval Widths:")
    for idx, row in df.iterrows():
        print(f"  {row['Category']}: {row['CI_Width']:.3f}")

    # Compare by preference
    compare_wtp_by_preference(df)

    # Create plot
    try:
        plot_confidence_intervals(df)
    except Exception as e:
        print(f"\nNote: Could not create plot - {e}")
        print("(This is normal in environments without display)")

    return df


if __name__ == "__main__":
    df = main()
