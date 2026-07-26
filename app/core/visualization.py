# START OF MODIFIED visualization.py

"""
Visualization helpers for batch graphs.
"""

import os
import logging
import traceback
import pandas as pd
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
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert results to a pandas DataFrame for easier manipulation
        df = pd.DataFrame(batch_results)
        
        # Ensure numeric types for plotting
        for col in ['psnr', 'ssim', 'capacity', 'ber', 'file_size']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['psnr', 'ssim', 'capacity', 'file_size'], inplace=True)

        if df.empty:
            return {'success': False, 'error': 'No valid numeric data to plot after cleaning'}

        generated_graphs = []

        # --- Graph 1: Scatter Plots (PSNR vs. File Size, SSIM vs. Capacity) ---
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
            fig.suptitle('Performance Scatter Plots', fontsize=16, y=0.95)

            # PSNR vs. File Size
            ax1.scatter(df['file_size'], df['psnr'], alpha=0.7, edgecolors='w', s=80)
            ax1.set_xlabel('File Size (KB)')
            ax1.set_ylabel('PSNR (dB)')
            ax1.set_title('PSNR vs. Cover Image File Size')
            ax1.grid(True, linestyle='--', alpha=0.6)

            # SSIM vs. Payload Capacity
            ax2.scatter(df['capacity'], df['ssim'], alpha=0.7, edgecolors='w', s=80, color='green')
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
            
            # Use file index as x-axis
            file_indices = range(len(df))
            
            # Plot PSNR
            ax.plot(file_indices, df['psnr'], 'o-', label='PSNR (dB)', color='dodgerblue')
            ax.set_ylabel('PSNR (dB)', color='dodgerblue')
            ax.tick_params(axis='y', labelcolor='dodgerblue')
            
            # Create a second y-axis for SSIM
            ax2 = ax.twinx()
            ax2.plot(file_indices, df['ssim'], 's--', label='SSIM', color='crimson')
            ax2.set_ylabel('SSIM', color='crimson')
            ax2.tick_params(axis='y', labelcolor='crimson')
            ax2.set_ylim(min(0.9, df['ssim'].min() * 0.99), 1)

            ax.set_xlabel('File Index')
            ax.set_xticks(file_indices)
            ax.set_xticklabels([name[:15] for name in df['filename']], rotation=45, ha='right')
            fig.legend(loc="upper right", bbox_to_anchor=(1,1), bbox_transform=ax.transAxes)
            
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
            # Take a sample of up to 5 files for clarity
            radar_df = df.head(5)
            labels = ['PSNR', 'SSIM', 'Capacity']
            num_vars = len(labels)
            
            # Normalize data for radar chart
            psnr_norm = (radar_df['psnr'] - 30) / 20  # Normalize PSNR (e.g., 30-50dB range)
            ssim_norm = (radar_df['ssim'] - 0.95) / 0.05 # Normalize SSIM (e.g., 0.95-1.0 range)
            capacity_norm = radar_df['capacity'] / df['capacity'].max() # Normalize capacity
            
            stats = np.vstack([psnr_norm, ssim_norm, capacity_norm]).T
            
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            stats = np.concatenate((stats, stats[:, [0]]), axis=1)
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            
            plt.xticks(angles[:-1], labels)
            ax.set_rlabel_position(0)
            ax.set_yticklabels([]) # Hide radial labels

            for i in range(len(radar_df)):
                ax.plot(angles, stats[i], 'o-', linewidth=2, label=f"File {i+1}: {radar_df.iloc[i]['filename'][:15]}...")
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

# END OF MODIFIED visualization.py