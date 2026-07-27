"""
Visualization helpers for batch graphs.

Note: this used to build a pandas DataFrame from batch_results. pandas is
a fairly heavy dependency for what was actually a thin usage here (build
a table, coerce a few columns to numeric, drop invalid rows, do some
column-wise min/max/plotting) - all replaced below with plain Python +
the numpy we already depend on anyway, saving pandas and its transitive
dependencies entirely.
"""

import os
import logging
import traceback
import numpy as np

logger = logging.getLogger(__name__)


def _import_matplotlib():
    """Safely imports matplotlib and sets a non-interactive backend."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend for servers
        import matplotlib.pyplot as plt
        logger.info("matplotlib imported successfully.")
        return matplotlib, plt
    except ImportError as e:
        logger.warning("matplotlib import failed: %s. Graph generation will be skipped.", e)
        return None, None


def _to_float_or_nan(value):
    """Mirrors pandas.to_numeric(errors='coerce'): convert to float, or
    NaN if that's not possible, rather than raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _clean_batch_results(batch_results):
    """
    Replaces the old pandas pipeline (DataFrame -> to_numeric(errors=
    'coerce') -> dropna) with plain Python: coerce the numeric columns,
    then drop any row missing a required metric.
    """
    cleaned = []
    numeric_cols = ("psnr", "ssim", "capacity", "ber", "file_size")
    required_cols = ("psnr", "ssim", "capacity", "file_size")
    for row in batch_results:
        row = dict(row)
        for col in numeric_cols:
            if col in row:
                row[col] = _to_float_or_nan(row[col])
        if all(col in row and not np.isnan(row[col]) for col in required_cols):
            cleaned.append(row)
    return cleaned


def generate_all_graphs(batch_results, output_dir):
    """
    Generates a set of performance analysis graphs from batch results.

    Returns:
        dict: A dictionary indicating success and a list of generated graph filenames.
    """
    matplotlib, plt = _import_matplotlib()
    if not all([matplotlib, plt]):
        return {'success': False, 'error': 'matplotlib is not installed on the server'}

    if not batch_results:
        return {'success': False, 'error': 'No successful results provided for graph generation'}

    try:
        os.makedirs(output_dir, exist_ok=True)

        records = _clean_batch_results(batch_results)
        if not records:
            return {'success': False, 'error': 'No valid numeric data to plot after cleaning'}

        psnr_arr = np.array([r['psnr'] for r in records], dtype=np.float64)
        ssim_arr = np.array([r['ssim'] for r in records], dtype=np.float64)
        capacity_arr = np.array([r['capacity'] for r in records], dtype=np.float64)
        file_size_arr = np.array([r['file_size'] for r in records], dtype=np.float64)
        filenames = [r.get('filename', '') for r in records]

        generated_graphs = []

        # --- Graph 1: Scatter Plots (PSNR vs. File Size, SSIM vs. Capacity) ---
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
            fig.suptitle('Performance Scatter Plots', fontsize=16, y=0.95)

            ax1.scatter(file_size_arr, psnr_arr, alpha=0.7, edgecolors='w', s=80)
            ax1.set_xlabel('File Size (KB)')
            ax1.set_ylabel('PSNR (dB)')
            ax1.set_title('PSNR vs. Cover Image File Size')
            ax1.grid(True, linestyle='--', alpha=0.6)

            ax2.scatter(capacity_arr, ssim_arr, alpha=0.7, edgecolors='w', s=80, color='green')
            ax2.set_xlabel('Payload Capacity (bits per pixel)')
            ax2.set_ylabel('SSIM')
            ax2.set_title('SSIM vs. Payload Capacity')
            ax2.grid(True, linestyle='--', alpha=0.6)

            plt.tight_layout(rect=[0, 0, 1, 0.93])
            scatter_path = os.path.join(output_dir, 'scatter_plots.png')
            plt.savefig(scatter_path, dpi=120)
            plt.close(fig)
            generated_graphs.append('scatter_plots.png')
            logger.info("Generated scatter_plots.png")
        except Exception as e:
            logger.error("Failed to generate scatter plot: %s", e)

        # --- Graph 2: Multi-Metric Line Comparison ---
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.set_title('Multi-Metric Comparison Across Files')

            file_indices = range(len(records))

            ax.plot(file_indices, psnr_arr, 'o-', label='PSNR (dB)', color='dodgerblue')
            ax.set_ylabel('PSNR (dB)', color='dodgerblue')
            ax.tick_params(axis='y', labelcolor='dodgerblue')

            ax2 = ax.twinx()
            ax2.plot(file_indices, ssim_arr, 's--', label='SSIM', color='crimson')
            ax2.set_ylabel('SSIM', color='crimson')
            ax2.tick_params(axis='y', labelcolor='crimson')
            ax2.set_ylim(min(0.9, ssim_arr.min() * 0.99), 1)

            ax.set_xlabel('File Index')
            ax.set_xticks(list(file_indices))
            ax.set_xticklabels([name[:15] for name in filenames], rotation=45, ha='right')
            fig.legend(loc="upper right", bbox_to_anchor=(1, 1), bbox_transform=ax.transAxes)

            plt.tight_layout()
            line_path = os.path.join(output_dir, 'multi_metric_line.png')
            plt.savefig(line_path, dpi=120)
            plt.close(fig)
            generated_graphs.append('multi_metric_line.png')
            logger.info("Generated multi_metric_line.png")
        except Exception as e:
            logger.error("Failed to generate line plot: %s", e)

        # --- Graph 3: Radar Chart for Performance Profile (using first 5 files) ---
        try:
            n = min(5, len(records))
            labels = ['PSNR', 'SSIM', 'Capacity']
            num_vars = len(labels)

            psnr_norm = (psnr_arr[:n] - 30) / 20  # Normalize PSNR (e.g., 30-50dB range)
            ssim_norm = (ssim_arr[:n] - 0.95) / 0.05  # Normalize SSIM (e.g., 0.95-1.0 range)
            capacity_norm = capacity_arr[:n] / capacity_arr.max()  # Normalize capacity

            stats = np.vstack([psnr_norm, ssim_norm, capacity_norm]).T

            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            stats = np.concatenate((stats, stats[:, [0]]), axis=1)
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)

            plt.xticks(angles[:-1], labels)
            ax.set_rlabel_position(0)
            ax.set_yticklabels([])  # Hide radial labels

            for i in range(n):
                ax.plot(angles, stats[i], 'o-', linewidth=2, label=f"File {i+1}: {filenames[i][:15]}...")
                ax.fill(angles, stats[i], alpha=0.25)

            plt.title('Performance Radar Profile (First 5 Images)', size=15, y=1.1)
            plt.legend(loc='upper right', bbox_to_anchor=(1.4, 1.1))

            radar_path = os.path.join(output_dir, 'radar_chart.png')
            plt.savefig(radar_path, dpi=120)
            plt.close(fig)
            generated_graphs.append('radar_chart.png')
            logger.info("Generated radar_chart.png")
        except Exception as e:
            logger.error("Failed to generate radar chart: %s", e)

        return {'success': True, 'graphs': generated_graphs}

    except Exception as e:
        logger.error("Error during graph generation: %s\n%s", e, traceback.format_exc())
        return {'success': False, 'error': str(e)}
