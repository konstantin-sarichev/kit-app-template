---

# 🧭 SYSTEM PROMPT — *Industrial Dynamics Vision Digital Twin Environment*

## 1. Project Overview

The Vision Digital Twin project by **Industrial Dynamics** is a unified environment for creating, simulating, and managing physically accurate **digital twins of optical inspection systems** in **NVIDIA Omniverse**.
It integrates real-world camera, lens, and lighting data into Omniverse scenes to support automation, manufacturing simulation, and vision system design.

The system must operate deterministically in **millimeter units**, with all optical and geometric parameters derived from real hardware.
Every action, modification, and generated file must reinforce **physical accuracy**, **reusability**, and **traceability** across assets.

---

## 2. Project Goals

1. Maintain a **modular and reusable architecture** for camera, lens, lighting, and mechanical assets.
2. Build a **bootstrap system** that automatically enables capabilities and configures the stage each time a project is opened.
3. Ensure all data, geometry, and parameters align with **real-world scale (mm)** and consistent optical behavior.
4. Keep a **transparent record of all actions and updates** performed by the LLM or user through a persistent **Change Log**.
5. **Strictly organize scripts and tools**, preventing clutter in the project root.

---

## 3. Folder and Capability Architecture

### 3.1 Folder Structure

The project follows a fixed layout to guarantee portability and modularity:

```
project_root/
├─ bootstrap/                 → logic that initializes capabilities
│   ├─ loader.py              → discovers and runs capability modules on stage open
│   ├─ utils/                 → shared helper scripts (optional)
│   └─ capabilities/          → individual functional modules
├─ custom_scripts/            → dedicated location for ad-hoc or utility scripts
├─ extensions/                → Omniverse Kit extensions folder (determines what to load)
├─ Assets/                    → all reusable USD assets
│   ├─ Cameras/               → camera assets (Camera_<Model>_<Magnification>.usd)
│   ├─ Lights/                → light assets (Light_<Type>_<WD>.usd)
│   ├─ Brackets/              → mechanical bracket assets
│   └─ Assemblies/            → assembly assets (Assembly_<Name>.usd)
├─ logs/                      → project context and change history
│   └─ changes.log
└─ project.kit                → Omniverse configuration file
```

### 3.2 Capabilities

Each *capability* represents a discrete and reusable unit of project logic — for example:

* Setting units to millimeters
* Enabling required Omniverse extensions
* Configuring telecentric camera parameters
* Normalizing light transforms
* Adding custom brightness attributes
* Checking asset consistency

Capabilities are **independent modules** located in `bootstrap/capabilities/`.
Each module:

* Contains a clearly stated purpose and description.
* Executes automatically when the Omniverse stage is opened.
* Operates only on relevant prims and parameters (non-destructive).
* Can be run individually if required.

The **loader** automatically discovers, sorts, and executes these capabilities in numeric order (e.g., `00_`, `10_`, `20_`…), ensuring consistent initialization across environments.

---

## 4. Bootstrap Behavior

When a stage opens:

1. The loader identifies all capabilities in `bootstrap/capabilities/`.
2. It runs them sequentially based on filename order.
3. Each capability performs its designated task.
4. Once complete, the loader displays a **status message** confirming all capabilities have been loaded successfully, or reports which capabilities failed to load correctly.

This ensures deterministic startup and provides immediate feedback on initialization status.

---

## 5. Change Log and Historical Background

### 5.1 Purpose

The **Change Log** is the authoritative history of all modifications, created assets, parameter updates, and new capabilities added to the project.
It serves as:

* A **context source for agents** to understand the project history and prior decisions, and
* A **recovery mechanism** in case the context window resets or sessions are interrupted.

The log does **not** control or trigger capability execution—it exists solely for documentation and context continuity.

### 5.2 Storage and Format

* The log is stored as a plain text file at `logs/changes.log`.
* Each entry must include:

  * **Timestamp**
  * **Capability or action name**
  * **Summary of change**
  * **Affected paths or files**
  * **Reason or intent**
  * **Author** (LLM, user, or system)

Entries are appended chronologically and never deleted.
In case of reset, the log remains the single source of project history.

### 5.3 Operational Rule

**Before performing any new action**, the LLM must:

1. **Read and summarize the existing log** to understand prior actions and context.
2. **Review the project background** provided in this system prompt.
3. Confirm whether the requested modification aligns with prior work or supersedes it.
4. After execution, **append a detailed new entry** describing the update and rationale.

This guarantees continuity even across sessions or models.

---

## 6. Project-Wide Conventions

* **Units:** Always use millimeters (`metersPerUnit = 0.001`).
* **Geometry & optics:** Must correspond 1:1 with real measurements.
* **No scaling transformations** — normalize all prims before saving.
* **All assets self-contained:** Each USD asset must include geometry, materials, and parameter metadata.
* **Asset categories:** Cameras, Lights, Brackets, Assemblies.
* **File naming:**

  * Cameras → `Camera_<Model>_<Magnification>.usd`
  * Lights → `Light_<Type>_<WD>.usd`
  * Assemblies → `Assembly_<Name>.usd`
* **Execution order:** Controlled by numeric prefixes in filenames.
* **Traceability:** All created or modified entities must include `id:` metadata (e.g., `id:model`, `id:type`, `id:version`, `id:author`).

---

## 7. LLM Behavior and Responsibilities

When assisting this project, the LLM must:

1. **Review Context First**

   * Read the system prompt and the entire `logs/changes.log`.
   * Summarize key prior actions before making any new change.

2. **Operate Modularly**

   * Create or update capabilities as isolated modules.
   * Never hard-code paths outside of the project structure.
   * Maintain mm-based scale consistency across all generated work.

3. **Maintain the Log**

   * Document every addition, removal, or modification to capabilities, assets, or configuration files.
   * Include reasoning for each change.

4. **Preserve Non-Destructive Design**

   * Avoid overwriting or deleting existing assets unless explicitly instructed.
   * When replacing logic, version or deprecate old capability files rather than removing them.

5. **Promote Physical Accuracy**

   * Simulated optical and lighting behavior must remain realistic and consistent with hardware parameters.

6. **Preserve Determinism**

   * Outputs and scripts should produce identical results each time they are run under the same conditions.

7. **Script Management (NO Random Scripts)**

   * **NEVER** create script files in the project root directory.
   * If a script is needed for a specific task, utility, or test, it must be saved in the `custom_scripts/` directory (or another descriptive subfolder like `tools/`).
   * Give the script a descriptive name (e.g., `custom_scripts/validate_normals.py`, not `script.py`).
   * Include a comment header or README explaining the script's purpose and usage.

---

## 8. Change Management Workflow

1. **Before change:**

   * Review log and current state.
   * Summarize context for continuity.

2. **During change:**

   * Apply updates to the correct capability or asset file.
   * Keep structure and naming conventions consistent.

3. **After change:**

   * Append a new entry to `logs/changes.log` describing what changed and why.
   * Confirm success or note any errors encountered.

4. **Upon reset or transfer:**

   * Reload the background (this system prompt).
   * Read and reconstruct project context from `changes.log`.

---

## 9. Expected Outputs

Whenever the LLM performs a task or generates content, the result should:

* Follow the existing folder and naming structure.
* **Place all ad-hoc scripts in `custom_scripts/`**, never in the root.
* Integrate seamlessly with the bootstrap loader system.
* Be described and timestamped in the change log.
* Preserve physical fidelity and system consistency.

---

## 10. CRITICAL: Build Directory Policy

> **⚠️ ALL EDITS MUST BE MADE DIRECTLY TO `_build/bootstrap/` — NOT `bootstrap/`**

Omniverse loads the bootstrap system from `_build/bootstrap/`, NOT from the source `bootstrap/` directory. This has caused repeated issues where code changes did not take effect.

### 10.1 Mandatory Edit Location

| Edit Type | Target Directory |
|-----------|------------------|
| Capabilities | `_build/bootstrap/capabilities/` |
| Utilities | `_build/bootstrap/utils/` |
| Loader | `_build/bootstrap/loader.py` |

**NEVER edit files in `bootstrap/` and expect them to work in Omniverse without copying to `_build/`.**

### 10.2 Workflow

```
┌────────────────────────────────────────────────────────────────┐
│                    EDITING BOOTSTRAP FILES                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. EDIT directly in _build/bootstrap/                          │
│     └─ This is what Omniverse loads                             │
│                                                                 │
│  2. TEST in Omniverse                                           │
│     └─ Restart Omniverse to pick up changes                     │
│                                                                 │
│  3. COPY BACK to bootstrap/ for version control (optional)      │
│     └─ If satisfied with changes, sync back to source           │
│                                                                 │
│  4. NEVER rely on automatic sync — it doesn't exist             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 10.3 LLM Instruction

When making changes to bootstrap capabilities or utilities:

1. **Always target `_build/bootstrap/`** for the working copy
2. If also updating source for version control, edit **both** files
3. Log in `changes.log` which files were edited
4. Explicitly state: "Edited in `_build/` (live) and `bootstrap/` (source)"

### 10.4 Common Mistake

❌ **Wrong**: "I've updated `bootstrap/capabilities/my_feature.py`"
   → Changes won't appear in Omniverse!

✅ **Correct**: "I've updated `_build/bootstrap/capabilities/my_feature.py`"
   → Changes will work immediately after Omniverse restart

---

## 11. Python Runtime Environment

### 11.1 CRITICAL: Multiple Python Installations

There are **three** Python installations in `_build/`. Only **one** is used at runtime:

| Location | Used at Runtime? |
|----------|------------------|
| `_build/target-deps/python/` | ❌ No (build-time only) |
| `_build/host-deps/python/` | ❌ No (host tools) |
| **`_build/windows-x86_64/release/kit/python/`** | ✅ **YES - Runtime Python** |

### 11.2 Installing Python Packages

When you encounter `ModuleNotFoundError` in Omniverse, install packages in the **runtime Python**:

```powershell
_build\windows-x86_64\release\kit\python\python.exe -m pip install <package_name>
```

### 11.3 Currently Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| pip | 24.3.1 | Package installer |
| zmxtools | 0.1.5 | Zemax .ZAR archive extraction |

### 11.4 LLM Instructions for Package Installation

1. **Always use the runtime Python path:**
   ```
   _build\windows-x86_64\release\kit\python\python.exe -m pip install <package>
   ```

2. **Verify installation:**
   ```
   _build\windows-x86_64\release\kit\python\python.exe -m pip list
   ```

3. **Update `PYTHON_RUNTIME.md`** when packages are added

4. **Update `changes.log`** to document the installation

### 11.5 Reference

For detailed Python environment documentation, see: `bootstrap/documentation/PYTHON_RUNTIME.md`

---

## 12. Documentation Architecture

### 11.1 Document Types and Their Purposes

The documentation system uses **discrete, purpose-specific documents** to avoid duplication and simplify maintenance:

| Document | Location | Purpose | Update When |
|----------|----------|---------|-------------|
| `LIGHTING_AND_OPTICS.md` | `bootstrap/documentation/` | SPD, luminosity, Kelvin color systems | Lighting features change |
| `BOOTSTRAP_SYSTEM.md` | `bootstrap/documentation/` | Bootstrap architecture and capabilities | Bootstrap system changes |
| `HARDWARE_SPECS.md` | `bootstrap/documentation/` | Camera, lens, light specifications | Hardware requirements change |
| `DEVELOPMENT_GUIDE.md` | `bootstrap/documentation/` | Common pitfalls, patterns, templates | Development patterns learned |
| `VISION_ROADMAP.md` | `bootstrap/documentation/` | Implemented vs. planned features | Features added/completed |
| `ZEMAX_LENS_INTEGRATION.md` | `bootstrap/documentation/` | Zemax file parsing and lens library integration | Lens library features change |
| `PYTHON_RUNTIME.md` | `bootstrap/documentation/` | Python environment, package installation, troubleshooting | Python packages added/issues |
| `changes.log` | `logs/` | Incremental changes and debugging | Every code change |
| `systemprompt.md` | `bootstrap/` | Project goals and LLM behavior | Policy changes only |

### 11.2 When to Reference Each Document

**Before implementing lighting/optics features:**
→ Read `LIGHTING_AND_OPTICS.md` for SPD modes, attribute names, and color calculation pipeline

**Before modifying bootstrap capabilities:**
→ Read `BOOTSTRAP_SYSTEM.md` for capability template, directory structure, and troubleshooting

**Before specifying hardware parameters:**
→ Read `HARDWARE_SPECS.md` for required camera/lens/light specifications

**Before writing new Omniverse code:**
→ Read `DEVELOPMENT_GUIDE.md` for common pitfalls, patterns, and code templates

**Before starting a new feature:**
→ Check `VISION_ROADMAP.md` for what's implemented vs. what's planned

**Before implementing lens library features:**
→ Read `ZEMAX_LENS_INTEGRATION.md` for Zemax file parsing and lens profile application

**Before installing Python packages or debugging import errors:**
→ Read `PYTHON_RUNTIME.md` for correct Python location and installation commands

**Before any code change:**
→ Check `changes.log` for recent context and prior decisions

### 11.3 Maintenance Rules

1. **One source of truth per topic** — Do not duplicate content across documents
2. **Architecture docs describe design** — They explain HOW the system works, not WHAT changed
3. **Changes.log tracks increments** — It records WHAT changed, not HOW the system works
4. **System prompt sets policy** — It defines rules, not technical details

### 11.4 Document Update Triggers

| Scenario | Action |
|----------|--------|
| New lighting feature | Update `LIGHTING_AND_OPTICS.md` + `VISION_ROADMAP.md` + append to `changes.log` |
| New bootstrap capability | Update `BOOTSTRAP_SYSTEM.md` + append to `changes.log` |
| New development pattern/pitfall learned | Update `DEVELOPMENT_GUIDE.md` + append to `changes.log` |
| Hardware specification change | Update `HARDWARE_SPECS.md` + append to `changes.log` |
| Lens library feature change | Update `ZEMAX_LENS_INTEGRATION.md` + append to `changes.log` |
| Feature completed from roadmap | Update `VISION_ROADMAP.md` (mark as ✅) + append to `changes.log` |
| Bug fix | Append to `changes.log` only |
| Policy change | Update `systemprompt.md` + append to `changes.log` |
| Refactoring | Append to `changes.log` only |
| New document created | Update `systemprompt.md` (add to reference table) + append to `changes.log` |

---

## 13. Guiding Principle

> **The system must remain self-documenting.**
> Every piece of code, asset, or modification should explain itself through its metadata and the persistent log.
> The LLM is responsible for maintaining this transparency and for ensuring that all future work aligns with the recorded history and technical standards of the Industrial Dynamics Vision Digital Twin environment.

---
