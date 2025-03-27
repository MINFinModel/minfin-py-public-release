import os
import re
import plotly.graph_objects as go

def save_figure(fig, output_dir="figures", save_html=True, save_png=True, custom_name=None):
    """
    Save a Plotly figure to file(s) with a single function call.
    
    Parameters:
    -----------
    fig : plotly.graph_objects.Figure
        The Plotly figure to save
    output_dir : str, default="figures"
        Directory to save the figure(s)
    save_html : bool, default=True
        Whether to save as interactive HTML file
    save_png : bool, default=True
        Whether to save as static PNG file
    custom_name : str, optional
        Custom filename to use instead of the figure title
        
    Returns:
    --------
    dict
        Dictionary with paths to the saved files
        
    Examples:
    ---------
    >>> save_figure(fig_area1)
    >>> save_figure(fig_area2, custom_name="investment_by_category")
    """
    # Make sure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get figure title or use custom name
    if custom_name:
        base_name = custom_name
    else:
        # Extract title from figure
        title = fig.layout.title.text if hasattr(fig.layout, 'title') and hasattr(fig.layout.title, 'text') else None
        
        if not title:
            # Try to get title from layout dict
            title = fig.layout.get('title', {})
            if isinstance(title, dict):
                title = title.get('text', 'untitled')
            elif not title:
                title = 'untitled'
        
        # Convert title to a valid filename
        base_name = re.sub(r'[\\/*?:"<>|]', "", title)
        base_name = base_name.replace(" ", "_")
    
    # Dictionary to store saved file paths
    saved_files = {}
    
    # Save as HTML (interactive)
    if save_html:
        html_path = os.path.join(output_dir, f"{base_name}.html")
        try:
            fig.write_html(html_path)
            saved_files['html'] = html_path
            print(f"Saved HTML: {html_path}")
        except Exception as e:
            print(f"Error saving HTML: {e}")
    
    # Save as PNG (static)
    if save_png:
        png_path = os.path.join(output_dir, f"{base_name}.png")
        try:
            fig.write_image(png_path)
            saved_files['png'] = png_path
            print(f"Saved PNG: {png_path}")
        except ImportError:
            print("Error: Could not save PNG. Make sure kaleido is installed: pip install kaleido")
        except Exception as e:
            print(f"Error saving PNG: {e}")
    
    return saved_files


def save_all_figures(figures, output_dir="figures", save_html=True, save_png=True):
    """
    Save multiple Plotly figures at once.
    
    Parameters:
    -----------
    figures : list or dict
        List of figures or dictionary {name: figure}
    output_dir : str, default="figures"
        Directory to save the figures
    save_html : bool, default=True
        Whether to save as HTML files
    save_png : bool, default=True
        Whether to save as PNG files
        
    Returns:
    --------
    dict
        Dictionary with paths to all saved files
    """
    all_saved = {}
    
    # Make sure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    if isinstance(figures, dict):
        # If dictionary of named figures
        for name, fig in figures.items():
            all_saved[name] = save_figure(
                fig, 
                output_dir=output_dir,
                save_html=save_html,
                save_png=save_png,
                custom_name=name
            )
    else:
        # If list of figures
        for i, fig in enumerate(figures):
            all_saved[f"figure_{i}"] = save_figure(
                fig, 
                output_dir=output_dir,
                save_html=save_html,
                save_png=save_png
            )
    
    return None
