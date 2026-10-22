
"""
Capture Practice Tasks 1.1 through 1.9 from Jupyter notebooks.

Output:
    Screenshots/Mod05Practice_Lab01_01.png
    ...
    Screenshots/Mod05Practice_Lab01_09.png

Install dependencies:
    python -m pip install --upgrade nbformat nbconvert playwright
    python -m playwright install chromium

The notebook cells are exported but NOT executed.
"""

import asyncio
import tempfile
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter
from nbconvert.writers import FilesWriter
from playwright.async_api import async_playwright


# ================= CONFIGURATION =================

NOTEBOOK_FOLDER = Path(".")
OUTPUT_FOLDER = Path("Screenshots")

OUTPUT_PREFIX = "Mod05Practice_Lab01_"

# Capture only these tasks
FIRST_TASK = 1
LAST_TASK = 9

# ==================================================


GROUP_CELLS_JS = r"""
() => {
    const selectors = [
        ".jp-Notebook > .jp-Cell",
        ".jp-Notebook-cell",
        ".jp-Cell",
        ".cell"
    ];

    let cells = [];

    for (const selector of selectors) {
        cells = Array.from(document.querySelectorAll(selector));
        if (cells.length > 0) break;
    }

    // Avoid counting nested cells twice.
    const allCells = cells;
    cells = allCells.filter(cell =>
        !allCells.some(other =>
            other !== cell && other.contains(cell)
        )
    );

    if (cells.length === 0) {
        throw new Error("No notebook cells found.");
    }

    function getHeadingInfo(cell) {
        const markdown = cell.querySelector(
            ".text_cell_render, .jp-RenderedMarkdown, " +
            ".jp-MarkdownOutput, .markdown"
        );

        if (!markdown) return null;

        const heading = markdown.querySelector(
            "h1, h2, h3, h4, h5, h6"
        );

        if (!heading) return null;

        return {
            text: heading.innerText.trim(),
            level: Number(heading.tagName.substring(1))
        };
    }

    // Match headings such as:
    // TASK 1.1
    // TASK 1.2: Create a plot
    // Task 1.9
    const taskPattern = /^\s*TASK\s*1\.(\d+)\b/i;

    // Find the Practice Tasks heading.
    let practiceIndex = -1;

    for (let i = 0; i < cells.length; i++) {
        const heading = getHeadingInfo(cells[i]);

        if (
            heading &&
            /practice\s+tasks/i.test(heading.text)
        ) {
            practiceIndex = i;
            break;
        }
    }

    // Find the requested task headings.
    const taskStarts = [];

    const searchStart = practiceIndex >= 0
        ? practiceIndex
        : 0;

    for (let i = searchStart; i < cells.length; i++) {
        const heading = getHeadingInfo(cells[i]);

        if (!heading) continue;

        const match = heading.text.match(taskPattern);

        if (match) {
            const taskNumber = Number(match[1]);

            if (
                taskNumber >= 1 &&
                taskNumber <= 9
            ) {
                taskStarts.push({
                    index: i,
                    number: taskNumber,
                    level: heading.level
                });
            }
        }
    }

    if (taskStarts.length === 0) {
        throw new Error(
            "No TASK 1.1 through TASK 1.9 headings found. " +
            "Check the notebook's Markdown headings."
        );
    }

    // Build one screenshot group for each task.
    const groups = [];

    for (let i = 0; i < taskStarts.length; i++) {
        const current = taskStarts[i];

        // Include the Practice Tasks heading in the first capture,
        // if it exists.
        const start = (
            i === 0 && practiceIndex >= 0
        )
            ? practiceIndex
            : current.index;

        let end = taskStarts[i + 1]
            ? taskStarts[i + 1].index
            : cells.length;

        // Stop the last task before TASK 1.10 or a new section.
        if (i === taskStarts.length - 1) {
            for (
                let j = current.index + 1;
                j < cells.length;
                j++
            ) {
                const heading = getHeadingInfo(cells[j]);

                if (!heading) continue;

                const match = heading.text.match(taskPattern);

                if (match && Number(match[1]) > LAST_TASK) {
                    end = j;
                    break;
                }

                if (
                    !match &&
                    heading.level <= current.level
                ) {
                    end = j;
                    break;
                }
            }
        }

        const group = cells.slice(start, end);

        if (group.length > 0) {
            groups.push({
                taskNumber: current.number,
                cells: group
            });
        }
    }

    // Wrap each task so Playwright can screenshot it separately.
    groups.forEach(item => {
        const group = item.cells;
        const wrapper = document.createElement("div");

        wrapper.className = "step-capture";
        wrapper.dataset.taskNumber = String(item.taskNumber);

        wrapper.style.cssText =
            "background:white;color:#222;padding:16px;" +
            "box-sizing:border-box;width:100%;";

        group[0].parentNode.insertBefore(
            wrapper,
            group[0]
        );

        group.forEach(cell => wrapper.appendChild(cell));
    });

    return groups.map(item => item.taskNumber);
}
"""


def get_output_filename(task_number):
    """Return a screenshot filename for a task number."""
    return (
        f"{OUTPUT_PREFIX}"
        f"{task_number:02d}.png"
    )


async def capture_notebook(browser, notebook_path):
    """Export one notebook and capture Practice Tasks 1.1–1.9."""

    print("\n" + "=" * 60)
    print(f"Notebook: {notebook_path.name}")
    print("=" * 60)

    # Read the saved notebook. Do not execute its cells.
    notebook = nbformat.read(
        str(notebook_path),
        as_version=4
    )

    with tempfile.TemporaryDirectory(
        prefix="practice_task_screenshots_"
    ) as temp_dir:

        temp_path = Path(temp_dir)

        print("Exporting notebook to HTML...")

        exporter = HTMLExporter()
        exporter.template_name = "classic"

        body, resources = exporter.from_notebook_node(
            notebook
        )

        # Keep supporting files such as output images together.
        resources["output_files_dir"] = "notebook_files"

        writer = FilesWriter(
            build_directory=str(temp_path)
        )

        html_file = writer.write(
            body,
            resources,
            notebook_name="notebook"
        )

        html_path = Path(html_file).resolve()

        if not html_path.is_file():
            raise RuntimeError(
                f"HTML export was not created: {html_path}"
            )

        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            },
            device_scale_factor=1
        )

        try:
            await page.goto(
                html_path.as_uri(),
                wait_until="load"
            )

            # Wait for fonts and embedded/local images.
            await page.evaluate(
                "() => document.fonts.ready"
            )

            await page.evaluate(
                """() => Promise.all(
                    Array.from(document.images).map(
                        img => img.decode().catch(() => {})
                    )
                )"""
            )

            task_numbers = await page.evaluate(
                GROUP_CELLS_JS
            )

            if not task_numbers:
                raise RuntimeError(
                    "No task screenshot groups were found."
                )

            print(
                "Found task(s): "
                + ", ".join(
                    f"1.{number}" for number in task_numbers
                )
            )

            for task_number in task_numbers:
                filename = get_output_filename(task_number)
                output_path = OUTPUT_FOLDER / filename

                group = page.locator(
                    f'div.step-capture[data-task-number="{task_number}"]'
                )

                await group.screenshot(
                    path=str(output_path),
                    animations="disabled",
                    type="png"
                )

                print(f"Saved: {output_path}")

            print(f"Completed: {notebook_path.name}")

        finally:
            await page.close()


async def main():
    """Process the notebook files in the configured folder."""

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    notebooks = sorted(
        path
        for path in NOTEBOOK_FOLDER.glob("*.ipynb")
        if path.is_file()
    )

    if not notebooks:
        print(
            "No .ipynb notebooks found in: "
            f"{NOTEBOOK_FOLDER.resolve()}"
        )
        print(
            "Place this script in the notebook folder "
            "or update NOTEBOOK_FOLDER."
        )
        return

    print(f"Found {len(notebooks)} notebook(s).")
    print(f"Notebook folder: {NOTEBOOK_FOLDER.resolve()}")
    print(f"Output folder: {OUTPUT_FOLDER.resolve()}")

    successful = []
    failed = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        try:
            for notebook_path in notebooks:
                try:
                    await capture_notebook(
                        browser,
                        notebook_path
                    )
                    successful.append(notebook_path.name)

                except Exception as error:
                    failed.append(
                        (notebook_path.name, str(error))
                    )

                    print(
                        f"\nERROR processing {notebook_path.name}:"
                        f"\n{error}"
                    )
                    print(
                        "Continuing with the next notebook..."
                    )

        finally:
            await browser.close()

    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Successful notebooks: {len(successful)}")
    print(f"Failed notebooks:     {len(failed)}")
    print(f"Output folder:         {OUTPUT_FOLDER.resolve()}")

    if failed:
        print("\nFiles that need attention:")

        for filename, error in failed:
            print(f"  - {filename}: {error}")

    print("\nFinished.")


if __name__ == "__main__":
    asyncio.run(main())