# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import inspect
import logging
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path


import carb
import omni.ext
import omni.kit.app
import omni.kit.commands
import omni.kit.menu.utils
import omni.kit.stage_templates as stage_templates
import omni.kit.ui
import omni.kit.window.property as property_window_ext
import omni.ui as ui
import omni.usd
from omni.kit.menu.utils import MenuLayout, MenuItemDescription
from omni.kit.property.usd import PrimPathWidget
from omni.kit.quicklayout import QuickLayout
from omni.kit.window.title import get_main_window_title

# Import Vision Digital Twin bootstrap system
try:
    # Add bootstrap directory to path
    # Path to bootstrap is 7 levels up from this file location
    # extension.py -> my_usd_composer_setup_extension -> my_company -> my_usd_composer_setup_extension -> extensions -> source -> kit-app-template -> bootstrap
    bootstrap_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "bootstrap"
    if bootstrap_path.exists() and str(bootstrap_path) not in sys.path:
        sys.path.insert(0, str(bootstrap_path))

    # Try to import the loader module directly
    # Since 'bootstrap' is in sys.path, we can import 'loader' directly if it's in the bootstrap root
    # OR we can import it as 'bootstrap.loader' if we added the parent of bootstrap to path.
    # Given the current structure, 'loader.py' is directly inside 'bootstrap'.
    # So if we add 'bootstrap' folder to sys.path, we import via 'import loader'

    import loader
    from loader import BootstrapLoader
    BOOTSTRAP_AVAILABLE = True
except ImportError as e:
    # Fallback: Try appending paths relative to the extension root if the relative path above failed
    try:
        # Alternative path calculation
        current_dir = Path(__file__).parent
        # Traverse up to find 'kit-app-template' root
        # extension.py (0) -> my_usd_composer_setup_extension (1) -> my_company (2) -> my_usd_composer_setup_extension (3) -> extensions (4) -> source (5) -> kit-app-template (6)
        repo_root = current_dir.parents[5]
        bootstrap_path = repo_root / "bootstrap"

        if bootstrap_path.exists() and str(bootstrap_path) not in sys.path:
             sys.path.insert(0, str(bootstrap_path))

        import loader
        from loader import BootstrapLoader
        BOOTSTRAP_AVAILABLE = True
        logging.info(f"Vision DT Bootstrap initialized via fallback path: {bootstrap_path}")

    except ImportError as e2:
        # Final Fallback: Try using the absolute path from the known project structure if dynamic relative paths fail
        # This is a hardcoded fallback for the specific environment G:/Vision_Example_1/kit-app-template
        try:
             # Hardcoded path based on user's workspace
             hardcoded_bootstrap = Path("G:/Vision_Example_1/kit-app-template/bootstrap")
             if hardcoded_bootstrap.exists() and str(hardcoded_bootstrap) not in sys.path:
                 sys.path.insert(0, str(hardcoded_bootstrap))

             import loader
             from loader import BootstrapLoader
             BOOTSTRAP_AVAILABLE = True
             logging.info(f"Vision DT Bootstrap initialized via ABSOLUTE fallback path: {hardcoded_bootstrap}")
        except ImportError as e3:
             logging.warning(f"Vision DT Bootstrap system not available (All methods failed): {e} | {e2} | {e3}")
             BOOTSTRAP_AVAILABLE = False

DATA_PATH = Path(carb.tokens.get_tokens_interface().resolve(
    "${my_company.my_usd_composer_setup_extension}")
)


async def _load_layout(layout_file: str, keep_windows_open=False):
    """Loads a provided layout file and ensures the viewport is set to FILL."""
    try:
        # few frames delay to avoid the conflict with the
        # layout of omni.kit.mainwindow
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        QuickLayout.load_file(layout_file, keep_windows_open)
    except:
        QuickLayout.load_file(layout_file)


class CreateSetupExtension(omni.ext.IExt):
    """Create Final Configuration"""
    def on_startup(self, _ext_id):
        """
        setup the window layout, menu, final configuration
        of the extensions etc
        """
        self._settings = carb.settings.get_settings()
        if self._settings and self._settings.get("/app/warmupMode"):
            # if warmup mode is enabled, we don't want to load the stage or
            # layout, just return
            return

        self._menu_layout = []
        self._bootstrap_loader = None
        self._stage_event_subscription = None

        telemetry_logger = logging.getLogger("idl.telemetry.opentelemetry")
        telemetry_logger.setLevel(logging.ERROR)

        # this is a work around as some Extensions don't properly setup their
        # default setting in time
        self._set_defaults()

        # adjust couple of viewport settings
        self._settings.set("/app/viewport/boundingBoxes/enabled", True)

        # These two settings do not co-operate well on ADA cards, so for
        # now simulate a toggle of the present thread on startup to work around
        if self._settings.get("/exts/omni.kit.renderer.core/present/enabled") \
            and self._settings.get(
            "/exts/omni.kit.widget.viewport/autoAttach/mode"
        ):
            async def _toggle_present(settings, n_waits: int = 1):
                async def _toggle_setting(app, enabled: bool, n_waits: int):
                    for _ in range(n_waits):
                        await app.next_update_async()
                    settings.set(
                        "/exts/omni.kit.renderer.core/present/enabled",
                        enabled
                    )

                app = omni.kit.app.get_app()
                await _toggle_setting(app, False, n_waits)
                await _toggle_setting(app, True, n_waits)

            asyncio.ensure_future(_toggle_present(self._settings))

        # Setting and Saving FSD as a global change in preferences
        # Requires to listen for changes at the local path to update
        # Composer's persistent path.
        fabric_app_setting = self._settings.get("/app/useFabricSceneDelegate")
        fabric_persistent_setting = self._settings.get(
            "/persistent/app/useFabricSceneDelegate"
        )
        fabric_enabled: bool = fabric_app_setting if \
            fabric_persistent_setting is None else fabric_persistent_setting

        self._settings.set("/app/useFabricSceneDelegate", fabric_enabled)

        self._sub_fabric_delegate_changed = \
            omni.kit.app.SettingChangeSubscription(
                "/app/useFabricSceneDelegate",
                self._on_fabric_delegate_changed
            )

        # Adjust the Window Title to show the Create Version
        window_title = get_main_window_title()

        app_version = self._settings.get("/app/version")
        if not app_version:
            with open(
                carb.tokens.get_tokens_interface().resolve("${app}/../VERSION"),
                encoding="utf-8"
            ) as f:
                app_version = f.read()

        if app_version:
            if "+" in app_version:
                app_version, _ = app_version.split("+")

            # for RC version we remove some details
            if self._settings.get("/privacy/externalBuild"):
                if "-" in app_version:
                    app_version, _ = app_version.split("-")
                window_title.set_app_version(app_version)
            else:
                window_title.set_app_version(app_version)

        imgui_style_applied = False
        try:
            # using imgui directly to adjust some color and Variable
            import omni.kit.imgui as _imgui
            imgui = _imgui.acquire_imgui()
            if imgui.is_valid():
                imgui.push_style_color(_imgui.StyleColor.ScrollbarGrab, carb.Float4(0.4, 0.4, 0.4, 1))
                imgui.push_style_color(_imgui.StyleColor.ScrollbarGrabHovered, carb.Float4(0.6, 0.6, 0.6, 1))
                imgui.push_style_color(_imgui.StyleColor.ScrollbarGrabActive, carb.Float4(0.8, 0.8, 0.8, 1))
                imgui.push_style_var_float(_imgui.StyleVar.DockSplitterSize, 2)
                imgui_style_applied = True
        except ImportError:
            pass

        if not imgui_style_applied:
            carb.log_error("Style may not be as expected (carb.imgui was not valid)")

        layout_file = f"{DATA_PATH}/layouts/default.json"

        # Setting to hack few things in test run. Ideally we shouldn't need it.
        test_mode = self._settings.get("/app/testMode")

        if not test_mode:
            asyncio.ensure_future(_load_layout(layout_file, True))

        asyncio.ensure_future(self.__property_window())

        self.__menu_update()

        if not test_mode and not \
                self._settings.get("/app/content/emptyStageOnStart"):
            asyncio.ensure_future(self.__new_stage())

        startup_time = \
            omni.kit.app.get_app_interface().get_time_since_start_s()
        self._settings.set(
            "/crashreporter/data/startup_time", f"{startup_time}"
        )

        def show_documentation(*args):
            webbrowser.open(
                "https://docs.omniverse.nvidia.com/composer/latest/index.html"
            )
        self._help_menu_items = [
            MenuItemDescription(
                name="Documentation",
                onclick_fn=show_documentation,
                appear_after=[omni.kit.menu.utils.MenuItemOrder.FIRST]
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._help_menu_items, name="Help")

        # Initialize Vision DT Bootstrap System
        if BOOTSTRAP_AVAILABLE:
            self._initialize_bootstrap()

    def _initialize_bootstrap(self):
        """Initialize the Vision Digital Twin bootstrap system."""
        try:
            # Helper to validate if a directory contains capability files
            def is_valid_capabilities_dir(path: Path) -> bool:
                if not path or not path.exists():
                    return False
                # Check for at least one .py file that isn't __init__.py
                # and doesn't start with _ (unless we want to count disabled ones)
                # Just finding ANY .py file is a good enough heuristic that it's not an empty skeleton dir
                py_files = list(path.glob("*.py"))
                valid_files = [f for f in py_files if f.name != "__init__.py"]
                return len(valid_files) > 0

            # Create bootstrap loader instance
            # Critical Fix: Do NOT use relative paths from __file__ if __file__ is in _build.
            # Instead, use the same robust logic as the import block or default to hardcoded source.

            bootstrap_path = None

            # Method 1: Check relative to current file (works if not built/packaged yet)
            relative_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "bootstrap" / "capabilities"
            if is_valid_capabilities_dir(relative_path):
                bootstrap_path = relative_path
            else:
                logging.warning(f"Vision DT Bootstrap: Relative path {relative_path} found but empty/invalid.")

            # Method 2: Check repo root relative traversal (handles _build offset sometimes)
            if not bootstrap_path:
                 try:
                     # extension.py (0) -> ... -> extensions (4) -> source (5) -> kit-app-template (6)
                     repo_root = Path(__file__).parent.parents[5]
                     candidate = repo_root / "bootstrap" / "capabilities"
                     if is_valid_capabilities_dir(candidate):
                         bootstrap_path = candidate
                     else:
                        logging.warning(f"Vision DT Bootstrap: Repo root path {candidate} found but empty/invalid.")
                 except:
                     pass

            # Method 3: Hardcoded fallback (Most reliable for this specific workspace)
            if not bootstrap_path:
                candidate = Path("G:/Vision_Example_1/kit-app-template/bootstrap/capabilities")
                if is_valid_capabilities_dir(candidate):
                    bootstrap_path = candidate
                else:
                     logging.warning(f"Vision DT Bootstrap: Hardcoded path {candidate} found but empty/invalid.")

            # Final check
            if not bootstrap_path:
                logging.error("Vision DT Bootstrap: Could not find any valid capabilities directory!")
                return

            logging.info(f"Vision DT Bootstrap loading capabilities from: {bootstrap_path}")
            self._bootstrap_loader = loader.BootstrapLoader(bootstrap_path)

            # Subscribe to stage events to run bootstrap when stage opens
            usd_context = omni.usd.get_context()
            events = usd_context.get_stage_event_stream()
            self._stage_event_subscription = events.create_subscription_to_pop(
                self._on_stage_event, name="Vision DT Bootstrap"
            )

            logging.info("Vision DT Bootstrap system initialized")

        except Exception as e:
            logging.error(f"Failed to initialize Vision DT Bootstrap: {e}")

    def _on_stage_event(self, event):
        """Handle stage events and run bootstrap on stage open."""
        try:
            if event.type == int(omni.usd.StageEventType.OPENED):
                # Stage was opened, run bootstrap capabilities
                if self._bootstrap_loader:
                    logging.info("Stage opened - running Vision DT bootstrap capabilities")

                    # Run bootstrap asynchronously to not block the UI
                    asyncio.ensure_future(self._run_bootstrap_async())

        except Exception as e:
            logging.error(f"Error handling stage event for bootstrap: {e}")

    async def _run_bootstrap_async(self):
        """Run bootstrap capabilities asynchronously."""
        try:
            # Wait a few frames for stage to be fully loaded
            for _ in range(5):
                await omni.kit.app.get_app().next_update_async()

            # Get the current stage
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None

            if stage:
                # Run all bootstrap capabilities
                results = self._bootstrap_loader.run_all_capabilities(stage)

                # Display status message
                status_msg = self._bootstrap_loader.get_status_message()
                logging.info(status_msg)

                # Show notification to user
                if results["failed"] == 0:
                    carb.log_info(f"Vision DT: {status_msg}")
                else:
                    carb.log_warn(f"Vision DT: {status_msg}")
            else:
                logging.warning("No stage available for bootstrap")

        except Exception as e:
            logging.error(f"Error running bootstrap capabilities: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def _set_defaults(self):
        """
        This is trying to setup some defaults for extensions to avoid warnings.
        """
        self._settings.set_default("/persistent/app/omniverse/bookmarks", {})
        self._settings.set_default(
            "/persistent/app/stage/timeCodeRange", [0, 100]
        )

        self._settings.set_default(
            "/persistent/audio/context/closeAudioPlayerOnStop",
            False
        )

        self._settings.set_default(
            "/persistent/app/primCreation/PrimCreationWithDefaultXformOps",
            True
        )
        self._settings.set_default(
            "/persistent/app/primCreation/DefaultXformOpType",
            "Scale, Rotate, Translate"
        )
        self._settings.set_default(
            "/persistent/app/primCreation/DefaultRotationOrder",
            "ZYX"
        )
        self._settings.set_default(
            "/persistent/app/primCreation/DefaultXformOpPrecision",
            "Double"
        )

        # omni.kit.property.tagging
        self._settings.set_default(
            "/persistent/exts/omni.kit.property.tagging/showAdvancedTagView",
            False
        )
        self._settings.set_default(
            "/persistent/exts/omni.kit.property.tagging/showHiddenTags",
            False
        )
        self._settings.set_default(
            "/persistent/exts/omni.kit.property.tagging/modifyHiddenTags",
            False
        )

        self._settings.set_default(
            "/rtx/sceneDb/ambientLightIntensity", 0.0
        )  # set default ambientLight intensity to Zero

    def _on_fabric_delegate_changed(
            self, _v: str, event_type: carb.settings.ChangeEventType):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            enabled: bool = self._settings.get_as_bool(
                "/app/useFabricSceneDelegate"
            )
            self._settings.set(
                "/persistent/app/useFabricSceneDelegate", enabled
            )

    async def __new_stage(self):
        """Create a new stage """
        # 5 frame delay to allow Layout
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        if omni.usd.get_context().can_open_stage():
            stage_templates.new_stage(template=None)

    def _launch_app(self, app_id, console=True, custom_args=None):
        """launch another Kit app with the same settings"""
        app_path = carb.tokens.get_tokens_interface().resolve("${app}")
        kit_file_path = os.path.join(app_path, app_id)

        # https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
        # Validate input from command line (detected in static analysis)
        kit_exe = sys.argv[0]
        if not os.path.exists(kit_exe):
            print(f"cannot find executable{kit_exe}")
            return

        launch_args = [kit_exe]
        launch_args += [kit_file_path]
        if custom_args:
            launch_args.extend(custom_args)

        # Pass all exts folders
        exts_folders = self._settings.get("/app/exts/folders")
        if exts_folders:
            for folder in exts_folders:
                launch_args.extend(["--ext-folder", folder])

        kwargs = {"close_fds": False}
        if platform.system().lower() == "windows":
            if console:
                kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE | \
                    subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(launch_args, **kwargs)

    def _show_ui_docs(self):
        """show the omniverse ui documentation as an external Application"""
        self._launch_app("omni.app.uidoc.kit")

    def _show_launcher(self):
        """show the omniverse ui documentation as an external Application"""
        self._launch_app(
            "omni.create.launcher.kit",
            console=False,
            custom_args={"--/app/auto_launch=false"}
        )

    async def __property_window(self):
        """Creates a propety window and sets column sizes."""
        await omni.kit.app.get_app().next_update_async()

        property_window = property_window_ext.get_window()
        property_window.set_scheme_delegate_layout(
            "Create Layout",
            ["basis_curves_prim", "path_prim", "material_prim",
             "xformable_prim", "shade_prim", "camera_prim"],
        )

        # expand width of path_items so "Instancable" doesn't get wrapped
        PrimPathWidget.set_path_item_padding(3.5)

    def __menu_update(self):
        """Update the menu"""
        self._menu_layout = [
            MenuLayout.Menu(
                "Window",
                [
                    MenuLayout.SubMenu(
                        "Animation",
                        [
                            MenuLayout.Item("Timeline"),
                            MenuLayout.Item("Sequencer"),
                            MenuLayout.Item("Curve Editor"),
                            MenuLayout.Item("Retargeting"),
                            MenuLayout.Item("Animation Graph"),
                            MenuLayout.Item("Animation Graph Samples"),
                        ],
                    ),
                    MenuLayout.SubMenu(
                        "Layout",
                        [
                            MenuLayout.Item("Quick Save", remove=True),
                            MenuLayout.Item("Quick Load", remove=True),
                        ],
                    ),
                    MenuLayout.SubMenu(
                        "Browsers",
                        [
                            MenuLayout.Item("Content", source="Window/Content"),
                            MenuLayout.Item("Materials"),
                            MenuLayout.Item("Skies"),
                        ],
                    ),
                    MenuLayout.SubMenu(
                        "Rendering",
                        [
                            MenuLayout.Item("Render Settings"),
                            MenuLayout.Item("Movie Capture"),
                            MenuLayout.Item("MDL Material Graph"),
                            MenuLayout.Item("Tablet XR"),
                        ],
                    ),
                    MenuLayout.SubMenu(
                        "Utilities",
                        [
                            MenuLayout.Item("Console"),
                            MenuLayout.Item("Profiler"),
                            MenuLayout.Item("USD Paths"),
                            MenuLayout.Item("Statistics"),
                            MenuLayout.Item("Activity Progress"),
                            MenuLayout.Item("Actions"),
                            MenuLayout.Item("Asset Validator"),
                        ],
                    ),
                    MenuLayout.Sort(
                        exclude_items=["Extensions"], sort_submenus=True
                    ),
                    MenuLayout.Item("New Viewport Window", remove=True),
                ],
            ),
            MenuLayout.Menu(
                "Layout",
                [
                    MenuLayout.Item("Default", source="Reset Layout"),
                    MenuLayout.Seperator(),
                    MenuLayout.Item(
                        "UI Toggle Visibility",
                        source="Window/UI Toggle Visibility"
                    ),
                    MenuLayout.Item(
                        "Fullscreen Mode", source="Window/Fullscreen Mode"
                    ),
                    MenuLayout.Seperator(),
                    MenuLayout.Item(
                        "Save Layout", source="Window/Layout/Save Layout..."
                    ),
                    MenuLayout.Item(
                        "Load Layout", source="Window/Layout/Load Layout..."
                    ),
                    MenuLayout.Seperator(),
                    MenuLayout.Item(
                        "Quick Save", source="Window/Layout/Quick Save"
                    ),
                    MenuLayout.Item(
                        "Quick Load", source="Window/Layout/Quick Load"
                    ),
                ],
            ),
        ]
        omni.kit.menu.utils.add_layout(self._menu_layout)

        self._layout_menu_items = []

        def add_layout_menu_entry(name, parameter, key):
            """Add a layout menu entry."""
            if inspect.isfunction(parameter):
                menu_dict = omni.kit.menu.utils.build_submenu_dict(
                    [
                        MenuItemDescription(name=f"Layout/{name}",
                                            onclick_fn=lambda: asyncio.ensure_future(parameter()),
                                            hotkey=(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, key)),
                    ]
                )
            else:
                async def _active_layout(layout):
                    await _load_layout(layout)
                    # load layout file again to make sure layout correct
                    await _load_layout(layout)

                menu_dict = omni.kit.menu.utils.build_submenu_dict(
                    [
                        MenuItemDescription(name=f"Layout/{name}",
                                            onclick_fn=lambda: asyncio.ensure_future(_active_layout(f"{DATA_PATH}/layouts/{parameter}.json")),
                                            hotkey=(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, key)),
                    ]
                )

            # add menu
            for group in menu_dict:
                omni.kit.menu.utils.add_menu_items(menu_dict[group], group)

            self._layout_menu_items.append(menu_dict)

        add_layout_menu_entry(
            "Reset Layout", "default", carb.input.KeyboardInput.KEY_1
        )

        # create Quick Load & Quick Save
        async def quick_save():
            QuickLayout.quick_save(None, None)

        async def quick_load():
            QuickLayout.quick_load(None, None)

        add_layout_menu_entry(
            "Quick Save", quick_save, carb.input.KeyboardInput.KEY_7
        )
        add_layout_menu_entry(
            "Quick Load", quick_load, carb.input.KeyboardInput.KEY_8
        )

        # open "Asset Stores" window
        ui.Workspace.show_window("Asset Stores")

    def on_shutdown(self):
        """Clean up the extension"""
        self._sub_fabric_delegate_changed = None

        # Clean up bootstrap subscriptions
        if self._stage_event_subscription:
            self._stage_event_subscription.unsubscribe()
            self._stage_event_subscription = None

        self._bootstrap_loader = None

        omni.kit.menu.utils.remove_layout(self._menu_layout)
        self._menu_layout = None

        for menu_dict in self._layout_menu_items:
            for group in menu_dict:
                omni.kit.menu.utils.remove_menu_items(menu_dict[group], group)

        self._layout_menu_items = None
        self._launcher_menu = None
        self._reset_menu = None
