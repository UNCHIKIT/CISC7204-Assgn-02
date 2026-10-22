## python -m pip install --upgrade nbformat nbconvert playwright
## python -m playwright install chromium

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

# Output files are named:  <OUTPUT_PREFIX>_01.png, <OUTPUT_PREFIX>_02.png, ...
# Example: "Mod01_L1" -> Mod01_L1_01.png, Mod01_L1_02.png, ...
# Set to "" to use the notebook's own filename instead.
# (If you process several notebooks at once, use "" so files don't
#  overwrite each other.)
OUTPUT_PREFIX = "Mod04_L1"

# Screenshots start at the first Markdown heading containing this text
# (case-insensitive). Everything before it is skipped.
# Set to "" to start from the top of the notebook.
START_HEADING = "Plotly graph objects"

# Which Markdown heading levels start a new screenshot.
#   None      = automatic: every heading at the SAME level as the start
#               heading (or a higher one) starts a new screenshot.
#               Example: if "Import libraries" is a "##" heading, every
#               "##" (and "#") heading starts a new screenshot.
#   [1,2,3]   = split on exactly these levels (1 = "#", 2 = "##", ...).
#   [1,2,3,4,5,6] = split on every heading.
# Merge any section shorter than this into the following one, so that no
# screenshot is too small to read (the assignment penalises that).
MIN_GROUP_HEIGHT = 600

SECTION_HEADING_LEVELS = [1, 2, 3]

# ==================================================


GROUP_CELLS_JS = r"""
(config) => {
    const startHeading = (config.startHeading || "").toLowerCase();

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
        !allCells.some(other => other !== cell && other.contains(cell))
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

        const heading = markdown.querySelector("h1, h2, h3, h4, h5, h6");
        if (!heading) return null;

        return {
            text: heading.innerText.trim(),
            level: Number(heading.tagName.substring(1))
        };
    }

    // Find the cell where screenshots should begin.
    let firstIndex = 0;

    if (startHeading) {
        firstIndex = -1;

        for (let i = 0; i < cells.length; i++) {
            const heading = getHeadingInfo(cells[i]);

            if (heading && heading.text.toLowerCase().includes(startHeading)) {
                firstIndex = i;
                break;
            }
        }

        if (firstIndex === -1) {
            throw new Error(
                'Could not find a heading containing "' +
                config.startHeading + '".'
            );
        }
    }

    // Decide which heading levels start a new screenshot.
    let levels = config.levels;

    if (!levels || levels.length === 0) {
        let startLevel = 6;

        for (let i = firstIndex; i < cells.length; i++) {
            const heading = getHeadingInfo(cells[i]);
            if (heading) {
                startLevel = heading.level;
                break;
            }
        }

        levels = [];
        for (let l = 1; l <= startLevel; l++) levels.push(l);
    }

    // The start cell always begins a section. After it, every heading
    // at a chosen level begins a new one.
    const starts = [firstIndex];

    for (let i = firstIndex + 1; i < cells.length; i++) {
        const heading = getHeadingInfo(cells[i]);

        if (heading && levels.includes(heading.level)) {
            starts.push(i);
        }
    }

    // Each section runs from its heading to the next one, so code
    // cells and their outputs are included.
    const groups = [];

    for (let i = 0; i < starts.length; i++) {
        const start = starts[i];
        const end = starts[i + 1] ?? cells.length;
        const group = cells.slice(start, end);

        if (group.length > 0) {
            groups.push(group);
        }
    }

    // Merge any group that would produce an unreadably short screenshot into the
    // next group, so every capture carries a heading plus its code and output.
    const minHeight = config.minHeight || 0;

    if (minHeight > 0 && groups.length > 1) {
        for (let i = groups.length - 2; i >= 0; i--) {
            const rect = groups[i][0].getBoundingClientRect();
            const last = groups[i][groups[i].length - 1].getBoundingClientRect();
            const height = (last.bottom - rect.top);

            if (height < minHeight) {
                groups[i + 1] = groups[i].concat(groups[i + 1]);
                groups.splice(i, 1);
            }
        }
    }

    // Wrap each section so it can be screenshotted as its own element.
    groups.forEach(group => {
        const first = group[0];
        const wrapper = document.createElement("div");

        wrapper.className = "step-capture";
        wrapper.style.cssText =
            "background:white;color:#222;padding:16px;" +
            "box-sizing:border-box;width:100%;";

        first.parentNode.insertBefore(wrapper, first);
        group.forEach(cell => wrapper.appendChild(cell));
    });

    return { count: groups.length, levels: levels };
}
"""


def get_output_prefix(notebook_path):
    """Build the output filename prefix."""
    if OUTPUT_PREFIX:
        return OUTPUT_PREFIX + "_"

    return notebook_path.stem + "_"


async def capture_notebook(browser, notebook_path):
    """Export one notebook and capture its screenshot groups."""

    prefix = get_output_prefix(notebook_path)

    print(f"\n{'=' * 55}")
    print(f"Notebook: {notebook_path.name}")
    print(f"{'=' * 55}")

    # Read saved notebook content. Never execute its cells.
    notebook = nbformat.read(
        str(notebook_path),
        as_version=4
    )

    with tempfile.TemporaryDirectory(
        prefix="notebook_screenshots_"
    ) as temp_dir:

        temp_path = Path(temp_dir)

        print("Exporting notebook to HTML...")

        exporter = HTMLExporter()
        exporter.template_name = "classic"

        body, resources = exporter.from_notebook_node(
            notebook
        )

        # Write supporting resources, such as output images.
        resources["output_files_dir"] = "notebook_files"

        writer = FilesWriter(
            build_directory=str(temp_path)
        )

        html_path = Path(
            writer.write(
                body,
                resources,
                notebook_name="notebook"
            )
        ).resolve()

        if not html_path.is_file():
            raise RuntimeError(
                f"Exported HTML file was not created: {html_path}"
            )

        page = await browser.new_page(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1
        )

        try:
            await page.goto(
                html_path.as_uri(),
                wait_until="load"
            )

            # Wait for fonts and any embedded/local images.
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

            result = await page.evaluate(
                GROUP_CELLS_JS,
                {
                    "levels": SECTION_HEADING_LEVELS,
                    "startHeading": START_HEADING,
                    "minHeight": MIN_GROUP_HEIGHT,
                }
            )

            group_count = result["count"]
            used_levels = ", ".join(
                "#" * level for level in result["levels"]
            )

            if group_count == 0:
                raise RuntimeError("No screenshot groups found.")

            print(f"Splitting on heading levels: {used_levels}")
            print(f"Found {group_count} screenshot group(s).")

            for index in range(group_count):
                filename = f"{prefix}{index + 1:02d}.png"
                output_path = OUTPUT_FOLDER / filename

                group = page.locator(
                    "div.step-capture"
                ).nth(index)

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
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Find notebooks in this folder only, not nested folders.
    notebooks = sorted(
        path
        for path in NOTEBOOK_FOLDER.glob(
            "CISC7204 Assgn02 Module 04 - Lab01 mc65308 UN CHI KIT.ipynb"
        )
        if path.is_file()
    )
    if not notebooks:
        print(
            f"No .ipynb files found in "
            f"{NOTEBOOK_FOLDER.resolve()}"
        )
        return

    print(f"Found {len(notebooks)} notebook(s).")
    print(f"Screenshot folder: {OUTPUT_FOLDER.resolve()}")

    if OUTPUT_PREFIX and len(notebooks) > 1:
        print(
            "\nWARNING: OUTPUT_PREFIX is set but several notebooks were "
            "found. Their screenshots will overwrite each other. "
            'Set OUTPUT_PREFIX = "" to name files after each notebook.'
        )

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
                    failed.append((notebook_path.name, str(error)))

                    print(
                        f"\nERROR processing {notebook_path.name}:"
                        f"\n{error}"
                    )
                    print("Continuing with the next notebook...")

        finally:
            await browser.close()

    print("\n" + "=" * 55)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 55)
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
