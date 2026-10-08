"""Drives each app through the UI like a user: add, view, edit (name + priority), delete.

Usage:  python3 bench/functional_test.py
"""
from playwright.sync_api import expect, sync_playwright

from common import open_app, serve_all


def check(page, fw):
    rows = page.locator("#task-list > li.task")
    expect(rows).to_have_count(0)
    expect(page.locator(".empty")).to_be_visible()

    # Add three tasks with different priorities
    for name, prio in [("Write report", "high"), ("Buy milk", "low"), ("Call bank", "medium")]:
        page.fill("#new-task-name", name)
        page.select_option("#new-task-priority", prio)
        page.click("button.primary")
    expect(rows).to_have_count(3)
    expect(page.locator(".count")).to_have_text("3 tasks")
    expect(rows.nth(0).locator(".task-name")).to_have_text("Write report")
    expect(rows.nth(0).locator(".badge")).to_have_text("high")
    expect(rows.nth(1).locator(".badge")).to_have_class("badge badge-low")
    expect(page.locator("#new-task-name")).to_have_value("")  # form resets
    expect(page.locator(".empty")).to_have_count(0)

    # Empty names are rejected
    page.fill("#new-task-name", "   ")
    page.click("button.primary")
    expect(rows).to_have_count(3)

    # Edit task 2: rename + change priority
    rows.nth(1).locator("button.edit").click()
    rows.nth(1).locator("input.edit-name").fill("Buy oat milk")
    rows.nth(1).locator("select.edit-priority").select_option("high")
    rows.nth(1).locator("button.save").click()
    expect(rows.nth(1).locator(".task-name")).to_have_text("Buy oat milk")
    expect(rows.nth(1).locator(".badge")).to_have_text("high")

    # Cancel an edit leaves the task unchanged
    rows.nth(2).locator("button.edit").click()
    rows.nth(2).locator("input.edit-name").fill("SHOULD NOT SAVE")
    rows.nth(2).locator("button.cancel").click()
    expect(rows.nth(2).locator(".task-name")).to_have_text("Call bank")

    # Enter key saves an edit
    rows.nth(2).locator("button.edit").click()
    rows.nth(2).locator("input.edit-name").fill("Call the bank")
    rows.nth(2).locator("input.edit-name").press("Enter")
    expect(rows.nth(2).locator(".task-name")).to_have_text("Call the bank")

    # Delete the first task
    rows.nth(0).locator("button.delete").click()
    expect(rows).to_have_count(2)
    expect(rows.nth(0).locator(".task-name")).to_have_text("Buy oat milk")
    expect(page.locator(".count")).to_have_text("2 tasks")

    # Harness operations also go through the app's state and self-verify
    page.evaluate("__bench.render(1000)")
    page.evaluate("__bench.update(50)")
    page.evaluate("__bench.remove(50)")
    expect(rows).to_have_count(950)

    # Adding after a bulk render must not collide with existing ids
    page.fill("#new-task-name", "Added after bulk")
    page.click("button.primary")
    expect(rows).to_have_count(951)
    ids = page.eval_on_selector_all("#task-list > li.task", "els => els.map(e => e.dataset.id)")
    assert len(ids) == len(set(ids)), f"{fw}: duplicate ids"
    print(f"  {fw:8s} OK — add / view / edit / cancel / delete / bulk ops")


def main():
    urls = serve_all(base_port=5190)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for fw, url in urls.items():
            page = browser.new_page()
            page.on("pageerror", lambda e, fw=fw: errors.append(f"{fw}: {e}"))
            page.on("console", lambda m, fw=fw: m.type == "error" and errors.append(f"{fw} console: {m.text}"))
            open_app(page, url)
            check(page, fw)
            page.close()
        browser.close()
    if errors:
        raise SystemExit("Errors:\n" + "\n".join(errors))
    print("All four apps passed.")


if __name__ == "__main__":
    main()
