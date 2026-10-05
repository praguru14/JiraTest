import argparse
import sys

from agents.content_reviewer import ContentReviewer
from agents.content_generator import ContentGenerator
from core.document import Document
from documents.profiles import RELEASE_NOTES
from publishers.file_publisher import FilePublisher
from services.html_builder import HTMLBuilder
from sources.csv_source import CsvWorkItemSource


def main():
    parser = argparse.ArgumentParser(
        description="Generate a reviewed HTML document from a CSV work-item export."
    )
    parser.add_argument("csv_path", help="CSV file containing work items")
    parser.add_argument("--output", default="output/release_notes.html")
    parser.add_argument("--scope", default="Done", help="Status to include; use an empty string for all rows")
    parser.add_argument("--title", default="CSV Release Notes")
    args = parser.parse_args()

    items = CsvWorkItemSource(args.csv_path).fetch_done_items(args.scope)
    if not items:
        print("No matching work items found.")
        return 1

    generator = ContentGenerator(RELEASE_NOTES)
    notes = generator.generate(items)
    if not notes:
        print("Document generation returned no valid content.")
        return 1

    review = ContentReviewer(RELEASE_NOTES).review(notes)
    if not isinstance(review, dict) or review.get("valid") is not True:
        print(f"Document review failed: {review}")
        return 1

    rendered = HTMLBuilder.build_document(args.title, notes)
    document = Document(
        title=args.title,
        body=rendered.body,
        format=rendered.format,
        metadata={"source": "csv", "document_type": RELEASE_NOTES.name},
    )
    FilePublisher(args.output).publish(document)
    print(f"Published {len(notes)} items to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
