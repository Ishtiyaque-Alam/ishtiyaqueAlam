import click
import json
from pathlib import Path
from src.pipeline.analyzer import CodeAnalyzer
from dotenv import load_dotenv

load_dotenv()

@click.group()
def main():
    """Code Analysis Pipeline with Vector Search"""
    pass


@main.command()
@click.argument('target_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='./analysis_output', 
              help='Output directory for analysis results')
def analyze(target_path, output_dir):
    """Analyze code and generate reports"""
    analyzer = CodeAnalyzer(output_dir)
    
    try:
        # Run analysis
        summary = analyzer.analyze(target_path)
        
        # Print summary
        click.echo("\n" + "="*50)
        click.echo("ANALYSIS SUMMARY")
        click.echo("="*50)
        click.echo(f"Files analyzed: {summary['files_analyzed']}")
        click.echo(f"Functions found: {summary['total_functions']}")
        click.echo(f"Total issues: {summary['total_issues']}")
        click.echo(f"Dependencies: {summary['dependencies']}")
        
        click.echo("\nIssues by category:")
        for category, count in summary['issues_by_category'].items():
            click.echo(f"  {category}: {count}")
        
        click.echo("\nIssues by severity:")
        for severity, count in summary['issues_by_severity'].items():
            click.echo(f"  {severity}: {count}")
        
        click.echo(f"\nResults saved to: {output_dir}")
        click.echo(f"Interactive graph: {output_dir}/graph.html")
        click.echo(f"Summary report: {output_dir}/summary_report.html")
    
    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        raise click.Abort()




if __name__ == '__main__':
    main()
