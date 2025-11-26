"""
TNM Staging Prediction System - Main Application

This is the main entry point for the TNM staging prediction system.
It provides a CLI interface for processing PET-CT PDF reports.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from dotenv import load_dotenv
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
except ImportError:
    print("Error: Required packages not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

from pdf_to_markdown import MarkdownConverter, pdf_to_markdown_text
from workflow import run_tnm_staging_workflow

# Initialize Rich console
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


def generate_markdown_report(staging_result: dict, report_id: Optional[str] = None) -> str:
    """Generate a human-readable markdown report from staging results.
    
    Args:
        staging_result: TNM staging result dictionary
        report_id: Optional report identifier
        
    Returns:
        Formatted markdown report
    """
    staging = staging_result.get("staging", {})
    
    report_lines = [
        "# TNM Staging Report",
        "",
        f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    
    if report_id:
        report_lines.append(f"**Report ID:** {report_id}")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## Final Staging",
        "",
        f"**TNM Stage:** `{staging.get('tnm_stage', 'N/A')}`  ",
        f"**Overall Stage:** `{staging.get('overall_stage', 'N/A')}`  ",
        f"**Prefix:** `{staging.get('clinical_stage_prefix', 'c')}`TNM",
        "",
        "### Summary",
        "",
        staging.get('summary', 'No summary available'),
        "",
        "---",
        "",
        "## Component Details",
        "",
        "### T-Stage (Tumor)"
    ])
    
    tumor = staging.get('tumor', {})
    report_lines.extend([
        "",
        f"**Stage:** {tumor.get('stage', 'N/A')}  ",
        f"**Size:** {tumor.get('tumor_size_mm', 'N/A')} mm  " if tumor.get('tumor_size_mm') else "",
        f"**Location:** {tumor.get('location', 'N/A')}  ",
        f"**Laterality:** {tumor.get('laterality', 'N/A')}  ",
        f"**Confidence:** {tumor.get('confidence', 'N/A')}",
        "",
        "**Invasion:**"
    ])
    
    invasion = tumor.get('invasion', [])
    if invasion:
        for inv in invasion:
            report_lines.append(f"- {inv}")
    else:
        report_lines.append("- None identified")
    
    report_lines.extend([
        "",
        "**Separate Nodules:**"
    ])
    
    nodules = tumor.get('separate_nodules', [])
    if nodules:
        for nodule in nodules:
            report_lines.append(f"- {nodule}")
    else:
        report_lines.append("- None identified")
    
    report_lines.extend([
        "",
        "**Evidence:**",
        "",
        f"> {tumor.get('evidence', 'No evidence provided')}",
        "",
        "### N-Stage (Lymph Nodes)",
        ""
    ])
    
    nodes = staging.get('nodes', {})
    report_lines.extend([
        f"**Stage:** {nodes.get('stage', 'N/A')}  ",
        f"**Confidence:** {nodes.get('confidence', 'N/A')}",
        "",
        "**Involved Nodes:**"
    ])
    
    involved_nodes = nodes.get('involved_nodes', [])
    if involved_nodes:
        for node in involved_nodes:
            report_lines.append(f"- Station {node.get('station', 'N/A')} ({node.get('laterality', 'N/A')}): {node.get('description', '')}")
    else:
        report_lines.append("- No pathologic nodes identified")
    
    report_lines.extend([
        "",
        "**Evidence:**",
        "",
        f"> {nodes.get('evidence', 'No evidence provided')}",
        "",
        "### M-Stage (Metastasis)",
        ""
    ])
    
    metastasis = staging.get('metastasis', {})
    report_lines.extend([
        f"**Stage:** {metastasis.get('stage', 'N/A')}  ",
        f"**Organ Systems Involved:** {metastasis.get('organ_systems_count', 0)}  ",
        f"**Confidence:** {metastasis.get('confidence', 'N/A')}",
        "",
        "**Metastatic Sites:**"
    ])
    
    met_sites = metastasis.get('metastasis_sites', [])
    if met_sites:
        for site in met_sites:
            report_lines.append(f"- {site.get('organ_system', 'N/A')}: {site.get('location', '')} - {site.get('description', '')}")
    else:
        report_lines.append("- No distant metastases identified")
    
    report_lines.extend([
        "",
        "**Evidence:**",
        "",
        f"> {metastasis.get('evidence', 'No evidence provided')}",
        "",
        "---",
        "",
        "*Report generated by TNM Staging AI System using TNM 9th Edition guidelines*"
    ])
    
    return "\n".join(report_lines)


def process_pdf_report(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    save_json: bool = True,
    save_markdown: bool = True
) -> dict:
    """Process a PDF report and generate TNM staging.
    
    Args:
        pdf_path: Path to input PDF file
        output_dir: Directory for output files (default: same as PDF)
        save_json: Save JSON output
        save_markdown: Save markdown report
        
    Returns:
        Staging result dictionary
    """
    if output_dir is None:
        output_dir = pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = pdf_path.stem
    report_id = base_name
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Step 1: Convert PDF to Markdown
        task = progress.add_task("[cyan]Converting PDF to markdown...", total=None)
        
        try:
            load_dotenv()
            import os
            api_key = os.environ.get('MISTRAL_API_KEY')
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not found in environment")
            
            converter = MarkdownConverter(api_key=api_key)
            markdown_text = pdf_to_markdown_text(str(pdf_path), converter, with_images=False)
            
            # Save intermediate markdown
            md_path = output_dir / f"{base_name}_report.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            progress.update(task, description="[green]✓ PDF converted to markdown")
            
        except Exception as e:
            progress.update(task, description="[red]✗ PDF conversion failed")
            console.print(f"[red]Error converting PDF: {e}")
            raise
        
        # Step 2: Run TNM Staging Workflow
        task = progress.add_task("[cyan]Running TNM staging analysis...", total=None)
        
        try:
            result = run_tnm_staging_workflow(
                report_text=markdown_text,
                report_id=report_id
            )
            
            if not result.get("success"):
                progress.update(task, description="[red]✗ Staging analysis failed")
                error_msg = result.get("error", "Unknown error")
                console.print(f"[red]Staging failed: {error_msg}")
                return result
            
            progress.update(task, description="[green]✓ TNM staging completed")
            
        except Exception as e:
            progress.update(task, description="[red]✗ Staging analysis failed")
            console.print(f"[red]Error during staging: {e}")
            raise
    
    # Step 3: Save outputs
    if save_json:
        json_path = output_dir / f"{base_name}_staging.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]✓ Saved JSON output: {json_path}")
    
    if save_markdown:
        md_report_path = output_dir / f"{base_name}_staging_report.md"
        md_report = generate_markdown_report(result, report_id)
        with open(md_report_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        console.print(f"[green]✓ Saved markdown report: {md_report_path}")
    
    # Display summary
    staging = result.get("staging", {})
    summary_panel = Panel(
        f"[bold]TNM Stage:[/bold] {staging.get('tnm_stage', 'N/A')}\n"
        f"[bold]Overall Stage:[/bold] {staging.get('overall_stage', 'N/A')}\n\n"
        f"{staging.get('summary', 'No summary available')}",
        title="[bold green]Staging Result",
        border_style="green"
    )
    console.print(summary_panel)
    
    return result


def main():
    """Main entry point for CLI application."""
    parser = argparse.ArgumentParser(
        description="TNM Staging Prediction System for Lung Cancer PET-CT Reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input report.pdf
  %(prog)s --input report.pdf --output ./results
  %(prog)s --input report.pdf --no-json
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        type=Path,
        help='Path to input PDF report'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=None,
        help='Output directory (default: same as input PDF)'
    )
    
    parser.add_argument(
        '--no-json',
        action='store_true',
        help='Do not save JSON output'
    )
    
    parser.add_argument(
        '--no-markdown',
        action='store_true',
        help='Do not save markdown report'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input
    if not args.input.exists():
        console.print(f"[red]Error: Input file not found: {args.input}")
        sys.exit(1)
    
    if not args.input.suffix.lower() == '.pdf':
        console.print(f"[red]Error: Input file must be a PDF")
        sys.exit(1)
    
    # Process the report
    try:
        console.print(Panel(
            f"[bold]Input:[/bold] {args.input}\n"
            f"[bold]Output:[/bold] {args.output or args.input.parent}",
            title="[bold blue]TNM Staging System",
            border_style="blue"
        ))
        
        result = process_pdf_report(
            pdf_path=args.input,
            output_dir=args.output,
            save_json=not args.no_json,
            save_markdown=not args.no_markdown
        )
        
        if result.get("success"):
            console.print("\n[bold green]✓ Processing completed successfully!")
            sys.exit(0)
        else:
            console.print("\n[bold red]✗ Processing failed")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"\n[bold red]✗ Unexpected error: {e}")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
