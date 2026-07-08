"""
Main Textual Application for the Pubrun TUI Manager.
"""

from __future__ import annotations
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, TabbedContent, TabPane, Tree
from textual.message import Message
from textual.binding import Binding

from .widgets.sidebar import RunsSidebar
from .widgets.details import RunDetailsView
from .widgets.viewer import LogViewer
from .widgets.diff import DiffView
from .widgets.actions import ActionsPanel
from .widgets.config import ConfigPanel
from .widgets.resources import RunResourcesView

class PubrunTUIApp(App):
    """The main interactive TUI manager application for pubrun."""

    # Dynamic CSS loading
    CSS_PATH = os.path.join(os.path.dirname(__file__), "css", "style.css")

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+s", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+r", "refresh_all", "Refresh Data", show=True),
        Binding("r", "show_resources", "Resources", show=True),
    ]

    class RefreshSidebar(Message):
        """Custom message to request refreshing of runs sidebar list."""
        pass

    def __init__(self, output_dir: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir
        self.selected_run_info = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RunsSidebar(output_dir=self.output_dir, id="sidebar")
            with Container(id="workspace"):
                with TabbedContent(id="workspace-tabs"):
                    # Tab 1: Run Details
                    with TabPane("Run Details", id="tab-details"):
                        yield RunDetailsView(id="details-view")
                    
                    # Tab 2: Console Logs
                    with TabPane("Console Logs", id="tab-logs"):
                        yield LogViewer(id="logs-view")

                    # Tab: Resource usage (CPU / memory over the run)
                    with TabPane("Resources", id="tab-resources"):
                        yield RunResourcesView(id="resources-view")
                    
                    # Tab 3: Semantic Diff
                    with TabPane("Semantic Diff", id="tab-diff"):
                        yield DiffView(output_dir=self.output_dir, id="diff-view")
                    
                    # Tab 4: Actions & Citations
                    with TabPane("Actions & Citations", id="tab-actions"):
                        yield ActionsPanel(output_dir=self.output_dir, id="actions-view")
                    
                    # Tab 5: Configuration Settings
                    with TabPane("TUI Settings", id="tab-config"):
                        yield ConfigPanel(id="config-view")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Pubrun TUI Manager"
        # Initial population of diff dropdowns
        sidebar = self.query_one("#sidebar", RunsSidebar)
        self.query_one("#diff-view", DiffView).populate_dropdowns(sidebar.all_runs)

    def action_toggle_sidebar(self) -> None:
        """Toggle the visibility of the sidebar navigation widget."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_show_resources(self) -> None:
        """Jump to the Resources tab (CPU / memory usage) for the selected run."""
        try:
            self.query_one("#workspace-tabs", TabbedContent).active = "tab-resources"
        except Exception:
            pass

    def action_refresh_all(self) -> None:
        """Refresh the sidebar runs list and diff dropdown options."""
        sidebar = self.query_one("#sidebar", RunsSidebar)
        sidebar.load_runs()
        
        diff_view = self.query_one("#diff-view", DiffView)
        diff_view.populate_dropdowns(sidebar.all_runs)
        
        self.notify("Runs database and cache refreshed.", severity="information")

    def on_refresh_sidebar(self, event: RefreshSidebar) -> None:
        """Handle custom RefreshSidebar messages sent from widgets."""
        self.action_refresh_all()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle selection events in the runs tree navigation."""
        node_data = event.node.data
        if node_data and node_data.get("type") == "run":
            r_info = node_data.get("run_info")
            self.selected_run_info = r_info

            # Update details pane
            self.query_one("#details-view", RunDetailsView).display_run(r_info)
            
            # Update log viewer pane
            self.query_one("#logs-view", LogViewer).display_run_logs(r_info.run_dir)

            # Update resources pane (CPU / memory usage)
            self.query_one("#resources-view", RunResourcesView).display_run(r_info)

            # Update actions pane
            self.query_one("#actions-view", ActionsPanel).display_run(r_info)
