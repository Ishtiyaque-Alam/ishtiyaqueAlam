import networkx as nx
from pyvis.network import Network
from typing import Dict, Any, List, Optional
import os


class GraphVisualizer:
    def __init__(self):
        self.net = None
    
    def create_interactive_graph(self, 
                                graph: nx.DiGraph, 
                                output_path: str = "graph.html",
                                width: str = "100%",
                                height: str = "800px") -> str:
        """Create an interactive HTML visualization of the dependency graph"""
        
        # Create pyvis network
        self.net = Network(
            height=height,
            width=width,
            bgcolor="#222222",
            font_color="white",
            directed=True
        )
        
        # Configure physics
        self.net.set_options("""
        {
            "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100},
                "barnesHut": {
                    "gravitationalConstant": -2000,
                    "centralGravity": 0.1,
                    "springLength": 200,
                    "springConstant": 0.05,
                    "damping": 0.09
                }
            }
        }
        """)
        
        # Add nodes
        for node in graph.nodes():
            self._add_node(node, graph.nodes[node])
        
        # Add edges
        for edge in graph.edges():
            self._add_edge(edge[0], edge[1])
        
        # Save the graph
        self.net.save_graph(output_path)
        return output_path
    
    def _add_node(self, node_id: str, node_data: Dict[str, Any]):
        """Add a node to the visualization"""
        # Extract function name and file from node_id
        parts = node_id.split('::')
        if len(parts) >= 2:
            file_path = parts[0]
            function_name = parts[-1]
            class_name = parts[1] if len(parts) > 2 else ''
            
            # Create display name
            file_name = os.path.basename(file_path)
            if class_name:
                display_name = f"{file_name}\n{class_name}.{function_name}"
            else:
                display_name = f"{file_name}\n{function_name}"
        else:
            display_name = node_id
        
        # Get issue information
        total_issues = node_data.get('total_issues', 0)
        issues_by_category = node_data.get('issues_by_category', {})
        severity_distribution = node_data.get('severity_distribution', {})
        
        # Determine node color based on issue severity
        color = self._get_node_color(severity_distribution)
        
        # Create tooltip
        tooltip = self._create_function_tooltip(node_id, total_issues, issues_by_category, severity_distribution, node_data)
        
        # Determine node size based on total issues and function length
        function_length = node_data.get('function_length', 0)
        size = max(15, min(40, 15 + total_issues + function_length // 10))
        
        # Add node
        self.net.add_node(
            node_id,
            label=display_name,
            title=tooltip,
            color=color,
            size=size,
            font={"size": 10}
        )
    
    def _add_edge(self, source: str, target: str):
        """Add an edge to the visualization"""
        self.net.add_edge(source, target, color="#666666", width=2)
    
    def _get_node_color(self, severity_distribution: Dict[str, int]) -> str:
        """Determine node color based on issue severity"""
        high_count = severity_distribution.get('High', 0)
        medium_count = severity_distribution.get('Medium', 0)
        low_count = severity_distribution.get('Low', 0)
        
        if high_count > 0:
            return "#ff4444"  # Red for high severity
        elif medium_count > 0:
            return "#ffaa00"  # Orange for medium severity
        elif low_count > 0:
            return "#ffff00"  # Yellow for low severity
        else:
            return "#44ff44"  # Green for no issues
    
    def _create_function_tooltip(self, 
                                node_id: str, 
                                total_issues: int, 
                                issues_by_category: Dict[str, int],
                                severity_distribution: Dict[str, int],
                                node_data: Dict[str, Any]) -> str:
        """Create tooltip text for a function node"""
        # Extract function info
        parts = node_id.split('::')
        file_path = parts[0] if parts else node_id
        function_name = parts[-1] if len(parts) > 1 else node_id
        class_name = parts[1] if len(parts) > 2 else ''
        
        file_name = os.path.basename(file_path)
        
        tooltip = f"<b>{file_name}</b><br>"
        if class_name:
            tooltip += f"<b>Class:</b> {class_name}<br>"
        tooltip += f"<b>Function:</b> {function_name}<br>"
        tooltip += f"<b>Total Issues:</b> {total_issues}<br>"
        
        # Add function metrics
        function_length = node_data.get('function_length', 0)
        nesting_depth = node_data.get('nesting_depth', 0)
        has_docstring = node_data.get('has_docstring', False)
        
        tooltip += f"<b>Length:</b> {function_length} lines<br>"
        tooltip += f"<b>Nesting Depth:</b> {nesting_depth}<br>"
        tooltip += f"<b>Has Docstring:</b> {'Yes' if has_docstring else 'No'}<br><br>"
        
        if issues_by_category:
            tooltip += "<b>Issues by Category:</b><br>"
            for category, count in issues_by_category.items():
                tooltip += f"• {category}: {count}<br>"
        
        if severity_distribution:
            tooltip += "<br><b>Issues by Severity:</b><br>"
            for severity, count in severity_distribution.items():
                color = self._get_severity_color(severity)
                tooltip += f"• <span style='color:{color}'>{severity}</span>: {count}<br>"
        
        return tooltip
    
    def _create_tooltip(self, 
                       file_name: str, 
                       total_issues: int, 
                       issues_by_category: Dict[str, int],
                       severity_distribution: Dict[str, int]) -> str:
        """Create tooltip text for a file node (legacy)"""
        tooltip = f"<b>{file_name}</b><br>"
        tooltip += f"Total Issues: {total_issues}<br><br>"
        
        if issues_by_category:
            tooltip += "<b>Issues by Category:</b><br>"
            for category, count in issues_by_category.items():
                tooltip += f"• {category}: {count}<br>"
        
        if severity_distribution:
            tooltip += "<br><b>Issues by Severity:</b><br>"
            for severity, count in severity_distribution.items():
                color = self._get_severity_color(severity)
                tooltip += f"• <span style='color:{color}'>{severity}</span>: {count}<br>"
        
        return tooltip
    
    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level"""
        colors = {
            'High': '#ff4444',
            'Medium': '#ffaa00',
            'Low': '#ffff00'
        }
        return colors.get(severity, '#ffffff')
    
    def create_summary_report(self, 
                            graph: nx.DiGraph, 
                            output_path: str = "summary_report.html") -> str:
        """Create a summary report of the analysis"""
        
        # Calculate statistics
        total_files = graph.number_of_nodes()
        total_edges = graph.number_of_edges()
        
        # Count issues
        total_issues = 0
        issues_by_category = {}
        issues_by_severity = {}
        
        for node in graph.nodes():
            node_data = graph.nodes[node]
            total_issues += node_data.get('total_issues', 0)
            
            # Aggregate category counts
            for category, count in node_data.get('issues_by_category', {}).items():
                issues_by_category[category] = issues_by_category.get(category, 0) + count
            
            # Aggregate severity counts
            for severity, count in node_data.get('severity_distribution', {}).items():
                issues_by_severity[severity] = issues_by_severity.get(severity, 0) + count
        
        # Create HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Analysis Summary Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; text-align: center; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
                .stat-card {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .stat-label {{ color: #666; margin-top: 5px; }}
                .section {{ margin: 30px 0; }}
                .issue-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .issue-item {{ margin: 10px 0; padding: 10px; background-color: white; border-radius: 5px; border-left: 4px solid #007bff; }}
                .high {{ border-left-color: #dc3545; }}
                .medium {{ border-left-color: #ffc107; }}
                .low {{ border-left-color: #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Code Analysis Summary Report</h1>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_files}</div>
                        <div class="stat-label">Files Analyzed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_edges}</div>
                        <div class="stat-label">Dependencies</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_issues}</div>
                        <div class="stat-label">Total Issues</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Issues by Category</h2>
                    <div class="issue-list">
        """
        
        for category, count in issues_by_category.items():
            html_content += f'<div class="issue-item">{category}: {count} issues</div>'
        
        html_content += """
                    </div>
                </div>
                
                <div class="section">
                    <h2>Issues by Severity</h2>
                    <div class="issue-list">
        """
        
        for severity, count in issues_by_severity.items():
            severity_class = severity.lower()
            html_content += f'<div class="issue-item {severity_class}">{severity}: {count} issues</div>'
        
        html_content += """
                    </div>
                </div>
                
                <div class="section">
                    <h2>Files with Most Issues</h2>
                    <div class="issue-list">
        """
        
        # Sort files by issue count
        files_with_issues = [(node, graph.nodes[node].get('total_issues', 0)) for node in graph.nodes()]
        files_with_issues.sort(key=lambda x: x[1], reverse=True)
        
        for file_path, issue_count in files_with_issues[:10]:  # Top 10
            if issue_count > 0:
                file_name = os.path.basename(file_path)
                html_content += f'<div class="issue-item">{file_name}: {issue_count} issues</div>'
        
        html_content += """
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
