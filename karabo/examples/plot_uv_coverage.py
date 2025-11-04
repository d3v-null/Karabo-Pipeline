#!/usr/bin/env python
"""
Script to plot UV coverage from visibility data.
Reads uvfits or MS files and creates a grid showing UV plane occupancy.

for tel in mwa-ph1 mwa-ph2-cmp mwa-ph2-ext ska-low-aa0.5 ska-low-aa1 ska-low-aa2 ska-low-aastar; do
    docker run --rm -v $PWD/out:/out -v "$PWD/plot_uv_coverage.py:/tmp/plot_uv_coverage.py:ro" \
    sp5505:latest bash -lc "python /tmp/plot_uv_coverage.py --output /out/$tel.png /out/$tel.MS"
done
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from pathlib import Path
from pyuvdata import UVData


def read_uv_coordinates(filepath):
    """Read UV coordinates from visibility file using pyuvdata (with casacore fallback)."""
    try:
        # Try pyuvdata first (supports uvfits and MS)
        uvd = UVData()
        uvd.read(filepath, read_data=False)

        # Get UVW coordinates
        uvw = uvd.uvw_array  # Shape: (Nblts, 3)
        u = uvw[:, 0]
        v = uvw[:, 1]

        # Get lowest frequency
        freq = np.min(uvd.freq_array)

    except Exception as e:
        print(f"pyuvdata failed: {e}")
        print("Falling back to casacore for MS reading...")

        # Fallback to casacore for MS files
        from casacore.tables import table

        ms = table(filepath, readonly=True, ack=False)

        # Get UVW coordinates (in meters)
        uvw = ms.getcol('UVW')  # Shape: (Nrows, 3)
        u = uvw[:, 0]
        v = uvw[:, 1]

        # Get spectral window table for frequencies
        spw_table = table(f"{filepath}/SPECTRAL_WINDOW", readonly=True, ack=False)
        chan_freqs = spw_table.getcol('CHAN_FREQ')
        freq = np.min(chan_freqs)  # Use lowest frequency
        spw_table.close()

        ms.close()

    # Convert to wavelengths
    c = 299792458.0  # speed of light in m/s
    wavelength = c / freq

    u_lambda = u / wavelength
    v_lambda = v / wavelength

    return u_lambda, v_lambda


def filter_baselines(u, v, min_lambda, max_lambda):
    """Filter baselines based on UV distance."""
    uv_dist = np.sqrt(u**2 + v**2)
    mask = (uv_dist >= min_lambda) & (uv_dist <= max_lambda)
    return u[mask], v[mask]


def create_uv_grid(u, v, max_lambda, bin_width=0.5):
    """
    Create a grid of UV pixels and count occupancy.

    Parameters:
    -----------
    u, v : array-like
        UV coordinates in wavelengths
    max_lambda : float
        Maximum lambda value for grid extent
    bin_width : float
        Width of each UV pixel in wavelengths (default: 0.5)

    Returns:
    --------
    grid : 2D array
        Occupancy grid
    extent : tuple
        Grid extent (left, right, bottom, top) for plotting
    u_folded : array
        Folded u coordinates (for 1D histogram)
    """
    # if negative u , negate u and v
    u_folded = u * np.sign(u)
    v_folded = v * np.sign(u)

    # Define grid boundaries: u from 0 to max_lambda, v from -max_lambda to max_lambda
    u_bins = np.arange(0, max_lambda + bin_width, bin_width)
    v_bins = np.arange(-max_lambda, max_lambda + bin_width, bin_width)

    # Create 2D histogram
    grid, _, _ = np.histogram2d(u_folded, v_folded, bins=[u_bins, v_bins])

    # Extent for imshow: (left, right, bottom, top)
    extent = [0, max_lambda, -max_lambda, max_lambda]

    return grid, extent, u_folded


def plot_uv_coverage(grid, extent, u_data, max_lambda, bin_width, output_file=None, title="UV Coverage"):
    """Plot the UV coverage grid with 1D histogram below."""
    fig = plt.figure(figsize=(24, 36))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.3)

    plt.style.use('dark_background')

    # Top panel: 2D UV coverage
    ax1 = fig.add_subplot(gs[0])

    # Use symmetric log normalization to show contrast at low occupancy
    # while still handling high values
    norm = colors.SymLogNorm(linthresh=1.0, vmin=0, vmax=grid.max())

    # Plot the grid (transpose because histogram2d returns (x, y) but imshow expects (y, x))
    im = ax1.imshow(
        grid.T,
        origin='lower',
        extent=extent,
        aspect='auto',
        cmap='inferno',
        interpolation='bilinear',
        norm=norm,
    )

    ax1.set_xlabel('u (wavelengths)', fontsize=12)
    ax1.set_ylabel('v (wavelengths)', fontsize=12)
    ax1.set_title(title, fontsize=14)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax1, label='Occupancy')

    # Bottom panel: 1D radial histogram
    ax2 = fig.add_subplot(gs[1])

    # Create bins for 1D histogram
    u_bins = np.arange(0, max_lambda + bin_width, bin_width)
    counts, edges = np.histogram(u_data, bins=u_bins)

    # Plot as bar chart
    bin_centers = (edges[:-1] + edges[1:]) / 2
    ax2.bar(bin_centers, counts, width=bin_width, edgecolor='black', linewidth=0.5)

    ax2.set_xlabel('u (wavelengths)', fontsize=12)
    ax2.set_ylabel('Count', fontsize=12)
    ax2.set_xlim(0, max_lambda)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_file}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Plot UV coverage from visibility data (uvfits or MS format)"
    )
    parser.add_argument(
        'visibility_file',
        type=str,
        help='Path to visibility file (uvfits or MS)'
    )
    parser.add_argument(
        '--min-lambda',
        type=float,
        default=10.0,
        help='Minimum baseline length in wavelengths (default: 10)'
    )
    parser.add_argument(
        '--max-lambda',
        type=float,
        default=100.0,
        help='Maximum baseline length in wavelengths (default: 100)'
    )
    parser.add_argument(
        '--bin-width',
        type=float,
        default=0.5,
        help='Width of UV pixels in wavelengths (default: 0.5)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file for plot (optional)'
    )

    args = parser.parse_args()

    # Check if file exists
    filepath = Path(args.visibility_file)
    if not filepath.exists():
        print(f"Error: File {filepath} does not exist")
        return 1

    # Read UV coordinates
    print(f"Reading visibility file: {filepath}")
    u_lambda, v_lambda = read_uv_coordinates(str(filepath))
    print(f"Read {len(u_lambda)} visibilities")

    # Filter baselines
    print(f"Filtering baselines: {args.min_lambda} - {args.max_lambda} wavelengths")
    u_filtered, v_filtered = filter_baselines(u_lambda, v_lambda, args.min_lambda, args.max_lambda)
    print(f"Retained {len(u_filtered)} visibilities after filtering")

    # Create UV grid
    print("Creating UV grid...")
    grid, extent, u_folded = create_uv_grid(u_filtered, v_filtered, args.max_lambda, args.bin_width)
    print(f"Grid shape: {grid.shape}")
    print(f"Total occupancy: {np.sum(grid):.0f}")
    print(f"Non-zero pixels: {np.count_nonzero(grid)}")

    # Plot
    title = f"UV Coverage ({args.min_lambda}-{args.max_lambda} λ)"
    plot_uv_coverage(grid, extent, u_folded, args.max_lambda, args.bin_width, args.output, title)

    return 0


if __name__ == '__main__':
    exit(main())
