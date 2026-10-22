
from pathlib import Path
import argparse
import re
import sys

import nbformat
from nbconvert import HTMLExporter
from playwright.sync_api import sync_playwright


# ============================================================
# USER SETTINGS — CHANGE THESE FOR EACH LAB
# ============================================================

FILE_PREFIX = "Mod5_Lab01"

DEFAULT_OUTPUT_FOLDER = "Screenshots"
VIEWPORT_WIDTH = 1440


# ============================================================
# TASK HEADING PATTERNS
# Recognizes headings such as TASK 1.1, TASK 1.10, TASK 2.3
# ============================================================

TASK_PATTERN = re.compile(
    r"^\s{0,3}#{0,6}\s*TASK\s*"
    r"(\d+(?:\.\d+)*)\b",
    re.IGNORECASE | re.MULTILINE,
)

PRACTICE_PATTERN = re.compile(
    r"\bPractice\s+Tasks?\b",
    re.IGNORECASE,
)

HEADING_PATTERN = re.compile(
    r"^\s{0,3}(#{1,6})\s+",
    re.MULTILINE,
)


# ============================================================
# NOTEBOOK DISCOVERY
# ============================================================

def discover_notebooks(input_path, output_path):
    """Find one notebook or all notebooks in a folder recursively."""

    input_path = input_path.resolve()
    output_path = output_path.resolve()

    if input_path.is_file():
        if input_path.suffix.lower() != ".ipynb":
            raise ValueError(
                f"Input file is not a notebook: {input_path}"
            )
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(
            f"Input path does not exist: {input_path}"
        )

    notebooks = []

    for path in input_path.rglob("*.ipynb"):

        if ".ipynb_checkpoints" in path.parts:
            continue

        if ".git" in path.parts:
            continue

        # Do not scan notebooks inside the screenshot output folder.
        try:
            path.resolve().relative_to(output_path)
            continue
        except ValueError:
            pass

        notebooks.append(path)

    return sorted(notebooks)


# ============================================================
# TASK DETECTION
# ============================================================

def get_task_number(source):
    """Return the task number if a Markdown cell contains a task heading."""

    match = TASK_PATTERN.search(source)

    if match:
        return match.group(1)

    return None


def get_heading_level(cell):
    """Return the Markdown heading level, if available."""

    if cell.cell_type != "markdown":
        return None

    match = HEADING_PATTERN.search(cell.source)

    if match:
        return len(match.group(1))

    return None


def detect_tasks(notebook):
    """Find task headings and their cell positions."""

    task_starts = []
    seen_numbers = set()

    for index, cell in enumerate(notebook.cells):

        if cell.cell_type != "markdown":
            continue

        task_number = get_task_number(cell.source)

        if task_number is None:
            continue

        # Keep the first occurrence of each task number.
        if task_number in seen_numbers:
            continue

        seen_numbers.add(task_number)

        task_starts.append(
            (index, task_number, get_heading_level(cell))
        )

    return task_starts


def get_task_ranges(notebook, task_starts):
    """
    Determine which cells belong to each task.

    The first screenshot starts at the Practice Tasks heading
    if one exists before the first task. Otherwise it starts at
    the first task heading.

    Each subsequent task starts at its own task heading.
    """

    cells = notebook.cells

    if not task_starts:
        return []

    first_task_index = task_starts[0][0]
    first_start = first_task_index

    # Include introductory instructions when possible.
    for index in range(first_task_index):
        cell = cells[index]

        if cell.cell_type == "markdown":
            if PRACTICE_PATTERN.search(cell.source):
                first_start = index

    ranges = []

    for position, (task_index, task_number, task_level) in enumerate(
        task_starts
    ):

        start = (
            first_start
            if position == 0
            else task_index
        )

        # Stop at the next task heading.
        if position + 1 < len(task_starts):
            end = task_starts[position + 1][0]

        else:
            # For the last task, stop at the next Markdown section
            # heading at the same or a higher level, if one exists.
            end = len(cells)

            if task_level is not None:
                for index in range(task_index + 1, len(cells)):
                    cell = cells[index]

                    if cell.cell_type != "markdown":
                        continue

                    # Never split on a task heading here.
                    if get_task_number(cell.source) is not None:
                        continue

                    level = get_heading_level(cell)

                    if level is not None and level <= task_level:
                        end = index
                        break

        selected_cells = cells[start:end]

        if selected_cells:
            ranges.append(
                (task_number, selected_cells)
            )

    return ranges


# ============================================================
# EXPORT EACH TASK TO HTML
# ============================================================

def export_task_html(task_cells, notebook_metadata):
    """Export a task with its saved outputs, charts, and Markdown."""

    task_notebook = nbformat.v4.new_notebook(
        cells=task_cells,
        metadata=notebook_metadata,
    )

    exporter = HTMLExporter()
    exporter.exclude_input = False

    html, resources = exporter.from_notebook_node(task_notebook)

    return html


# ============================================================
# CAPTURE ONE FULL-PAGE PNG PER TASK
# ============================================================

def capture_notebook(
    notebook_path,
    output_root,
    input_root,
    browser,
):
    """Capture all detected tasks from one notebook."""

    print(f"\nNotebook: {notebook_path}")

    notebook = nbformat.read(
        str(notebook_path),
        as_version=4,
    )

    task_starts = detect_tasks(notebook)

    if not task_starts:
        print(
            "  SKIPPED: No task headings found. "
            "Expected Markdown headings such as TASK 1.1."
        )
        return 0

    task_ranges = get_task_ranges(notebook, task_starts)

    notebook_output = output_root
    notebook_output.mkdir(parents=True, exist_ok=True)

    page = browser.new_page(
        viewport={
            "width": VIEWPORT_WIDTH,
            "height": 1000,
        },
        device_scale_factor=1,
    )

    saved_count = 0

    try:
        for ordinal, (task_number, task_cells) in enumerate(
            task_ranges,
            start=1,
        ):

            print(
                f"  Capturing task {task_number} "
                f"({ordinal}/{len(task_ranges)})..."
            )

            html = export_task_html(
                task_cells,
                notebook.metadata,
            )

            page.set_content(
                html,
                wait_until="load",
                timeout=60000,
            )

            # Make sure the screenshot includes all cell content.
            page.add_style_tag(content="""
                html,
                body {
                    background: white !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    height: auto !important;
                    overflow: visible !important;
                }

                body {
                    box-sizing: border-box !important;
                    padding: 24px !important;
                    color: black !important;
                }

                .jp-Cell,
                .cell,
                .output,
                .output_area {
                    overflow: visible !important;
                    max-height: none !important;
                }

                pre {
                    white-space: pre-wrap !important;
                    overflow-wrap: anywhere !important;
                }

                img,
                svg,
                canvas {
                    max-width: 100% !important;
                }
            """)

            # Wait for fonts and embedded images to load.
            page.evaluate("""
                async () => {
                    if (document.fonts?.ready) {
                        await document.fonts.ready;
                    }

                    await Promise.all(
                        Array.from(document.images).map(img => {
                            if (img.complete) {
                                return Promise.resolve();
                            }

                            return new Promise(resolve => {
                                img.addEventListener(
                                    "load",
                                    resolve,
                                    { once: true }
                                );

                                img.addEventListener(
                                    "error",
                                    resolve,
                                    { once: true }
                                );
                            });
                        })
                    );
                }
            """)

            # Short filenames using the manually configured prefix.
            # The ordinal supports any number of tasks.
            filename = f"{FILE_PREFIX}_{ordinal:02d}.png"

            output_path = notebook_output / filename

            # One full-page PNG for the entire task.
            page.screenshot(
                path=str(output_path),
                full_page=True,
                animations="disabled",
                caret="hide",
                timeout=60000,
            )

            print(f"  Saved: {output_path}")
            saved_count += 1

    finally:
        page.close()

    print(f"  Completed: {saved_count} screenshots")

    return saved_count


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Capture notebook tasks as full-page PNG screenshots."
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help=(
            "Notebook file or folder. Folders are searched "
            "recursively. Defaults to the current folder."
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_FOLDER,
        help="Screenshot output folder.",
    )

    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    try:
        notebooks = discover_notebooks(
            input_path,
            output_path,
        )

    except (ValueError, FileNotFoundError) as error:
        print(f"ERROR: {error}")
        sys.exit(1)

    if not notebooks:
        print(f"No notebooks found in: {input_path}")
        sys.exit(1)

    print(f"Input folder/file: {input_path}")
    print(f"Output folder: {output_path}")
    print(f"Notebooks found: {len(notebooks)}")
    print(f"Screenshot prefix: {FILE_PREFIX}")

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_screenshots = 0
    failed_notebooks = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        try:
            for notebook_path in notebooks:

                try:
                    notebook_root = (
                        input_path
                        if input_path.is_dir()
                        else input_path.parent
                    )

                    total_screenshots += capture_notebook(
                        notebook_path=notebook_path,
                        output_root=output_path,
                        input_root=notebook_root,
                        browser=browser,
                    )

                except Exception as error:
                    failed_notebooks.append(
                        (notebook_path, str(error))
                    )

                    print(f"  ERROR: {error}")

        finally:
            browser.close()

    print("\n" + "=" * 55)
    print("FINISHED")
    print(f"Notebooks found: {len(notebooks)}")
    print(f"Screenshots created: {total_screenshots}")
    print(f"Notebooks with errors: {len(failed_notebooks)}")
    print(f"Output folder: {output_path}")

    if failed_notebooks:
        print("\nNotebooks requiring attention:")

        for path, error in failed_notebooks:
            print(f"\n- {path}")
            print(f"  {error}")


if __name__ == "__main__":
    main()
