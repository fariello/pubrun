"""
Main Textual Application for the Pubrun TUI Manager.
"""

from __future__ import annotations
import os
from typing import Any, Optional, Set

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static, TabbedContent, TabPane, Tree

from pubrun.status import RunInfo
from .widgets.sidebar import RunsSidebar
from .widgets.details import RunDetailsView
from .widgets.viewer import LogViewer
from .widgets.diff import DiffView
from .widgets.actions import ActionsPanel
from .widgets.config import ConfigPanel
from .widgets.resources import RunResourcesView


_LAZY_RUN_TABS = frozenset({"tab-details", "tab-logs", "tab-resources", "tab-actions"})


class KeybindHelpModal(ModalScreen[None]):
    """Modal listing available TUI keyboard shortcuts."""

    BINDINGS = [Binding("escape", "dismiss_help", "Close", show=False)]

    def compose(self) -> ComposeResult:
        help_text = "\n".join(
            [
                "  1 - 6     Switch workspace tabs (Details, Logs, Resources, Diff, Actions, Config)",
                "  r         Jump to the Resources tab",
                "  /         Focus the sidebar run search box",
                "  ?         Show this keyboard shortcuts help dialog",
                "  Ctrl+S    Toggle the runs sidebar",
                "  Ctrl+R    Refresh runs list and diff dropdowns from disk",
                "  Ctrl+Q    Quit Pubrun TUI Manager",
                "  Esc       Close this dialog",
            ]
        )
        yield Vertical(
            Label("KEYBOARD SHORTCUTS", id="dialog-title"),
            Static(help_text, id="dialog-message"),
            Horizontal(
                Button("Close", id="btn-close-help", variant="primary"),
                classes="horizontal-buttons",
            ),
            id="dialog-container",
        )

    def action_dismiss_help(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-help":
            self.dismiss(None)


class PubrunTUIApp(App):
    """The main interactive TUI manager application for pubrun."""

    # Dynamic CSS loading
    CSS_PATH = os.path.join(os.path.dirname(__file__), "css", "style.css")

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+s", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+r", "refresh_all", "Refresh Data", show=True),
        Binding("r", "show_resources", "Resources", show=True, priority=False),
        Binding("1", "show_tab('tab-details')", "Details", show=False, priority=False),
        Binding("2", "show_tab('tab-logs')", "Logs", show=False, priority=False),
        Binding("3", "show_tab('tab-resources')", "Resources Tab", show=False, priority=False),
        Binding("4", "show_tab('tab-diff')", "Diff", show=False, priority=False),
        Binding("5", "show_tab('tab-actions')", "Actions", show=False, priority=False),
        Binding("6", "show_tab('tab-config')", "Config", show=False, priority=False),
        Binding("/", "focus_search", "Search", show=True, priority=False),
        Binding("?", "show_help", "Help", show=True, priority=False),
    ]

    class RefreshSidebar(Message):
        """Custom message to request refreshing of runs sidebar list."""
        pass

    def __init__(self, output_dir: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir
        self._explicit_output_dir = output_dir is not None
        self.selected_run_info: Optional[RunInfo] = None
        self._dirty_tabs: Set[str] = set()

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

                    # Tab 3: Resource usage (CPU / memory over the run)
                    with TabPane("Resources", id="tab-resources"):
                        yield RunResourcesView(id="resources-view")

                    # Tab 4: Semantic Diff
                    with TabPane("Semantic Diff", id="tab-diff"):
                        yield DiffView(output_dir=self.output_dir, id="diff-view")

                    # Tab 5: Actions & Citations
                    with TabPane("Actions & Citations", id="tab-actions"):
                        yield ActionsPanel(output_dir=self.output_dir, id="actions-view")

                    # Tab 6: Project Config (.pubrun.toml)
                    with TabPane("Project Config", id="tab-config"):
                        yield ConfigPanel(id="config-view")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Pubrun TUI Manager"
        sidebar = self.query_one("#sidebar", RunsSidebar)
        self.query_one("#diff-view", DiffView).populate_dropdowns(sidebar.all_runs)

        if sidebar.all_runs:
            self._select_run(sidebar.all_runs[0])
        else:
            self.query_one("#details-view", RunDetailsView).show_onboarding()

        # Place initial focus on the runs tree rather than #runs-search so arrow navigation
        # and non-priority 1-6 / r / / / ? bindings work immediately on launch.
        try:
            self.query_one("#runs-tree", Tree).focus()
        except Exception:
            pass

    def _select_run(self, run_info: RunInfo) -> None:
        """Record the selected run, mark run-dependent tabs dirty, and render only the active tab."""
        self.selected_run_info = run_info
        self._dirty_tabs = set(_LAZY_RUN_TABS)
        active_tab = self.query_one("#workspace-tabs", TabbedContent).active
        if active_tab in self._dirty_tabs:
            self._render_tab(active_tab)

    def _render_tab(self, tab_id: str) -> None:
        """Render a single lazy run-dependent tab if it is marked dirty."""
        if tab_id not in self._dirty_tabs or self.selected_run_info is None:
            return
        self._dirty_tabs.discard(tab_id)
        r_info = self.selected_run_info

        if tab_id == "tab-details":
            self.query_one("#details-view", RunDetailsView).display_run(r_info)
        elif tab_id == "tab-logs":
            self.query_one("#logs-view", LogViewer).display_run_logs(r_info.run_dir)
        elif tab_id == "tab-resources":
            self.query_one("#resources-view", RunResourcesView).display_run(r_info)
        elif tab_id == "tab-actions":
            self.query_one("#actions-view", ActionsPanel).display_run(r_info)

    def update_output_dir(self, new_output_dir: Optional[str]) -> None:
        """Update workspace widgets to track a newly configured output directory."""
        self.output_dir = new_output_dir
        self.query_one("#sidebar", RunsSidebar).output_dir = new_output_dir
        self.query_one("#diff-view", DiffView).output_dir = new_output_dir
        self.query_one("#actions-view", ActionsPanel).output_dir = new_output_dir

    def action_toggle_sidebar(self) -> None:
        """Toggle the visibility of the sidebar navigation widget."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_show_tab(self, tab_id: str) -> None:
        """Switch the main workspace to ``tab_id``."""
        try:
            tabs = self.query_one("#workspace-tabs", TabbedContent)
            tabs.active = tab_id
            self._render_tab(tab_id)
        except Exception:
            pass

    def action_show_resources(self) -> None:
        """Jump to the Resources tab (CPU / memory usage) for the selected run."""
        self.action_show_tab("tab-resources")

    def action_focus_search(self) -> None:
        """Ensure the sidebar is visible and focus the run search input."""
        try:
            sidebar = self.query_one("#sidebar")
            sidebar.display = True
            self.query_one("#runs-search", Input).focus()
        except Exception:
            pass

    def action_show_help(self) -> None:
        """Open the keybind help modal."""
        self.push_screen(KeybindHelpModal())

    def action_refresh_all(self) -> None:
        """Refresh the sidebar runs list, diff dropdowns, and active run view."""
        sidebar = self.query_one("#sidebar", RunsSidebar)
        sidebar.load_runs()

        diff_view = self.query_one("#diff-view", DiffView)
        diff_view.populate_dropdowns(sidebar.all_runs)

        if sidebar.all_runs:
            prev_dir = self.selected_run_info.run_dir if self.selected_run_info else None
            matched = next((r for r in sidebar.all_runs if r.run_dir == prev_dir), None)
            self._select_run(matched or sidebar.all_runs[0])
        else:
            self.selected_run_info = None
            self._dirty_tabs.clear()
            self.query_one("#details-view", RunDetailsView).show_onboarding()

        self.notify("Runs database and cache refreshed.", severity="information")

    @on(RefreshSidebar)
    def on_refresh_sidebar(self, event: RefreshSidebar) -> None:
        """Handle custom RefreshSidebar messages sent from widgets."""
        self.action_refresh_all()

    @on(TabbedContent.TabActivated)
    def on_workspace_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Lazily render a workspace tab when the user activates it."""
        if event.tabbed_content.id == "workspace-tabs":
            self._render_tab(event.tabbed_content.active)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle selection events in the runs tree navigation."""
        node_data = event.node.data
        if node_data and node_data.get("type") == "run":
            r_info = node_data.get("run_info")
            if isinstance(r_info, RunInfo):
                self._select_run(r_info)
