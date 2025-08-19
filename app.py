import os, io, zipfile
from pathlib import Path
from flask import Flask, render_template, request, send_from_directory, send_file, redirect, url_for, flash
from PIL import Image, ImageOps

# Import our processor modules
from image_processing import (
    save_as_webp,
    convert_image_format,
    batch_convert_images,
    get_format_comparison,
    generate_responsive_images, 
    generate_srcset_html, 
    generate_thumbnails,
    generate_thumbnail_css,
    generate_thumbnail_html,
    generate_favicons,
    generate_favicon_html,
    generate_favicon_manifest,
    create_multi_ico_favicon,
    analyze_image_comprehensive,
    batch_analyze_images,
    WEB_FORMATS,
    RESPONSIVE_SIZES,
    THUMBNAIL_SIZES,
    CROP_METHODS,
    FAVICON_SIZES,
    FAVICON_SPECS
)

# Import optimization suite functions
from image_processing.optimization_suite import (
    optimize_image,
    batch_optimize_images,
    analyze_image_complexity,
    generate_optimization_report,
    OPTIMIZATION_PRESETS
)

# Import SVG toolkit functions
from image_processing.svg_toolkit import (
    validate_svg,
    optimize_svg,
    svg_to_png_multi_density,
    generate_app_icons,
    generate_color_variants,
    analyze_svg_complexity,
    generate_svg_report,
    MOBILE_DENSITIES,
    IOS_ICON_SIZES,
    ANDROID_ICON_SIZES,
    FLUTTER_ICON_SIZES
)

# Import utility functions
from utils.flask_helpers import (
    validate_and_get_files,
    get_output_directory,
    get_quality_settings,
    validate_selections,
    ALLOWED_EXT,
    DEFAULT_THUMBNAIL_QUALITY
)
from image_processing.utils import sanitize_filename

app = Flask(__name__)
app.secret_key = "dev"  # bara för flash-meddelanden lokalt

BASE_DIR = Path(__file__).parent.resolve()
DEFAULT_OUTPUT = BASE_DIR / "output"
DEFAULT_OUTPUT.mkdir(exist_ok=True)

@app.route("/", methods=["GET"])
def index():
    tab = request.args.get("tab", "webp")  # Default to webp tab
    return render_template("index.html", 
                         active_tab=tab, 
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS)

@app.route("/convert", methods=["POST"])
def convert():
    # Validate files
    files, error_response = validate_and_get_files()
    if error_response:
        return error_response

    # Get conversion settings
    output_format = request.form.get("output_format", "webp")
    quality_settings = get_quality_settings()
    format_comparison = request.form.get("format_comparison") == "on"

    # Get output directory
    out_dir = get_output_directory(BASE_DIR, DEFAULT_OUTPUT)

    converted = []
    comparisons = []
    
    for f in files:
        if format_comparison:
            # Generate format comparison
            f.stream.seek(0)  # Reset stream position
            comparison = get_format_comparison(f, out_dir, quality_settings["quality"])
            comparisons.append({
                "original": f.filename,
                "formats": comparison
            })
        else:
            # Regular conversion
            f.stream.seek(0)  # Reset stream position
            result = convert_image_format(f, out_dir, output_format, 
                                        quality_settings["quality"], 
                                        quality_settings["lossless"])
            converted.append(result)

    if not converted and not comparisons:
        flash("No allowed images were uploaded.")
        return redirect(url_for("index"))

    # ZIP download option
    if request.form.get("zip") == "on":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            if converted:
                for item in converted:
                    z.write(out_dir / item["filename"], arcname=item["filename"])
            if comparisons:
                for comp in comparisons:
                    for format_key, format_result in comp["formats"].items():
                        if "filename" in format_result:
                            z.write(out_dir / format_result["filename"], arcname=format_result["filename"])
        mem.seek(0)
        download_name = f"converted-{output_format}.zip" if converted else "format-comparison.zip"
        return send_file(mem, as_attachment=True, download_name=download_name, mimetype="application/zip")

    # Prepare results for display
    if converted:
        file_links = [url_for("serve_output", filename=item["filename"]) for item in converted]
        items = list(zip(converted, file_links))
    else:
        items = []

    return render_template("index.html", 
                         done=True, 
                         out_dir=str(out_dir), 
                         items=items, 
                         comparisons=comparisons,
                         lossless=quality_settings["lossless"], 
                         quality=quality_settings["quality"],
                         output_format=output_format,
                         active_tab="webp",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS)

@app.route("/output/<path:filename>")
def serve_output(filename):
    # serverar filer från valfri output-mapp bara när den ligger under projektet
    # (om du använder absolut mapp utanför projektet kan du öppna den i Explorer/Finder manuellt)
    return send_from_directory(DEFAULT_OUTPUT, filename, as_attachment=True)

@app.route("/responsive", methods=["POST"])
def responsive():
    # Validate files
    files, error_response = validate_and_get_files("responsive")
    if error_response:
        return error_response

    # Validate size selections
    selected_sizes, error_response = validate_selections(
        "sizes", "responsive", "Please select at least one size."
    )
    if error_response:
        return error_response

    # Get settings
    out_dir = get_output_directory(BASE_DIR, DEFAULT_OUTPUT)
    quality_settings = get_quality_settings()

    all_results = []
    for f in files:
        results = generate_responsive_images(f, out_dir, 
                                           quality_settings["quality"], 
                                           quality_settings["lossless"], 
                                           selected_sizes)
        if results:
            all_results.extend(results)

    if not all_results:
        flash("No images were processed. Make sure images are valid and target sizes are smaller than originals.")
        return redirect(url_for("index", tab="responsive"))

    # ZIP download option
    if request.form.get("zip") == "on":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for item in all_results:
                z.write(out_dir / item["name"], arcname=item["name"])
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="responsive-images.zip", mimetype="application/zip")

    # Show results
    file_links = [url_for("serve_output", filename=item["name"]) for item in all_results]
    items = list(zip(all_results, file_links))
    
    # Generate HTML srcset example
    srcset_example = generate_srcset_html(all_results)
    
    return render_template("index.html", 
                         active_tab="responsive",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS,
                         done=True, 
                         out_dir=str(out_dir), 
                         items=items, 
                         lossless=quality_settings["lossless"], 
                         quality=quality_settings["quality"],
                         srcset_example=srcset_example)

@app.route("/thumbnail", methods=["POST"])
def thumbnail():
    # Validate files
    files, error_response = validate_and_get_files("thumbnail")
    if error_response:
        return error_response

    # Validate size selections
    selected_sizes, error_response = validate_selections(
        "thumb_sizes", "thumbnail", "Please select at least one thumbnail size."
    )
    if error_response:
        return error_response

    # Get settings
    crop_method = request.form.get("crop_method", "center")
    format_type = request.form.get("format_type", "webp")
    out_dir = get_output_directory(BASE_DIR, DEFAULT_OUTPUT)
    quality = int(request.form.get("quality", str(DEFAULT_THUMBNAIL_QUALITY)))
    lossless = request.form.get("lossless") == "on" if format_type == "webp" else False

    all_results = []
    for f in files:
        results = generate_thumbnails(f, out_dir, quality, lossless, 
                                    selected_sizes, crop_method, format_type)
        if results:
            all_results.extend(results)

    if not all_results:
        flash("No images were processed. Make sure images are valid.")
        return redirect(url_for("index", tab="thumbnail"))

    # ZIP download option
    if request.form.get("zip") == "on":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for item in all_results:
                z.write(out_dir / item["name"], arcname=item["name"])
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="thumbnails.zip", mimetype="application/zip")

    # Show results
    file_links = [url_for("serve_output", filename=item["name"]) for item in all_results]
    items = list(zip(all_results, file_links))
    
    # Generate CSS and HTML examples
    css_examples = generate_thumbnail_css(all_results)
    html_examples = generate_thumbnail_html(all_results)
    
    return render_template("index.html", 
                         active_tab="thumbnail",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS,
                         done=True, 
                         out_dir=str(out_dir), 
                         items=items, 
                         lossless=lossless, 
                         quality=quality,
                         css_examples=css_examples,
                         html_examples=html_examples,
                         format_type=format_type,
                         crop_method=crop_method)

@app.route("/favicon", methods=["POST"])
def favicon():
    # Validate files
    files, error_response = validate_and_get_files("favicon")
    if error_response:
        return error_response

    # Validate size selections
    selected_sizes, error_response = validate_selections(
        "favicon_sizes", "favicon", "Please select at least one favicon size."
    )
    if error_response:
        return error_response

    # Get settings
    background_color = request.form.get("background_color", "transparent")
    out_dir = get_output_directory(BASE_DIR, DEFAULT_OUTPUT)

    all_results = []
    for f in files:
        results = generate_favicons(f, out_dir, selected_sizes, background_color)
        if results:
            all_results.extend(results)

    if not all_results:
        flash("No images were processed. Make sure images are valid.")
        return redirect(url_for("index", tab="favicon"))

    # Create traditional favicon.ico if ICO sizes were selected
    ico_sizes = [s for s in selected_sizes if s.startswith("ico_")]
    if ico_sizes and files:
        try:
            # Reset stream for the first file
            files[0].stream.seek(0)
            with Image.open(files[0].stream) as im:
                im = ImageOps.exif_transpose(im)
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                
                favicon_ico_path = out_dir / "favicon.ico"
                create_multi_ico_favicon(im, favicon_ico_path, background_color)
                
                # Add to results
                all_results.append({
                    "name": "favicon.ico",
                    "size_kb": round(favicon_ico_path.stat().st_size / 1024, 1),
                    "dimensions": "16x16, 32x32, 48x48",
                    "format": "ICO",
                    "size_key": "multi_ico",
                    "purpose": "Traditional multi-size favicon"
                })
        except Exception as e:
            flash(f"Error creating favicon.ico: {str(e)}")

    # ZIP download option
    if request.form.get("zip") == "on":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for item in all_results:
                z.write(out_dir / item["name"], arcname=item["name"])
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="favicons.zip", mimetype="application/zip")

    # Show results
    file_links = [url_for("serve_output", filename=item["name"]) for item in all_results]
    items = list(zip(all_results, file_links))
    
    # Generate HTML and manifest examples
    html_example = generate_favicon_html()
    manifest_example = generate_favicon_manifest()
    
    return render_template("index.html", 
                         active_tab="favicon",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS,
                         done=True, 
                         out_dir=str(out_dir), 
                         items=items, 
                         background_color=background_color,
                         html_example=html_example,
                         manifest_example=manifest_example)

@app.route("/optimize", methods=["POST"])
def optimize():
    # Validate files
    files, error_response = validate_and_get_files("optimize")
    if error_response:
        return error_response

    # Get optimization settings
    preset = request.form.get("preset", "web_basic")
    output_format = request.form.get("output_format", "auto")
    custom_quality = request.form.get("custom_quality")
    custom_max_width = request.form.get("custom_max_width")
    custom_max_height = request.form.get("custom_max_height")
    batch_mode = request.form.get("batch_mode") == "on"

    # Parse custom settings
    if custom_quality:
        try:
            custom_quality = int(custom_quality)
        except ValueError:
            custom_quality = None

    custom_max_size = None
    if custom_max_width and custom_max_height:
        try:
            custom_max_size = (int(custom_max_width), int(custom_max_height))
        except ValueError:
            custom_max_size = None

    # Get output directory
    out_dir = get_output_directory(BASE_DIR, DEFAULT_OUTPUT)

    # Process images
    if batch_mode and len(files) > 1:
        # Batch optimization
        results, errors, batch_stats = batch_optimize_images(
            files, out_dir, preset, output_format
        )
        optimization_report = generate_optimization_report(results, batch_stats)
    else:
        # Individual optimization
        results = []
        errors = []
        for f in files:
            try:
                f.stream.seek(0)  # Reset stream position
                result = optimize_image(
                    f, out_dir, preset, output_format, 
                    custom_quality, custom_max_size
                )
                results.append(result)
            except Exception as e:
                errors.append({
                    "filename": f.filename,
                    "error": str(e)
                })
        
        optimization_report = generate_optimization_report(results)
        batch_stats = None

    if not results:
        flash("No images were processed successfully.")
        return redirect(url_for("index", tab="optimize"))

    # ZIP download option
    if request.form.get("zip") == "on":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for item in results:
                z.write(out_dir / item["filename"], arcname=item["filename"])
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="optimized-images.zip", mimetype="application/zip")

    # Show results
    file_links = [url_for("serve_output", filename=item["filename"]) for item in results]
    items = list(zip(results, file_links))
    
    return render_template("index.html", 
                         active_tab="optimize",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS,
                         done=True, 
                         out_dir=str(out_dir), 
                         items=items,
                         optimization_results=results,
                         optimization_errors=errors,
                         optimization_report=optimization_report,
                         batch_stats=batch_stats,
                         preset=preset,
                         output_format=output_format)

@app.route("/analyze", methods=["POST"])
def analyze():
    # Validate files
    files, error_response = validate_and_get_files("analyze")
    if error_response:
        return error_response

    # Process images for analysis
    if len(files) == 1:
        # Single image detailed analysis
        try:
            files[0].stream.seek(0)
            analysis_result = analyze_image_comprehensive(files[0])
            analysis_results = [analysis_result]
            analysis_errors = []
            batch_insights = {}
        except Exception as e:
            analysis_results = []
            analysis_errors = [{"filename": files[0].filename, "error": str(e)}]
            batch_insights = {}
    else:
        # Batch analysis
        analysis_results, analysis_errors, batch_insights = batch_analyze_images(files)

    if not analysis_results:
        flash("No images could be analyzed successfully.")
        return redirect(url_for("index", tab="analyze"))

    return render_template("index.html", 
                         active_tab="analyze",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS,
                         done=True,
                         analysis_results=analysis_results,
                         analysis_errors=analysis_errors,
                         batch_insights=batch_insights,
                         is_single_analysis=len(analysis_results) == 1)

@app.route("/svg_process", methods=["POST"])
def svg_process():
    # Get SVG files
    files = request.files.getlist("svgs")
    if not files or files[0].filename == "":
        flash("Please choose at least one SVG file.")
        return redirect(url_for("index", tab="svg"))

    # Filter SVG files
    svg_files = []
    for f in files:
        if f.filename.lower().endswith('.svg'):
            svg_files.append(f)

    if not svg_files:
        flash("No valid SVG files were uploaded.")
        return redirect(url_for("index", tab="svg"))

    # Get processing options
    optimize = request.form.get("optimize") == "on"
    aggressive_optimization = request.form.get("aggressive_optimization") == "on"
    validate = request.form.get("validate") == "on"
    generate_pngs = request.form.get("generate_pngs") == "on"
    app_icons = request.form.get("app_icons") == "on"
    color_variants = request.form.get("color_variants") == "on"

    # Get output directory
    out_dir = get_output_directory(BASE_DIR, DEFAULT_OUTPUT)
    
    # Create SVG-specific output directory
    svg_out_dir = out_dir / "svg_processed"
    svg_out_dir.mkdir(exist_ok=True)

    results = {
        "optimized_svgs": [],
        "png_variants": [],
        "app_icon_sets": [],
        "color_variant_sets": [],
        "analysis_reports": []
    }

    for svg_file in svg_files:
        # Read SVG content
        svg_file.stream.seek(0)
        svg_content = svg_file.stream.read().decode('utf-8')
        base_name = sanitize_filename(svg_file.filename)

        # Validation and analysis
        if validate:
            report = generate_svg_report(svg_content, svg_file.filename)
            results["analysis_reports"].append(report)

        # Optimization
        if optimize:
            optimization_result = optimize_svg(svg_content, aggressive_optimization)
            optimized_content = optimization_result["optimized_svg"]
            
            # Save optimized SVG
            optimized_filename = f"{base_name}_optimized.svg"
            optimized_path = svg_out_dir / optimized_filename
            with open(optimized_path, 'w', encoding='utf-8') as f:
                f.write(optimized_content)
            
            optimization_result["filename"] = optimized_filename
            optimization_result["path"] = str(optimized_path)
            results["optimized_svgs"].append(optimization_result)
            
            # Use optimized content for further processing
            svg_content = optimized_content

        # PNG generation
        if generate_pngs:
            base_size = int(request.form.get("base_size", "48"))
            density_set = request.form.get("density_set", "mobile")
            
            density_map = MOBILE_DENSITIES
            if density_set == "ios":
                density_map = {"1x": 1.0, "2x": 2.0, "3x": 3.0}
            elif density_set == "android":
                density_map = MOBILE_DENSITIES
            elif density_set == "web":
                density_map = {"1x": 1.0, "2x": 2.0, "3x": 3.0, "4x": 4.0}

            png_dir = svg_out_dir / "png_variants"
            png_results = svg_to_png_multi_density(
                svg_content, base_size, png_dir, base_name, density_map
            )
            results["png_variants"].extend(png_results)

        # App icon generation
        if app_icons:
            app_name = request.form.get("app_name", "MyApp")
            platforms = request.form.getlist("platforms")
            
            if platforms:
                icons_dir = svg_out_dir / "app_icons"
                icon_sets = generate_app_icons(svg_content, icons_dir, app_name)
                
                # Filter by selected platforms
                filtered_sets = {}
                for platform in platforms:
                    if platform in icon_sets:
                        filtered_sets[platform] = icon_sets[platform]
                
                results["app_icon_sets"].append({
                    "base_name": base_name,
                    "app_name": app_name,
                    "platforms": filtered_sets
                })

        # Color variants
        if color_variants:
            color_schemes = request.form.getlist("color_schemes")
            primary_color = request.form.get("primary_color", "#0ea5e9")
            secondary_color = request.form.get("secondary_color", "#64748b")
            
            color_map = {}
            if "light_dark" in color_schemes:
                color_map.update({
                    "light": {"#000000": "#ffffff", "#000": "#fff"},
                    "dark": {"#ffffff": "#000000", "#fff": "#000"}
                })
            
            if "brand_colors" in color_schemes:
                color_map.update({
                    "primary": {"#0ea5e9": primary_color},
                    "secondary": {"#64748b": secondary_color}
                })
            
            if color_map:
                variants = generate_color_variants(svg_content, color_map)
                
                # Save color variants
                variant_dir = svg_out_dir / "color_variants"
                variant_dir.mkdir(exist_ok=True)
                
                variant_files = []
                for scheme_name, variant_svg in variants.items():
                    variant_filename = f"{base_name}_{scheme_name}.svg"
                    variant_path = variant_dir / variant_filename
                    with open(variant_path, 'w', encoding='utf-8') as f:
                        f.write(variant_svg)
                    
                    variant_files.append({
                        "filename": variant_filename,
                        "scheme": scheme_name,
                        "path": str(variant_path)
                    })
                
                results["color_variant_sets"].append({
                    "base_name": base_name,
                    "variants": variant_files
                })

    # ZIP download option
    if request.form.get("zip") == "on":
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            # Add all generated files to ZIP
            for root, dirs, files in os.walk(svg_out_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(svg_out_dir)
                    z.write(file_path, arcname=str(arcname))
        
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="svg_processed.zip", mimetype="application/zip")

    # Return results
    return render_template("index.html", 
                         active_tab="svg",
                         responsive_sizes=RESPONSIVE_SIZES,
                         thumbnail_sizes=THUMBNAIL_SIZES,
                         crop_methods=CROP_METHODS,
                         favicon_sizes=FAVICON_SIZES,
                         favicon_specs=FAVICON_SPECS,
                         optimization_presets=OPTIMIZATION_PRESETS,
                         web_formats=WEB_FORMATS,
                         done=True,
                         svg_results=results,
                         svg_output_dir=str(svg_out_dir))

if __name__ == "__main__":
    # kör lokalt
    app.run(debug=True)
